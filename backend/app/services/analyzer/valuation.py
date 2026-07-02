"""
估值分析模块

基于PE、PB等指标的历史分位数判断当前估值水平。
估值数据相对客观，置信度通常较高。
"""
import pandas as pd
import numpy as np
from typing import List
from app.services.analyzer.result import AnalysisResult


class ValuationAnalyzer:
    """估值分析器"""

    def __init__(self):
        self.name = "valuation"

    def analyze(
        self,
        pe_history: pd.Series,
        current_pe: float,
        peer_pe_median: float = None
    ) -> AnalysisResult:
        """
        估值分析

        参数：
            pe_history: 历史PE序列（用于计算分位）
            current_pe: 当前PE
            peer_pe_median: 同类基金/指数PE中位数（可选）
        """
        if pe_history is None or len(pe_history) < 60:
            return AnalysisResult(
                dimension=self.name,
                signal="中性",
                confidence=0.3,
                score=50.0,
                reasons=["历史数据不足，估值分析可靠性较低"]
            )

        # 计算当前PE的历史分位
        percentile = (pe_history < current_pe).mean() * 100

        # 估值判断
        reasons = []
        signal, score, confidence = self._judge_valuation(percentile, reasons)

        # 横向比较
        if peer_pe_median:
            if current_pe < peer_pe_median * 0.9:
                reasons.append(f"当前PE({current_pe:.1f})低于同类中位数({peer_pe_median:.1f})10%以上")
            elif current_pe > peer_pe_median * 1.1:
                reasons.append(f"当前PE({current_pe:.1f})高于同类中位数({peer_pe_median:.1f})10%以上")

        reasons.append(f"当前PE={current_pe:.1f}，处于历史{percentile:.0f}%分位")

        return AnalysisResult(
            dimension=self.name,
            signal=signal,
            confidence=round(confidence, 2),
            score=round(score, 1),
            reasons=reasons[:5],
            details={
                "当前PE": current_pe,
                "历史分位": f"{percentile:.1f}%",
                "历史最大值": float(pe_history.max()),
                "历史最小值": float(pe_history.min()),
                "历史中位数": float(pe_history.median())
            }
        )

    def _judge_valuation(self, percentile: float, reasons: List[str]):
        """根据分位判断估值水平"""
        if percentile < 20:
            reasons.append("估值处于历史低位，性价比突出，下行空间有限")
            return "看多", 80.0, 0.85
        elif percentile < 40:
            reasons.append("估值处于历史中低位，相对合理偏低")
            return "看多", 65.0, 0.75
        elif percentile < 60:
            reasons.append("估值处于历史中位，性价比一般")
            return "中性", 50.0, 0.7
        elif percentile < 80:
            reasons.append("估值处于历史中高位，性价比降低")
            return "看空", 35.0, 0.75
        else:
            reasons.append("估值处于历史高位，需警惕估值回归风险")
            return "看空", 20.0, 0.85