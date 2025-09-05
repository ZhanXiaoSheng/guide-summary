from openai import OpenAI, AsyncOpenAI  # 显式使用新版客户端
from typing import List, Optional
from config.settings import settings
from loguru import logger
from core.models import SummaryResponse, SummaryRequest, QAPair, QA


class EmergencySummaryGenerator:
    def __init__(self):
        # 使用 AsyncOpenAI 异步客户端
        self.client = AsyncOpenAI(
            api_key=settings.API_KEY,
            base_url=settings.BASE_URL
        )
        self.model = settings.LLM_MODEL
        self.temperature = 0.3
        self.max_tokens = 512

    async def generate_summary(
        self,
        request_data: SummaryRequest
    ) -> SummaryResponse:
        """生成接警指引总结"""
        try:
            # 1. 构建提示词
            system_prompt = self._build_system_prompt(
                request_data.guidance_type,
                request_data.summary_type,
                request_data.prompt
            )

            # 2. 构建用户消息：整合所有 QA 数据
            user_message = self._build_user_message(
                request_data.qa_list,
                request_data.case_context
            )

            # 3. 调用大模型
            logger.debug(
                f"生成总结,案件ID= {request_data.case_id},问答记录={user_message}")
            logger.debug(f"系统提示词: {system_prompt}")
            response_text = await self._call_llm(system_prompt, user_message)

            # 4. 构建响应
            return SummaryResponse(
                case_id=request_data.case_id,
                summary=response_text,
                guidance_type=request_data.guidance_type

            )

        except Exception as e:
            logger.error(f"生成指引总结失败: {str(e)}", exc_info=True)
            raise

    def _build_system_prompt(self, guidance_type: str, summary_type: str, prompt: str) -> str:
        role_desc = "主报警人" if summary_type == 2 else "其他报警人"
        base_instruction = f"你是一名专业的消防救援指挥中心接警信息归纳员，需要根据接警员和{role_desc}提供的对话信息生成{guidance_type}接警指引总结。请按照以下要求提取信息：{prompt}"

        if summary_type != 3:
            # 按照报警人进行总结
            format_instruction = f"""
            请严格按照以下格式输出：
            （共X人报警，[角色分布统计，如：1轻生者+2住户+1路人]）

            报警人1（[具体身份]，电话：[电话号码]）：[简洁总结]
            报警人2（[具体身份]，电话：[电话号码]）：[简洁总结]
            ...

            请确保：
            - 开头标注总人数和详细的角色分布统计（根据实际身份类型汇总）
            - 然后为每个报警人单独提供一行简洁总结
            - 使用简洁的一句话总结，不要分点列出详细字段
            - 身份描述要具体：轻生者、报警人、知情人、住户、租客、路人、目击者、家属、朋友等
            - 不要添加额外标题、编号或分析内容
            - 总结内容完全基于指定的信息要点
            """
        else:
            # 一句话总结
            format_instruction = f"""
            请严格按照以下格式输出：
            （共X人报警，[角色分布统计，如：1轻生者+2住户+1路人]）
            
            简洁的一句话总结所有报警人记录

            请确保：
            - 开头标注总人数和详细的角色分布统计（根据实际身份类型汇总）
            - 第二行用一句话总结所有报警人的共同关键信息
            - 身份描述要具体：轻生者、报警人、知情人、住户、租客、路人、目击者、家属、朋友等
            - 总结内容完全基于指定的信息要点
            - 不要添加额外标题、编号或分析内容
            """

        return base_instruction + format_instruction

    def _build_user_message(self, qa_list: List[QA], case_context: Optional[str] = None) -> str:
        """构建指引信息"""
        lines = []

        if case_context:
            lines.append(f"【已有警情背景】\n{case_context}\n")

        lines.append("【报警人提供的信息】")
        for idx, qa in enumerate(qa_list):
            lines.append(f"\n--- 报警人 {idx+1} ({qa.caller_id}) 提供的信息 ---")
            for pair in qa.qa_pairs:
                lines.append(f"Q: {pair.question}")
                lines.append(f"A: {pair.answer}")

        return "\n".join(lines)

    async def _call_llm(self, system_prompt: str, user_message: str) -> str:
        """调用大模型 API（OpenAI v1.x+ 异步方式）"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"大模型API调用失败: {str(e)}")
            raise
