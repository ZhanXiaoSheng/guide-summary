from openai import OpenAI, AsyncOpenAI # 显式使用新版客户端
from typing import List, Dict, Optional
from config.settings import settings
from config.logging_conf import logger
from core.models import GuidanceType, SummaryResponse, SummaryRequest, QAPair, QA

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
                request_data.is_primary
            )
            
            # 2. 构建用户消息：整合所有 QA 数据
            user_message = self._build_user_message(
                request_data.qa_list,
                request_data.case_context
            )
            
            # 3. 调用大模型
            logger.info(f"生成总结,案件ID= {request_data.case_id}")
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
    
    def _build_system_prompt(self, guidance_type: GuidanceType, is_primary: bool) -> str:
        role_desc = "主报警人" if is_primary else "综合多个报警人信息"
        base_instruction = f"你是一名专业的消防救援指挥中心接警员，需要根据{role_desc}提供的信息生成{guidance_type.value}接警指引总结。"

        extraction_rules = {
            GuidanceType.TRAFFIC_ACCIDENT: (
                "请准确提取：事发地点、车辆类型及数量、伤亡情况、交通状况、是否起火或泄漏等危险因素。"
            ),
            GuidanceType.ELEVATOR_ENTRAPMENT: (
                "请准确提取：具体位置（楼栋/单元）、电梯编号或状态、被困人数、人员类型（老人/儿童）、被困楼层、已困时间、人员健康状况。"
            ),
            GuidanceType.SUICIDE_ATTEMPT: (
                "请准确提取：轻生者所在位置（建筑/楼层/阳台）、周边环境（护栏/高度）、轻生者人数、性别、年龄估计、情绪状态、是否有危险动作、可能动机。"
                "注意措辞要专业、冷静，避免刺激性语言。"
            )
        }

        return base_instruction + extraction_rules.get(guidance_type, "请提取关键警情信息，结构化总结。只需要根据问答内容总结，请勿提供额外的处置建议。")
    

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