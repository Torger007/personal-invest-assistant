"""
天天基金数据源
数据接口参考：https://fund.eastmoney.com/...
"""
from typing import List, Dict
from datetime import datetime
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

        使用天天基金基金详情接口：
        https://fund.eastmoney.com/pingzhongdata/{fund_code}.js
        返回JS变量赋值，需解析提取
        """
        url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
        text = await self.fetch_text(url)

        if not text:
            return {}

        # pingzhongdata.js 内是 JS 变量赋值，用简单字符串提取
        import re
        fund_info = {"code": fund_code}

        # 基金名称：var fS_name = "基金名称";
        name_match = re.search(r'var\s+fS_name\s*=\s*"([^"]+)";', text)
        if name_match:
            # 名称形如 "易方达蓝筹精选混合(005827)"
            fund_info["name"] = name_match.group(1).split("(")[0].strip()

        # 基金类型：var fS_FundType = "基金类型代码";
        # 基金经理：var fj_jjjl = "..." 但提取较复杂，这里先返回基础信息
        return fund_info

    async def get_fund_nav(self, fund_code: str, days: int = 30) -> List[Dict]:
        """获取基金净值数据

        使用天天基金历史净值接口：
        https://api.fund.eastmoney.com/f10/lsjz
        参数：fund_code, page_index, page_size
        需要Referer头：https://fundf10.eastmoney.com/
        返回JSON：{Data:{LSJZList:[{FSRQ,FDWQZ,LJJZ,JZZZL}, ...]}}
        """
        url = "https://api.fund.eastmoney.com/f10/lsjz"
        headers = {"Referer": f"https://fundf10.eastmoney.com/jjjz_{fund_code}.html"}
        params = {
            "fundCode": fund_code,
            "pageIndex": 1,
            "pageSize": days,
        }

        data = await self.fetch(url, params=params, headers=headers)

        if not data or "Data" not in data or data["Data"] is None:
            return []

        records = data["Data"].get("LSJZList", [])
        result = []

        for record in records[:days]:
            try:
                nav_date = datetime.strptime(record["FSRQ"], "%Y-%m-%d").date()
                unit_nav = float(record["DWJZ"]) if record.get("DWJZ") else 0.0
                acc_nav = float(record["LJJZ"]) if record.get("LJJZ") else 0.0
                daily_return = float(record["JZZZL"]) if record.get("JZZZL") else 0.0

                result.append({
                    "fund_code": fund_code,
                    "date": nav_date,
                    "unit_nav": unit_nav,
                    "acc_nav": acc_nav,
                    "daily_return": daily_return
                })
            except (ValueError, KeyError, TypeError):
                continue

        return result

    async def get_index_daily(self, index_code: str, days: int = 30) -> List[Dict]:
        """获取指数日线数据"""
        # 天天基金主要提供基金数据，指数数据可借助东方财富
        return []

    async def get_fund_flow(self, days: int = 30) -> List[Dict]:
        """获取资金流向数据"""
        return []

    async def get_fund_rank(self, fund_type: str = "gp") -> List[Dict]:
        """获取基金排行榜

        天天基金排行接口：
        https://fund.eastmoney.com/data/rankhandler.aspx
        参数：fund_type(gp=股票/hh=混合/zq=债券/zs=指数/qdii=QDII)
        """
        # TODO: 实现基金排行查询
        return []