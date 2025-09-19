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
                    "summary": "简洁的一句话总结，完全基于对话信息",
                    "isTrapped": true 或 false  // 若对话中明确表明报警人本人被困（如“我被困在…”、“我出不去了”、“是本人被困”等），则为 true；否则为 false

                }}
            ]
        }}

        请确保：
        - total_info 必须是“（共1人报警，[具体身份]）”格式，例如：“（共1人报警，轻生者）”
        - callers 列表中只包含一个对象，包含 identity、phone、summary 三个字段
        - identity 描述要具体：轻生者、报警人、知情人、住户、租客、路人、目击者、家属、朋友等
        - summary 必须是一句话，不要分点、不要换行、不要添加分析
        - isTrapped 必须是布尔值 true 或 false，根据对话内容判断：若报警人明确表示自己被困（如“我被困在1503”、“我在屋里出不去”、“是本人被困”），则为 true；若未提及或仅描述他人被困，则为 false
        - 输出必须是合法 JSON，可以直接被程序解析
        - 不要包含 ```json 或任何 Markdown 包装
        """
        elif summary_type == 3:
            # 总结全部报警人 → callers 只有一个对象，仅含 summary 字段，但采用“总分结构”
            format_instruction = f"""
        请严格按照以下 JSON 格式输出，不要包含任何额外文本、分析、编号或标题：

        {{
            "total_info": "（共X人报警，[角色分布统计，如：1轻生者+2住户+1路人]）",
            "callers": [
                {{
                    "summary": "各报警人共同反馈[共性内容一句话]。具体而言：[身份A]（[电话A]）描述：[个性化一句话]\\n[身份B]（[电话B]）描述：[个性化一句话]\\n..."
                }}
            ]
        }}

        请确保：
        - total_info 必须以“（共X人报警，...）”开头，角色分布按实际汇总（如：1轻生者+2住户）
        - callers 列表中只包含一个对象，且只包含 summary 字段
        - summary 字段内容必须为一个字符串，采用“总分结构”：
          1. 开头必须是“各报警人共同反馈[共性内容一句话]。” —— 提炼所有报警人提及的共同情况（如：浓烟、断电、位置、危险类型等）
          2. 紧接着是“具体而言：”，然后逐条列出每位报警人的个性化信息，格式为：
             “[身份]（[电话]）描述：[一句话总结]\\n”
          3. 每条报警人信息后必须使用 \\n 换行，最后一条也需换行（保持格式统一）
        - 示例：
          "各报警人共同反馈楼道浓烟弥漫且存在断电情况。具体而言：住户A（17633607832）描述：配电间起火及1503室两名老人被困\\n路人B（16696380123）描述：发现1601室厨房明火\\n14楼住户C（12038474728）描述：电梯井火花及不明位置呼救声\\n"
        - 共性内容必须基于对话中多个报警人交叉验证的信息，若无明确共性，可写“各报警人未反馈明显共同情况。”
        - 每个报警人的描述必须简洁、独立成句、不换行、不分析
        - 输出必须是合法 JSON，可以直接被程序解析
        - 不要包含 ```json 或任何 Markdown 包装
        """
        else:
            # 其他报警人总结
            format_instruction = f"""
            请严格按照以下 JSON 格式输出，不要包含任何额外文本、分析、编号或标题：

            {{
                "total_info": "（共X人报警，[角色分布统计，如：1轻生者+2住户+1路人]）",
                "callers": [
                    {{
                        "identity": "具体身份，如：路人、住户、轻生者等",
                        "phone": "电话号码",
                        "summary": "简洁的一句话总结，完全基于对话信息",
                        "isTrapped": true 或 false  // 若对话中明确表明报警人本人被困（如“我被困在…”、“我出不去了”、“是本人被困”等），则为 true；否则为 false

                    }},
                    ...
                ]
            }}

            请确保：
            - total_info 必须以“（共X人报警，...）”开头，角色分布按实际汇总（如：1轻生者+2住户）
            - callers 是一个列表，每个元素是一个对象，包含 identity、phone、summary 三个字段
            - identity 描述要具体：轻生者、报警人、知情人、住户、租客、路人、目击者、家属、朋友等
            - summary 必须是一句话，不要分点、不要换行、不要添加分析
            - isTrapped 必须是布尔值 true 或 false，根据对话内容判断：若报警人明确表示自己被困（如“我被困在1503”、“我在屋里出不去”、“是本人被困”），则为 true；若未提及或仅描述他人被困，则为 false
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
