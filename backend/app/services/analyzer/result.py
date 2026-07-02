"""
分析结果数据结构
所有分析器统一返回 AnalysisResult
"""
from typing import List, Optional
from pydantic import BaseModel


class AnalysisResult(BaseModel):
    """单维度分析结果

    设计核心：不是给出一个分数，而是给出结论+置信度+理由
    """
    dimension: str              # 维度名称（technical/valuation/fund_flow/sentiment）
    signal: str                 # 信号：看多 / 看空 / 中性
    confidence: float           # 置信度 0-1
    score: float                # 综合评分 0-100（仅供参考，决策依据以signal为准）
    reasons: List[str]          # 关键理由（证据链）
    details: Optional[dict] = None  # 详细数据（如关键价位、估值分位等）