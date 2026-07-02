"""
天天基金数据源
数据接口参考：https://fund.eastmoney.com/...
"""
from typing import List, Dict
from app.services.data_collector.base import BaseDataSource


class TianTianSource(BaseDataSource):
    """天天基金数据源"""

    def __init__(self):
        super().__init__(
            name="天天基金",
            base_url="https://api.fund.eastmoney.com"
        )

    async def get_fund_info(self, fund_code: str) -> Dict:
        """获取基金基本信息

        天天基金基金详情接口：
        https://fund.eastmoney.com/pingzhongdata/{fund_code}.js
        包含基金名称、类型、经理、规模、历史净值等
        """
        # TODO: 实现基金详情查询
        return {}

    async def get_fund_nav(self, fund_code: str, days: int = 30) -> List[Dict]:
        """获取基金净值数据

        天天基金历史净值接口：
        https://api.fund.eastmoney.com/f10/lsjz
        参数：fund_code, page_index, page_size
        需要Referer头：https://fundf10.eastmoney.com/
        """
        # TODO: 实现净值查询
        return []

    async def get_index_daily(self, index_code: str, days: int = 30) -> List[Dict]:
        """获取指数日线数据"""
        # 天天基金主要提供基金数据，指数数据可借助东方财富
        return []

    async def get_fund_flow(self) -> Dict:
        """获取资金流向数据"""
        return {}

    async def get_fund_rank(self, fund_type: str = "gp") -> List[Dict]:
        """获取基金排行榜

        天天基金排行接口：
        https://fund.eastmoney.com/data/rankhandler.aspx
        参数：fund_type(gp=股票/hh=混合/zq=债券/zs=指数/qdii=QDII)
        """
        # TODO: 实现基金排行查询
        return []