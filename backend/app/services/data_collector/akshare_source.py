"""
AKShare 统一数据源

用 akshare 替换原东方财富/天天基金 HTTP 爬虫。
所有方法同步执行，返回 List[Dict]，便于调用方用 asyncio.to_thread 包装。

SSL/UA 补丁在 app.startup_patch 中统一处理，此处直接调用。
"""
from typing import List, Dict
from datetime import datetime, date, timedelta

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

    def _get_fund_name_df(self):
        """获取全市场基金列表 DataFrame（类级别缓存，避免重复调用 AKShare）"""
        import time
        cls = self.__class__
        if not hasattr(cls, "_fund_name_cache"):
            cls._fund_name_cache = (0, None)
        cache_time, cache_data = cls._fund_name_cache
        now = time.time()
        if cache_data is not None and now - cache_time < 60:
            return cache_data
        df = ak.fund_name_em()
        cls._fund_name_cache = (now, df)
        return df

    def _clear_fund_name_cache(self):
        """清除基金列表缓存"""
        self.__class__._fund_name_cache = (0, None)

    def get_fund_info(self, fund_code: str) -> Dict:
        """获取基金基本信息（从全市场基金列表查询）

        Args:
            fund_code: 基金代码

        Returns:
            Dict: 包含 code/name/type 等信息，失败时只返回 code
        """
        for attempt in range(2):
            try:
                df = self._get_fund_name_df()
                if df is not None and not df.empty:
                    row = df[df["基金代码"].astype(str) == str(fund_code)]
                    if not row.empty:
                        row = row.iloc[0]
                        name = str(row.get("基金简称", "")).strip()
                        fund_type = str(row.get("基金类型", "")).strip()
                        if name:
                            return {
                                "code": fund_code,
                                "name": name,
                                "type": fund_type,
                            }
            except Exception as e:
                print(f"[AKShare] fund_name_em 失败 (尝试 {attempt+1}/2): {e}")
                if attempt < 1:
                    # 清除缓存后重试一次
                    import time
                    time.sleep(0.5)
                    self._clear_fund_name_cache()

        # 失败时只返回 code，调用方会跳过入库（因为没有 name）
        print(f"[AKShare] get_fund_info 失败，未获取到 {fund_code} 的基金信息")
        return {"code": fund_code}

    def get_fund_list(self) -> List[Dict]:
        """获取全市场基金列表

        Returns:
            List[Dict]: 每条包含 code/name/type
        """
        df = self._get_fund_name_df()

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
        """获取市场资金流向数据（主力/散户资金）

        使用 akshare 的 stock_market_fund_flow 接口。
        原 stock_hsgt_hist_em 接口的北向资金字段已停用（全为 NaN）。

        Returns:
            List[Dict]: 每条包含 date/north_flow/main_flow/retail_flow
                north_flow: 北向资金（已不可用，置为0）
                main_flow: 主力净流入（大单+中单）
                retail_flow: 散户净流入（小单）
        """
        try:
            df = ak.stock_market_fund_flow()
        except Exception as e:
            print(f"[AKShare] 获取市场资金流向失败: {e}")
            return []

        if df is None or df.empty:
            return []

        df = df.tail(days)

        result = []
        for _, row in df.iterrows():
            try:
                date_val = row.iloc[0]  # 日期
                if isinstance(date_val, str):
                    date_val = datetime.strptime(date_val, "%Y-%m-%d").date()
                elif hasattr(date_val, "date"):
                    date_val = date_val.date()

                # 列索引（基于 stock_market_fund_flow 返回列）:
                # [0]=日期 [1]=上证-收盘价 [2]=上证-涨跌幅 [3]=深证-收盘价 [4]=深证-涨跌幅
                # [5]=超大单净流入-金额 [6]=超大单净流入-占比
                # [7]=大单净流入-金额 [8]=大单净流入-占比
                # [9]=中单净流入-金额 [10]=中单净流入-占比
                # [11]=小单净流入-金额 [12]=小单净流入-占比
                # 主力 = 超大单 + 大单 + 中单
                # 散户 = 小单

                super_large = float(row.iloc[5]) if len(row) > 5 and not pd.isna(row.iloc[5]) else 0.0
                large = float(row.iloc[7]) if len(row) > 7 and not pd.isna(row.iloc[7]) else 0.0
                medium = float(row.iloc[9]) if len(row) > 9 and not pd.isna(row.iloc[9]) else 0.0
                small = float(row.iloc[11]) if len(row) > 11 and not pd.isna(row.iloc[11]) else 0.0

                main_flow = super_large + large + medium
                retail_flow = small

                result.append({
                    "date": date_val,
                    "north_flow": 0.0,  # 北向资金已不可用
                    "main_flow": main_flow,
                    "retail_flow": retail_flow,
                })
            except Exception as e:
                print(f"[AKShare] 解析资金流向行失败: {e}")
                continue

        result.sort(key=lambda x: x["date"], reverse=True)
        return result

    # ============== 板块数据（使用同花顺数据源，东方财富板块接口被CDN拦截）==============

    def get_sector_list(self, sector_type: str = "concept") -> List[Dict]:
        """获取板块列表（概念板块或行业板块）

        行业板块使用 stock_board_industry_summary_ths，返回涨跌幅/成交量/领涨股等完整数据。
        概念板块使用 stock_board_concept_name_ths，仅返回名称+代码，涨跌幅在点击时通过K线计算。

        Args:
            sector_type: "concept" 概念板块 / "industry" 行业板块

        Returns:
            List[Dict]: 每条包含 code/name/type/change_pct/volume/amount/leader/leader_change
        """
        if sector_type == "industry":
            return self._get_industry_list_ths()
        else:
            return self._get_concept_list_ths()

    def _get_industry_list_ths(self) -> List[Dict]:
        """从同花顺获取行业板块排名（含涨跌幅、成交量、领涨股等完整数据）

        列布局（位置索引）:
            [0]=序号 [1]=名称 [2]=涨跌幅 [3]=总成交量 [4]=总成交额
            [5]=换手率 [6]=上涨家数 [7]=下跌家数
            [8]=市盈率 [9]=领涨股 [10]=领涨股-所属行业? [11]=领涨股-涨跌幅

        Returns:
            List[Dict]
        """
        try:
            df = ak.stock_board_industry_summary_ths()
        except Exception as e:
            print(f"[AKShare] 获取行业板块排名失败: {e}")
            return []

        if df is None or df.empty:
            return []

        result = []
        for _, row in df.iterrows():
            try:
                result.append({
                    "code": str(row.iloc[1]),       # 名称（兼做code）
                    "name": str(row.iloc[1]),        # 名称
                    "type": "industry",
                    "change_pct": float(row.iloc[2] or 0),    # 涨跌幅
                    "volume": float(row.iloc[3] or 0),        # 总成交量
                    "amount": float(row.iloc[4] or 0),        # 总成交额
                    "leader": str(row.iloc[9] or ""),         # 领涨股
                    "leader_change": float(row.iloc[11] or 0), # 领涨股-涨跌幅
                })
            except Exception:
                continue

        result.sort(key=lambda x: x["change_pct"], reverse=True)
        return result

    def _get_concept_list_ths(self) -> List[Dict]:
        """从同花顺获取概念板块列表并计算涨跌幅

        列布局: [0]=name [1]=code
        涨跌幅通过拉取板块指数历史计算（取最近2日收盘价）。
        为控制请求量，只计算前50个热门板块（按名称排序）。

        Returns:
            List[Dict]
        """
        try:
            df = ak.stock_board_concept_name_ths()
        except Exception as e:
            print(f"[AKShare] 获取概念板块列表失败: {e}")
            return []

        if df is None or df.empty:
            return []

        result = []
        # 限制计算涨跌幅的板块数量，避免请求过多
        limit = min(50, len(df))

        for idx, row in df.iterrows():
            try:
                name = str(row.iloc[0])
                code = str(row.iloc[1])

                # 只计算前50个板块的涨跌幅
                change_pct = 0.0
                if idx < limit:
                    try:
                        # 获取最近2天的指数数据计算涨跌幅
                        hist_df = ak.stock_board_concept_index_ths(
                            symbol=name, start_date="20260101", end_date=date.today().strftime("%Y%m%d")
                        )
                        if hist_df is not None and len(hist_df) >= 2:
                            # 取最后两行的收盘价（第5列）
                            close_today = float(hist_df.iloc[-1].iloc[4])
                            close_yest = float(hist_df.iloc[-2].iloc[4])
                            if close_yest != 0:
                                change_pct = (close_today - close_yest) / close_yest * 100
                                change_pct = round(change_pct, 2)
                    except Exception as e:
                        # 静默失败，使用0.0
                        pass

                result.append({
                    "code": code,
                    "name": name,
                    "type": "concept",
                    "change_pct": change_pct,
                    "volume": 0.0,
                    "amount": 0.0,
                    "leader": "",
                    "leader_change": 0.0,
                })
            except Exception:
                continue

        # 按涨跌幅降序排列
        result.sort(key=lambda x: x["change_pct"], reverse=True)
        return result

    def get_sector_hist(self, sector_name: str, days: int = 30,
                        sector_type: str = "concept") -> List[Dict]:
        """获取板块历史行情（使用同花顺数据源）

        Args:
            sector_name: 板块名称（中文），如 "人工智能"、"半导体"
            days: 最近多少天
            sector_type: "concept" / "industry"

        Returns:
            List[Dict]: 每条包含 date/name/open/close/high/low/change_pct/volume/amount
        """
        today = date.today()
        # 多取一些天数以防停牌/节假日
        start_date = (today - timedelta(days=days * 3)).strftime("%Y%m%d")
        end_date = today.strftime("%Y%m%d")

        try:
            if sector_type == "industry":
                df = ak.stock_board_industry_index_ths(
                    symbol=sector_name, start_date=start_date, end_date=end_date
                )
            else:
                df = ak.stock_board_concept_index_ths(
                    symbol=sector_name, start_date=start_date, end_date=end_date
                )
        except Exception as e:
            print(f"[AKShare] 获取板块 {sector_name} 历史行情失败: {e}")
            return []

        if df is None or df.empty:
            return []

        # 只取最近 days 天
        df = df.tail(days)

        result = []
        prev_close = None
        for _, row in df.iterrows():
            try:
                date_val = row.iloc[0]  # 第一列是日期
                if isinstance(date_val, str):
                    date_val = datetime.strptime(date_val, "%Y-%m-%d").date()
                elif hasattr(date_val, "date"):
                    date_val = date_val.date()

                close_val = float(row.iloc[4])  # 第5列是收盘价
                open_val = float(row.iloc[1])
                high_val = float(row.iloc[2])
                low_val = float(row.iloc[3])
                vol = float(row.iloc[5]) if len(row) > 5 else 0.0
                amt = float(row.iloc[6]) if len(row) > 6 else 0.0

                # 计算涨跌幅
                if prev_close and prev_close != 0:
                    change_pct = (close_val - prev_close) / prev_close * 100
                else:
                    change_pct = 0.0
                prev_close = close_val

                result.append({
                    "date": date_val,
                    "name": sector_name,
                    "open": open_val,
                    "close": close_val,
                    "high": high_val,
                    "low": low_val,
                    "change_pct": round(change_pct, 2),
                    "volume": vol,
                    "amount": amt,
                })
            except Exception as e:
                print(f"[AKShare] 解析板块 {sector_name} 行失败: {e}")
                continue

        result.sort(key=lambda x: x["date"], reverse=True)
        return result