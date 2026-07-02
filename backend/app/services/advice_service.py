"""
建议生成服务
封装分析器+建议生成器的调用流程
"""
from typing import Optional
import pandas as pd
from app.services.analyzer import (
    TechnicalAnalyzer, ValuationAnalyzer,
    FundFlowAnalyzer, SentimentAnalyzer, Advisor
)


class AdviceService:
    """建议生成服务"""

    def __init__(self):
        self.tech = TechnicalAnalyzer()
        self.val = ValuationAnalyzer()
        self.flow = FundFlowAnalyzer()
        self.sent = SentimentAnalyzer()
        self.advisor = Advisor()

    def generate_for_fund(
        self,
        fund_code: str,
        kline_df: pd.DataFrame,
        pe_history: pd.Series,
        current_pe: float,
        main_flow_days: list,
        north_flow_days: list,
        market_turnover: list,
        current_position: float = 0.0,
        market_environment: str = "震荡市",
        margin_change: float = None,
        fear_greed_index: float = None,
        peer_pe_median: float = None
    ) -> dict:
        """为指定基金生成投资建议"""
        technical = self.tech.analyze(kline_df)
        valuation = self.val.analyze(pe_history, current_pe, peer_pe_median)
        fund_flow = self.flow.analyze(main_flow_days, north_flow_days, margin_change)
        sentiment = self.sent.analyze(market_turnover, fear_greed_index)

        result = self.advisor.generate(
            technical, valuation, fund_flow, sentiment,
            market_environment, current_position
        )
        result["fund_code"] = fund_code
        return result


advice_service = AdviceService()