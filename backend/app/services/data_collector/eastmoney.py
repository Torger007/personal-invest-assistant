"""
东方财富数据源
数据接口文档参考：https://push2.eastmoney.com/api/qt/...
"""
from typing import List, Dict
from datetime import datetime, timedelta
from app.services.data_collector.base import BaseDataSource


class EastMoneySource(BaseDataSource):
    """东方财富数据源"""

    def __init__(self):
        super().__init__(
            name="东方财富",
            base_url="https://push2.eastmoney.com"
        )

    async def get_fund_info(self, fund_code: str) -> Dict:
        """获取基金基本信息"""
        # TODO: 实现具体的请求逻辑
        return {}

    async def get_fund_nav(self, fund_code: str, days: int = 30) -> List[Dict]:
        """获取基金净值数据

        东方财富基金净值接口示例：
        http://api.fund.eastmoney.com/f10/lsjz
        参数：fund_code, page_index, page_size
        """
        # TODO: 实现净值查询
        return []

    async def get_index_daily(self, index_code: str, days: int = 30) -> List[Dict]:
        """获取指数日线数据

        使用东方财富K线接口获取指数历史行情
        接口：http://push2his.eastmoney.com/api/qt/stock/kline/get
        """
        # 构建指数证券ID（市场代码.指数代码）
        # 1=上交所，0=深交所
        secid_map = {
            "000001": "1.000001",  # 上证指数
            "399001": "0.399001",  # 深证成指
            "399006": "0.399006",  # 创业板指
        }
        secid = secid_map.get(index_code, f"1.{index_code}")

        # 计算日期范围（乘以2确保获取足够数据）
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y-%m-%d")

        url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": "101",  # 日K线
            "fqt": "1",    # 前复权
            "beg": start_date.replace("-", ""),
            "end": end_date.replace("-", ""),
        }

        data = await self.fetch(url, params=params)

        if not data or "data" not in data or data["data"] is None:
            return []

        klines = data["data"].get("klines", [])
        result = []

        # 取最近days天的数据
        for kline in klines[-days:]:
            fields = kline.split(",")
            if len(fields) >= 7:
                result.append({
                    "code": index_code,
                    "date": datetime.strptime(fields[0], "%Y-%m-%d").date(),
                    "open": float(fields[1]),
                    "close": float(fields[2]),
                    "high": float(fields[3]),
                    "low": float(fields[4]),
                    "volume": int(float(fields[5])),
                    "amount": float(fields[6])
                })

        return result

    async def get_fund_flow(self, days: int = 30) -> List[Dict]:
        """获取资金流向数据（北向资金、主力资金）

        使用东方财富资金流向接口
        接口：http://push2.eastmoney.com/api/qt/kamtbs.ann
        字段：f51=日期, f52=沪股通净流入, f53=深股通净流入,
              f54=北向合计, f55=当日净额, f56=当日余额
        """
        url = "http://push2.eastmoney.com/api/qt/kamtbs.ann"
        params = {
            "fields1": "f1,f2,f3,f4",
            "fields2": "f51,f52,f53,f54,f55,f56",
            "klt": "101",  # 日K
            "lmt": str(days),
        }

        data = await self.fetch(url, params=params)

        if not data or "data" not in data or data["data"] is None:
            return []

        result = []
        klines = data["data"].get("klines", [])

        for kline in klines[-days:]:
            fields = kline.split(",")
            if len(fields) >= 4:
                try:
                    # f52=沪股通净流入, f53=深股通净流入, f54=北向合计
                    north = float(fields[1]) if fields[1] != "-" else 0.0
                    # f54为北向合计；如缺失则用 f52+f53
                    main = float(fields[2]) if fields[2] != "-" else 0.0
                    result.append({
                        "date": datetime.strptime(fields[0], "%Y-%m-%d").date(),
                        "north_flow": north,   # 北向资金净流入（元）
                        "main_flow": main,     # 沪股通净流入（元，作为主力近似）
                        "retail_flow": 0.0     # 散户资金暂不可用
                    })
                except (ValueError, IndexError):
                    continue

        return result

    async def get_sector_list(self) -> List[Dict]:
        """获取板块列表及涨跌数据"""
        # TODO: 实现板块数据查询
        return []