"""
板块轮动分析模块
分析行业/概念板块的走势和资金流向，判断板块强弱和轮动趋势。
"""
from typing import List, Dict
import pandas as pd


class SectorAnalyzer:
    """板块分析器"""

    def __init__(self):
        self.name = "sector"

    def analyze(self, sectors: List[Dict]) -> Dict:
        """
        板块分析

        参数 sectors: 板块数据列表，每个包含
            {name, change_pct, fund_flow, type}
        """
        if not sectors:
            return {"status": "no_data"}

        df = pd.DataFrame(sectors)

        # 涨幅前5 / 跌幅前5
        if "change_pct" in df.columns:
            top_gainers = df.nlargest(5, "change_pct")[["name", "change_pct"]].to_dict("records")
            top_losers = df.nsmallest(5, "change_pct")[["name", "change_pct"]].to_dict("records")
        else:
            top_gainers, top_losers = [], []

        # 资金净流入前5
        if "fund_flow" in df.columns:
            top_inflow = df.nlargest(5, "fund_flow")[["name", "fund_flow"]].to_dict("records")
            top_outflow = df.nsmallest(5, "fund_flow")[["name", "fund_flow"]].to_dict("records")
        else:
            top_inflow, top_outflow = [], []

        # 强势板块（涨幅+资金双正）
        strong_sectors = []
        if "change_pct" in df.columns and "fund_flow" in df.columns:
            strong = df[(df["change_pct"] > 0) & (df["fund_flow"] > 0)]
            strong_sectors = strong.nlargest(5, "change_pct")[["name", "change_pct", "fund_flow"]].to_dict("records")

        return {
            "top_gainers": top_gainers,
            "top_losers": top_losers,
            "top_inflow": top_inflow,
            "top_outflow": top_outflow,
            "strong_sectors": strong_sectors,
            "total_sectors": len(sectors)
        }