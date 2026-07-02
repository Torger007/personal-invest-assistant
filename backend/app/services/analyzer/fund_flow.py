"""
资金流向分析模块

分析主力资金、北向资金、融资余额等动向。
资金数据有滞后性，置信度适中。
"""
from typing import Dict, List
from app.services.analyzer.result import AnalysisResult


class FundFlowAnalyzer:
    """资金流向分析器"""

    def __init__(self):
        self.name = "fund_flow"

    def analyze(
        self,
        main_flow_days: List[float],
        north_flow_days: List[float],
        margin_change: float = None
    ) -> AnalysisResult:
        """
        资金流向分析

        参数：
            main_flow_days: 近期主力资金净流入序列（按日）
            north_flow_days: 近期北向资金净流入序列
            margin_change: 融资余额变化百分比
        """
        reasons = []
        bull_count, bear_count = 0, 0
        confidence = 0.5

        # 1. 主力资金
        if main_flow_days:
            recent = main_flow_days[-5:]
            continuous_inflow = sum(1 for x in recent if x > 0)
            total_recent = sum(recent)

            if continuous_inflow >= 3 and total_recent > 0:
                reasons.append(f"主力资金近5日有{continuous_inflow}日净流入，累计{total_recent/1e8:.2f}亿")
                bull_count += 1
                confidence = max(confidence, 0.65)
            elif continuous_inflow <= 2 and total_recent < 0:
                reasons.append(f"主力资金近5日有{5-continuous_inflow}日净流出，累计{total_recent/1e8:.2f}亿")
                bear_count += 1
                confidence = max(confidence, 0.65)

        # 2. 北向资金
        if north_flow_days:
            recent = north_flow_days[-5:]
            north_inflow_days = sum(1 for x in recent if x > 0)
            north_total = sum(recent)

            if north_inflow_days >= 3 and north_total > 0:
                reasons.append(f"北向资金连续买入，近5日累计净买入{north_total/1e8:.2f}亿")
                bull_count += 1
                confidence = max(confidence, 0.70)
            elif north_inflow_days <= 2 and north_total < 0:
                reasons.append(f"北向资金持续卖出，近5日累计净卖出{abs(north_total)/1e8:.2f}亿")
                bear_count += 1
                confidence = max(confidence, 0.70)

        # 3. 融资余额
        if margin_change is not None:
            if margin_change > 0.02:
                reasons.append(f"融资余额上升{margin_change*100:.1f}%，杠杆资金加仓")
                bull_count += 1
            elif margin_change < -0.02:
                reasons.append(f"融资余额下降{abs(margin_change)*100:.1f}%，杠杆资金减仓")
                bear_count += 1

        # 综合判断
        if bull_count > bear_count and bull_count >= 2:
            signal, score = "看多", 70.0
        elif bear_count > bull_count and bear_count >= 2:
            signal, score = "看空", 30.0
        elif bull_count == bear_count and bull_count > 0:
            signal, score = "中性", 50.0
            reasons.append("资金面信号不一，多空分歧明显")
        else:
            signal, score = "中性", 50.0
            reasons.append("资金面数据不足或信号不明显")

        return AnalysisResult(
            dimension=self.name,
            signal=signal,
            confidence=round(confidence, 2),
            score=score,
            reasons=reasons[:5],
            details={
                "主力态度": "净流入" if (main_flow_days and sum(main_flow_days[-5:]) > 0) else "净流出",
                "北向态度": "净买入" if (north_flow_days and sum(north_flow_days[-5:]) > 0) else "净卖出"
            }
        )