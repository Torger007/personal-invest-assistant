"""
AKShare 统一数据源

用 akshare 替换原东方财富/天天基金 HTTP 爬虫。
所有方法同步执行，返回 List[Dict]，便于调用方（调度器）用 asyncio.to_thread 包装。
"""
from typing import List, Dict
from datetime import datetime, timedelta

import requests
import urllib3

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 保存原始 Session
_original_session = requests.Session

# 创建自定义 Session，禁用 SSL 验证 + 设置浏览器 UA
class _CustomSession(requests.Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verify = False  # 禁用 SSL 验证
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

# Monkey patch requests.Session
requests.Session = _CustomSession

import akshare as ak
import pandas as pd


# 指数代码 → akshare symbol 映射
INDEX_SYMBOL_MAP = {
    "000001": "sh000001",  # 上证指数
    "399001": "sz399001",  # 深证成指
    "399006": "sz399006",  # 创业板指
    "000300": "sh000300",  # 沪深300
    "000905": "sh000905",  # 中证500
}


class AkShareSource:
    """基于 akshare 的统一数据源"""

    def __init__(self):
        self.name = "AKShare"

    # ============== 指数数据 ==============

    def get_index_daily(self, index_code: str, days: int = 30) -> List[Dict]:
        """获取指数日线数据

        Args:
            index_code: 指数代码，如 000001 (上证)
            days: 获取最近多少天数据

        Returns:
            List[Dict]: 每条包含 code/date/open/high/low/close/volume/amount
        """
        symbol = INDEX_SYMBOL_MAP.get(index_code, f"sh{index_code}")
        try:
            df = ak.stock_zh_index_daily_em(symbol=symbol)
        except Exception as e:
            print(f"[AKShare] 获取指数 {index_code} 失败: {e}")
            return []

        if df is None or df.empty:
            return []

        # 只取最近 days 天
        df = df.tail(days)

        result = []
        for _, row in df.iterrows():
            try:
                date_val = row["date"]
                if isinstance(date_val, str):
                    date_val = datetime.strptime(date_val, "%Y-%m-%d").date()
                elif hasattr(date_val, "date"):
                    date_val = date_val.date()

                result.append({
                    "code": index_code,
                    "date": date_val,
                    "open": float(row.get("open", 0)),
                    "close": float(row.get("close", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "volume": int(float(row.get("volume", 0) or 0)),
                    "amount": float(row.get("amount", 0) or 0),
                })
            except Exception as e:
                print(f"[AKShare] 解析指数 {index_code} 行数据失败: {e}")
                continue

        # 按日期倒序（最新在前）
        result.sort(key=lambda x: x["date"], reverse=True)
        return result

    def get_index_spot(self) -> List[Dict]:
        """获取主要指数实时行情

        Returns:
            List[Dict]: 每条包含 code/name/value/change/change_pct
        """
        try:
            df = ak.stock_zh_index_spot_em(symbol="沪深重要指数")
        except Exception as e:
            print(f"[AKShare] 获取指数实时行情失败: {e}")
            return []

        if df is None or df.empty:
            return []

        # 只筛选关注的指数
        target_codes = list(INDEX_SYMBOL_MAP.keys())
        df = df[df["代码"].isin(target_codes)]

        result = []
        for _, row in df.iterrows():
            try:
                result.append({
                    "code": str(row.get("代码", "")),
                    "name": str(row.get("名称", "")),
                    "value": float(row.get("最新价", 0) or 0),
                    "change": float(row.get("涨跌额", 0) or 0),
                    "change_pct": float(row.get("涨跌幅", 0) or 0),
                })
            except Exception:
                continue
        return result

    # ============== 基金数据 ==============

    def get_fund_nav(self, fund_code: str, days: int = 30) -> List[Dict]:
        """获取基金历史净值

        Args:
            fund_code: 基金代码，如 005827
            days: 获取最近多少天

        Returns:
            List[Dict]: 每条包含 fund_code/date/unit_nav/acc_nav/daily_return
        """
        try:
            # 单位净值走势
            df_unit = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            # 累计净值走势
            df_acc = ak.fund_open_fund_info_em(symbol=fund_code, indicator="累计净值走势")
        except Exception as e:
            print(f"[AKShare] 获取基金 {fund_code} 净值失败: {e}")
            return []

        if df_unit is None or df_unit.empty:
            return []

        # 合并累计净值到单位净值表
        acc_map = {}
        if df_acc is not None and not df_acc.empty:
            for _, row in df_acc.iterrows():
                try:
                    d = row["净值日期"]
                    if isinstance(d, str):
                        d = datetime.strptime(d, "%Y-%m-%d").date()
                    elif hasattr(d, "date"):
                        d = d.date()
                    acc_map[d] = float(row.get("累计净值", 0) or 0)
                except Exception:
                    continue

        # 只取最近 days 天
        df_unit = df_unit.tail(days)

        result = []
        for _, row in df_unit.iterrows():
            try:
                d = row["净值日期"]
                if isinstance(d, str):
                    d = datetime.strptime(d, "%Y-%m-%d").date()
                elif hasattr(d, "date"):
                    d = d.date()

                result.append({
                    "fund_code": fund_code,
                    "date": d,
                    "unit_nav": float(row.get("单位净值", 0) or 0),
                    "acc_nav": acc_map.get(d, float(row.get("单位净值", 0) or 0)),
                    "daily_return": float(row.get("日增长率", 0) or 0),
                })
            except Exception as e:
                print(f"[AKShare] 解析基金 {fund_code} 净值行失败: {e}")
                continue

        # 按日期倒序（最新在前）
        result.sort(key=lambda x: x["date"], reverse=True)
        return result

    def get_fund_info(self, fund_code: str) -> Dict:
        """获取基金基本信息（从全市场基金列表查询）

        Args:
            fund_code: 基金代码

        Returns:
            Dict: 包含 code/name/type 等信息
        """
        try:
            df = ak.fund_name_em()
        except Exception as e:
            print(f"[AKShare] 获取基金列表失败: {e}")
            return {}

        if df is None or df.empty:
            return {}

        row = df[df["基金代码"].astype(str) == str(fund_code)]
        if row.empty:
            return {"code": fund_code}

        row = row.iloc[0]
        return {
            "code": fund_code,
            "name": str(row.get("基金简称", "")),
            "type": str(row.get("基金类型", "")),
        }

    def get_fund_list(self) -> List[Dict]:
        """获取全市场基金列表

        Returns:
            List[Dict]: 每条包含 code/name/type
        """
        try:
            df = ak.fund_name_em()
        except Exception as e:
            print(f"[AKShare] 获取基金列表失败: {e}")
            return []

        if df is None or df.empty:
            return []

        result = []
        for _, row in df.iterrows():
            try:
                result.append({
                    "code": str(row.get("基金代码", "")),
                    "name": str(row.get("基金简称", "")),
                    "type": str(row.get("基金类型", "")),
                })
            except Exception:
                continue
        return result

    # ============== 资金流向 ==============

    def get_fund_flow(self, days: int = 30) -> List[Dict]:
        """获取北向资金历史数据

        使用 akshare 的 stock_hsgt_hist_em 接口
        symbol 可选: "北向资金" / "沪股通" / "深股通"

        Returns:
            List[Dict]: 每条包含 date/north_flow/main_flow/retail_flow
                        north_flow 单位为元
        """
        try:
            df = ak.stock_hsgt_hist_em(symbol="北向资金")
        except Exception as e:
            print(f"[AKShare] 获取北向资金数据失败: {e}")
            return []

        if df is None or df.empty:
            return []

        df = df.tail(days)

        result = []
        for _, row in df.iterrows():
            try:
                date_val = row["日期"]
                if isinstance(date_val, str):
                    date_val = datetime.strptime(date_val, "%Y-%m-%d").date()
                elif hasattr(date_val, "date"):
                    date_val = date_val.date()

                # 当日成交净买额（akshare 单位：亿元），转为元
                net_buy = float(row.get("当日成交净买额", 0) or 0)
                north_flow = net_buy * 1e8

                result.append({
                    "date": date_val,
                    "north_flow": north_flow,
                    "main_flow": 0.0,  # 主力数据暂未支持
                    "retail_flow": 0.0,
                })
            except Exception as e:
                print(f"[AKShare] 解析北向资金行失败: {e}")
                continue

        result.sort(key=lambda x: x["date"], reverse=True)
        return result

    # ============== 板块数据 ==============

    def get_sector_list(self, sector_type: str = "concept") -> List[Dict]:
        """获取板块列表（概念板块或行业板块）

        Args:
            sector_type: "concept" 概念板块 / "industry" 行业板块

        Returns:
            List[Dict]: 每条包含 code/name/type/change_pct/volume/amount
        """
        try:
            if sector_type == "industry":
                df = ak.stock_board_industry_name_em()
                board_type = "industry"
            else:
                df = ak.stock_board_concept_name_em()
                board_type = "concept"
        except Exception as e:
            print(f"[AKShare] 获取板块列表失败: {e}")
            return []

        if df is None or df.empty:
            return []

        result = []
        for _, row in df.iterrows():
            try:
                result.append({
                    "code": str(row.get("板块代码", "") or row.get("板块名称", "")),
                    "name": str(row.get("板块名称", "")),
                    "type": board_type,
                    "change_pct": float(row.get("涨跌幅", 0) or 0),
                    "volume": float(row.get("总成交量", 0) or 0) if "总成交量" in row.index else 0.0,
                    "amount": float(row.get("成交额", 0) or 0) if "成交额" in row.index else 0.0,
                    "leader": str(row.get("领涨股票", "") or ""),
                    "leader_change": float(row.get("领涨股票-涨跌幅", 0) or 0) if "领涨股票-涨跌幅" in row.index else 0.0,
                })
            except Exception:
                continue

        # 按涨跌幅降序
        result.sort(key=lambda x: x["change_pct"], reverse=True)
        return result

    def get_sector_hist(self, sector_name: str, days: int = 30,
                        sector_type: str = "concept") -> List[Dict]:
        """获取板块历史行情

        Args:
            sector_name: 板块名称（中文），如 "人工智能"
            days: 最近多少天
            sector_type: "concept" / "industry"

        Returns:
            List[Dict]: 每条包含 date/name/open/close/high/low/change_pct/volume/amount
        """
        try:
            if sector_type == "industry":
                df = ak.stock_board_industry_hist_em(symbol=sector_name, period="日k")
            else:
                df = ak.stock_board_concept_hist_em(symbol=sector_name, period="日k")
        except Exception as e:
            print(f"[AKShare] 获取板块 {sector_name} 历史行情失败: {e}")
            return []

        if df is None or df.empty:
            return []

        df = df.tail(days)

        result = []
        for _, row in df.iterrows():
            try:
                date_val = row.get("日期")
                if isinstance(date_val, str):
                    date_val = datetime.strptime(date_val, "%Y-%m-%d").date()
                elif hasattr(date_val, "date"):
                    date_val = date_val.date()

                result.append({
                    "date": date_val,
                    "name": sector_name,
                    "open": float(row.get("开盘", 0) or 0),
                    "close": float(row.get("收盘", 0) or 0),
                    "high": float(row.get("最高", 0) or 0),
                    "low": float(row.get("最低", 0) or 0),
                    "change_pct": float(row.get("涨跌幅", 0) or 0),
                    "volume": float(row.get("成交量", 0) or 0),
                    "amount": float(row.get("成交额", 0) or 0),
                })
            except Exception as e:
                print(f"[AKShare] 解析板块 {sector_name} 行失败: {e}")
                continue

        result.sort(key=lambda x: x["date"], reverse=True)
        return result