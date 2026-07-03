"""
技术分析模块

基于均线、动量、形态、量价等技术指标判断趋势。
核心原则：不只看单一指标，而是多指标交叉验证，输出结论+置信度+理由。
"""
import pandas as pd
import ta
from typing import List
from app.services.analyzer.result import AnalysisResult


class TechnicalAnalyzer:
    """技术分析器"""

    def __init__(self):
        self.name = "technical"

    def analyze(self, df: pd.DataFrame) -> AnalysisResult:
        """
        分析K线数据

        参数 df 需包含列: date, open, high, low, close, volume
        """
        if df.empty or len(df) < 30:
            return AnalysisResult(
                dimension=self.name,
                signal="中性",
                confidence=0.0,
                score=50.0,
                reasons=["数据不足，无法进行技术分析"]
            )

        reasons_bull = []
        reasons_bear = []
        confidence = 0.5

        # 1. 均线系统判断趋势
        ma_signal, ma_conf = self._check_moving_averages(df, reasons_bull, reasons_bear)
        confidence = max(confidence, ma_conf)

        # 2. 动量指标（MACD/RSI）
        mom_signal, mom_conf = self._check_momentum(df, reasons_bull, reasons_bear)
        confidence = max(confidence, mom_conf)

        # 3. 量价配合
        vol_signal = self._check_volume(df, reasons_bull, reasons_bear)

        # 综合判断信号
        signals = [ma_signal, mom_signal, vol_signal]
        bull_count = signals.count("看多")
        bear_count = signals.count("看空")

        if bull_count > bear_count and bull_count >= 2:
            signal = "看多"
            score = 60 + bull_count * 10
        elif bear_count > bull_count and bear_count >= 2:
            signal = "看空"
            score = 40 - bear_count * 10
        else:
            signal = "中性"
            score = 50.0

        # 收集理由
        reasons = self._pick_reasons(reasons_bull, reasons_bear, signal)

        return AnalysisResult(
            dimension=self.name,
            signal=signal,
            confidence=round(confidence, 2),
            score=round(max(0, min(100, score)), 1),
            reasons=reasons,
            details={
                "趋势": ma_signal,
                "动量": mom_signal,
                "量价": vol_signal
            }
        )

    def _check_moving_averages(self, df: pd.DataFrame, bull: List[str], bear: List[str]):
        """均线系统：5/10/20/60日均线"""
        close = df["close"]
        ma5 = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else None
        price = close.iloc[-1]

        # 多头排列
        if price > ma5 > ma20:
            bull.append(f"价格站上5日({ma5:.4f})和20日均线({ma20:.4f})，多头排列")
            signal, conf = "看多", 0.7
        elif price < ma5 < ma20:
            bear.append(f"价格跌破5日({ma5:.4f})和20日均线({ma20:.4f})，空头排列")
            signal, conf = "看空", 0.7
        else:
            signal, conf = "中性", 0.3

        # 60日均线（中长期趋势）
        if ma60:
            if price > ma60:
                bull.append(f"价格在60日均线({ma60:.4f})上方，中期趋势向上")
            else:
                bear.append(f"价格在60日均线({ma60:.4f})下方，中期趋势承压")

        return signal, conf

    def _check_momentum(self, df: pd.DataFrame, bull: List[str], bear: List[str]):
        """动量指标：MACD / RSI"""
        close = df["close"]

        # MACD
        macd_indicator = ta.trend.MACD(close)
        macd_line = macd_indicator.macd().iloc[-1]
        signal_line = macd_indicator.macd_signal().iloc[-1]

        if macd_line > signal_line and macd_line > 0:
            bull.append("MACD零轴上方金叉，动能增强")
            return "看多", 0.65
        elif macd_line < signal_line and macd_line < 0:
            bear.append("MACD零轴下方死叉，动能衰减")
            return "看空", 0.65

        # RSI
        rsi_indicator = ta.momentum.RSIIndicator(close)
        rsi_val = rsi_indicator.rsi().iloc[-1]

        if rsi_val < 30:
            bull.append(f"RSI={rsi_val:.1f}，超卖区域，反弹概率增加")
            return "看多", 0.55
        elif rsi_val > 70:
            bear.append(f"RSI={rsi_val:.1f}，超买区域，回调风险增加")
            return "看空", 0.55

        return "中性", 0.3

    def _check_volume(self, df: pd.DataFrame, bull: List[str], bear: List[str]):
        """量价配合验证"""
        vol = df["volume"].iloc[-5:].mean()
        vol_prev = df["volume"].iloc[-10:-5].mean()
        price_change = (df["close"].iloc[-1] - df["close"].iloc[-5]) / df["close"].iloc[-5]

        if vol > vol_prev * 1.2 and price_change > 0:
            bull.append(f"放量上涨({(vol/vol_prev-1)*100:.0f}%)，上涨有量能支持")
            return "看多"
        elif vol > vol_prev * 1.2 and price_change < 0:
            bear.append(f"放量下跌({(vol/vol_prev-1)*100:.0f}%)，抛压较大")
            return "看空"
        return "中性"

    def _pick_reasons(self, bull: List[str], bear: List[str], signal: str, max_n: int = 5):
        """根据信号选择关键理由"""
        if signal == "看多":
            return bull[:max_n] if bull else ["技术面偏多，但证据不够充分"]
        elif signal == "看空":
            return bear[:max_n] if bear else ["技术面偏空，但证据不够充分"]
        else:
            return [*bull[:2], *bear[:2]][:max_n] or ["技术面信号混杂"]
