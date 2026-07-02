"""
市场情绪分析模块

分析市场热度、新闻舆情、恐贪指数等。
情绪指标噪音大，置信度较低。注意：情绪过热反而是风险信号。
"""
from typing import List, Optional
from app.services.analyzer.result import AnalysisResult


class SentimentAnalyzer:
    """市场情绪分析器"""

    def __init__(self):
        self.name = "sentiment"

    def analyze(
        self,
        market_turnover: List[float],    # 近期成交额序列
        fear_greed_index: float = None,   # 恐贪指数 0-100
        news_sentiment: float = None,     # 新闻情感倾向 -1 到 1
        new_fund_scale: float = None      # 新基金发行规模（亿）
    ) -> AnalysisResult:
        """市场情绪分析"""
        reasons = []
        bull_count, bear_count = 0, 0
        confidence = 0.5
        heat_score = 50.0  # 市场温度

        # 1. 市场热度（成交额）
        if market_turnover and len(market_turnover) >= 5:
            recent_avg = sum(market_turnover[-5:]) / 5
            prev_avg = sum(market_turnover[-10:-5]) / 5 if len(market_turnover) >= 10 else recent_avg

            if recent_avg > prev_avg * 1.5:
                reasons.append(f"成交额显著放大({recent_avg/1e8:.0f}亿)，市场活跃度高")
                heat_score = 75.0
                # 注意：过热是风险，反向解读
            elif recent_avg < prev_avg * 0.7:
                reasons.append(f"成交额萎缩({recent_avg/1e8:.0f}亿)，市场参与度低")
                heat_score = 30.0

        # 2. 恐贪指数
        if fear_greed_index is not None:
            if fear_greed_index >= 75:
                reasons.append(f"恐贪指数={fear_greed_index:.0f}，市场极度贪婪，警惕阶段高点")
                bear_count += 1
                confidence = max(confidence, 0.60)
                heat_score = max(heat_score, 80.0)
            elif fear_greed_index <= 25:
                reasons.append(f"恐贪指数={fear_greed_index:.0f}，市场极度恐惧，或存反弹机会")
                bull_count += 1
                confidence = max(confidence, 0.60)
                heat_score = min(heat_score, 20.0)
            else:
                heat_score = fear_greed_index

        # 3. 新闻舆情
        if news_sentiment is not None:
            if news_sentiment > 0.5:
                reasons.append("新闻舆情偏正面，但需警惕过热言论")
                if heat_score >= 70:
                    bear_count += 1  # 过热+利好=风险
                else:
                    bull_count += 1
            elif news_sentiment < -0.5:
                reasons.append("新闻舆情偏负面，市场情绪低迷")
                if heat_score <= 30:
                    bull_count += 1  # 过冷+利空=反弹机会
                else:
                    bear_count += 1

        # 4. 新基金发行（过热信号）
        if new_fund_scale is not None and new_fund_scale > 50:
            reasons.append(f"新基金发行火爆(单日{new_fund_scale:.0f}亿)，情绪过热信号")
            bear_count += 1
            heat_score = max(heat_score, 75.0)

        # 综合判断（情绪反向解读：过热=谨慎，过冷=机会）
        signal, score = self._synthesize(heat_score, bull_count, bear_count, reasons)

        return AnalysisResult(
            dimension=self.name,
            signal=signal,
            confidence=round(confidence, 2),
            score=score,
            reasons=reasons[:5],
            details={
                "市场温度": f"{heat_score:.0f}/100",
                "恐贪指数": fear_greed_index,
                "情绪状态": "过热" if heat_score >= 70 else ("过冷" if heat_score <= 30 else "正常")
            }
        )

    def _synthesize(self, heat_score, bull_count, bear_count, reasons):
        """情绪反向解读：过热=谨慎，过冷=机会"""
        if heat_score >= 75:
            # 过热 → 谨慎
            reasons.append("情绪过热时往往是阶段性高点，建议谨慎")
            return "看空", 30.0
        elif heat_score <= 25:
            # 过冷 → 机会
            reasons.append("情绪过冷时往往是布局机会，可考虑逢低介入")
            return "看多", 70.0
        elif bull_count > bear_count:
            return "看多", 60.0
        elif bear_count > bull_count:
            return "看空", 40.0
        else:
            return "中性", 50.0