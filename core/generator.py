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

        # 对当前 报警人进行总结
        if summary_type == 2:
            # 主报警人 → callers 只有一个对象，total_info 简化
            format_instruction = f"""
        请严格按照以下 JSON 格式输出，不要包含任何额外文本、分析、编号或标题：

        {{
            "total_info": "（共1人报警，[具体身份]）",
            "callers": [
                {{
                    "identity": "具体身份，如：轻生者、住户、路人等",
                    "phone": "电话号码",
                    "summary": "简洁的一句话总结，完全基于对话信息"
                }}
            ]
        }}

        请确保：
        - total_info 必须是“（共1人报警，[具体身份]）”格式，例如：“（共1人报警，轻生者）”
        - callers 列表中只包含一个对象，包含 identity、phone、summary 三个字段
        - identity 描述要具体：轻生者、报警人、知情人、住户、租客、路人、目击者、家属、朋友等
        - summary 必须是一句话，不要分点、不要换行、不要添加分析
        - 输出必须是合法 JSON，可以直接被程序解析
        - 不要包含 ```json 或任何 Markdown 包装
        """
        else:
            # 总的总结 （全部报警人）→ 要求输出结构化 JSON
            format_instruction = f"""
            请严格按照以下 JSON 格式输出，不要包含任何额外文本、分析、编号或标题：

            {{
                "total_info": "（共X人报警，[角色分布统计，如：1轻生者+2住户+1路人]）",
                "callers": [
                    {{
                        "identity": "具体身份，如：路人、住户、轻生者等",
                        "phone": "电话号码",
                        "summary": "简洁的一句话总结，完全基于对话信息"
                    }},
                    ...
                ]
            }}

            请确保：
            - total_info 必须以“（共X人报警，...）”开头，角色分布按实际汇总（如：1轻生者+2住户）
            - callers 是一个列表，每个元素是一个对象，包含 identity、phone、summary 三个字段
            - identity 描述要具体：轻生者、报警人、知情人、住户、租客、路人、目击者、家属、朋友等
            - summary 必须是一句话，不要分点、不要换行、不要添加分析
            - 输出必须是合法 JSON，可以直接被程序解析
            - 不要包含 ```json 或任何 Markdown 包装
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
