# api/summary_router.py
from fastapi import APIRouter, HTTPException
from typing import Dict, List
from core.generator import EmergencySummaryGenerator
from core.models import JavaData, SummaryRequest, SummaryResponse, QAPair, QA, IncrementalSummaryRequest
from loguru import logger

router = APIRouter(prefix="/summary", tags=["接警总结生成"])


@router.post("/generate", response_model=SummaryResponse)
async def generate_summary(request: JavaData):
    """
    生成接警指引总结
    - summaryType=1: 合并所有报警人信息生成总结
    - summaryType=2: 仅基于主报警人生成总结（但依然可传多人数据）
    """
    try:
        if not request.allAnswers:
            raise HTTPException(status_code=400, detail="报警记录不能为空")
        if not request.guideTypeName:
            raise HTTPException(status_code=400, detail="指引类型不能为空")
        if not request.prompt:
            raise HTTPException(status_code=400, detail="提示词不能为空")

        # 转换请求
        summary_request = convert_java_data(request)
        generator = EmergencySummaryGenerator()

        # 生成总结
        response = await generator.generate_summary(summary_request)
        return response

    except Exception as e:
        logger.error(f"生成总结失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/generate_incremental", response_model=SummaryResponse)
async def generate_incremental_summary(request: IncrementalSummaryRequest):
    """
    增量式生成单报警人总结（summary_type=2 格式）
    - 每次传入一个问答对 + 当前历史总结
    - 返回更新后的完整总结（JSON格式）
    """
    try:
        # 可选：校验参数
        if not request.question or not request.answer:
            raise HTTPException(status_code=400, detail="问题或回答不能为空")

        generator = EmergencySummaryGenerator()

        # 构建单个报警人的 QA 数据
        qa_pair = QAPair(question=request.question, answer=request.answer)
        qa_item = QA(
            caller_id=request.caller_id,  # 可自定义或传入
            qa_pairs=[qa_pair]
        )

        summary_request = SummaryRequest(
            case_id=request.case_id,
            guidance_type=request.guidance_type,
            prompt=request.prompt,
            summary_type=2,  # 使用单人格式
            qa_list=[qa_item],
            case_context=request.current_summary  # 把历史摘要作为上下文传入
        )

        # 生成增量总结
        response = await generator.generate_incremental_summary(summary_request)
        return response

    except Exception as e:
        logger.error(f"增量生成总结失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


def convert_java_data(java_data: JavaData) -> SummaryRequest:
    """将 Java 数据转换为 SummaryRequest"""

    # 解析所有报警人数据
    qa_list: List[QA] = []
    for caller_id, answer_map in java_data.allAnswers.items():
        qa_pairs = [QAPair(question=q, answer=a)
                    for q, a in answer_map.items()]
        qa_list.append(QA(caller_id=caller_id, qa_pairs=qa_pairs))

    # 判断是生成主报警人总结，还是合并总结
    # is_primary = False
    # if java_data.summaryType == 2:
    #     # 仅主报警人：但 Java 应确保 allAnswers 中第一个或标记者是主报警人
    #     # 这里我们假设 Java 已按顺序传入，或 caller_id 可识别，但为简化，我们仍传全部，由 prompt 控制 focus
    #     is_primary = True
    # elif java_data.summaryType == 1:
    #     # 合并所有报警人
    #     is_primary = False
    # else:
    #     raise ValueError("summaryType 必须为 1（合并）或 2（主报警人）")

    return SummaryRequest(
        case_id=java_data.incidentId,
        guidance_type=java_data.guideTypeName,
        prompt=java_data.prompt,
        qa_list=qa_list,
        case_context=None,  # 可选：Java 可额外传 context
        summary_type=java_data.summaryType
    )
