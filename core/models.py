from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel


# 数据模型


class QAPair(BaseModel):
    """问答"""
    question: str
    answer: str


class QA(BaseModel):
    """单个人的问答"""
    caller_id: str
    qa_pairs: List[QAPair]


class SummaryRequest(BaseModel):
    """发送给大模型的请求数据"""
    case_id: str
    guidance_type: str
    prompt: str
    qa_list: List[QA]  # 多个报警人的问答（支持合并）
    case_context: Optional[str] = None
    summary_type: int
   # is_primary: bool = True  # 是否为主报警人模式（决定提示词语气）


class JavaData(BaseModel):
    """java后台请求数据模型"""
    incidentId: str
    summaryType: int  # 1: 合并所有报警人；2: 仅当前主报警人
    guideTypeName: str
    prompt: str
    allAnswers: Dict[str, Dict[str, str]]  # caller_id -> {question: answer}


class SummaryResponse(BaseModel):
    """大模型返回数据"""
    case_id: str
    summary: str
    guidance_type: str
