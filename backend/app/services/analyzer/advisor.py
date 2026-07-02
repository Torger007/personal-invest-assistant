"""
综合建议生成器

系统核心：负责整合各维度分析结果，进行信号一致性检验，
根据市场环境动态调整权重，最终生成可信、可解释的投资建议。

设计原则：
1. 不是简单加权打分，而是检查各维度是否达成共识
2. 信号一致 → 高置信度；矛盾信号 → 保守建议并明确风险
3. 根据市场环境动态调整维度权重
4. 每个建议必须有完整的证据链
"""
from typing import List, Optional
from app.services.analyzer.result import AnalysisResult
import json


class Advisor:
    """综合建议生成器"""

    # 维度信号权重（基础值，会根据市场环境调整）
    BASE_WEIGHTS = {
        "technical": 0.25,
        "valuation": 0.30,
        "fund_flow": 0.20,
        "sentiment": 0.25
    }

    # 信号到分数的映射
    SIGNAL_SCORE = {"看多": 1.0, "中性": 0.0, "看空": -1.0}

    def __init__(self):
        self.name = "advisor"

    def generate(
        self,
        technical: AnalysisResult,
        valuation: AnalysisResult,
        fund_flow: AnalysisResult,
        sentiment: AnalysisResult,
        market_environment: str = "震荡市",  # 牛市/熊市/震荡市
        current_position: float = 0.0  # 当前仓位 0-1
    ) -> dict:
        """
        生成综合投资建议

        参数：
            technical/valuation/fund_flow/sentiment: 各维度分析结果
            market_environment: 当前市场环境
            current_position: 当前仓位比例
        """
        results = {
            "technical": technical,
            "valuation": valuation,
            "fund_flow": fund_flow,
            "sentiment": sentiment
        }

        # 1. 信号一致性检验
        consistency = self._check_consistency(results)

        # 2. 根据市场环境调整权重
        weights = self._adjust_weights(market_environment)

        # 3. 计算综合评分
        overall_score = self._calculate_score(results, weights)

        # 4. 综合置信度（考虑一致性）
        confidence = self._calculate_confidence(results, consistency)

        # 5. 生成操作建议
        action, target_position = self._generate_action(
            overall_score, confidence, consistency, current_position
        )

        # 6. 生成建议文本
        advice_text = self._build_advice_text(
            results, action, target_position, confidence, consistency,
            current_position, market_environment
        )

        return {
            "overall_signal": action,
            "confidence": round(confidence * 100, 1),
            "overall_score": round(overall_score, 1),
            "consistency": consistency,
            "market_environment": market_environment,
            "current_position": current_position,
            "target_position": target_position,
            "technical_score": technical.score,
            "valuation_score": valuation.score,
            "fund_flow_score": fund_flow.score,
            "sentiment_score": sentiment.score,
            "advice_text": advice_text,
            "details": {
                "technical": technical.dict(),
                "valuation": valuation.dict(),
                "fund_flow": fund_flow.dict(),
                "sentiment": sentiment.dict()
            }
        }

    def _check_consistency(self, results: dict) -> str:
        """信号一致性检验"""
        signals = [r.signal for r in results.values()]
        bull = signals.count("看多")
        bear = signals.count("看空")
        neutral = signals.count("中性")

        # 3个及以上维度同方向 → 高一致性
        if bull >= 3:
            return "高（多方共识）"
        elif bear >= 3:
            return "高（空方共识）"
        elif bull == 2 and bear == 0 and neutral >= 1:
            return "中高"
        elif bear == 2 and bull == 0 and neutral >= 1:
            return "中高"
        elif bull >= 1 and bear >= 1:
            return "低（信号矛盾）"  # 多空分歧
        else:
            return "中"

    def _adjust_weights(self, environment: str) -> dict:
        """根据市场环境动态调整权重"""
        weights = self.BASE_WEIGHTS.copy()

        if environment == "牛市":
            # 牛市：资金和情绪权重↑，估值权重↓
            weights["fund_flow"] = 0.30
            weights["sentiment"] = 0.30
            weights["valuation"] = 0.15
            weights["technical"] = 0.25
        elif environment == "熊市":
            # 熊市：估值权重↑，情绪权重↓
            weights["valuation"] = 0.40
            weights["sentiment"] = 0.15
            weights["fund_flow"] = 0.20
            weights["technical"] = 0.25
        else:  # 震荡市
            pass  # 使用基础权重

        return weights

    def _calculate_score(self, results: dict, weights: dict) -> float:
        """计算综合评分 0-100"""
        total = 0.0
        for dim, w in weights.items():
            # score已是0-100，直接加权
            total += results[dim].score * w
        return total

    def _calculate_confidence(self, results: dict, consistency: str) -> float:
        """计算综合置信度"""
        # 各维度置信度的加权平均
        avg_conf = sum(r.confidence for r in results.values()) / 4

        # 根据一致性调整
        if "高" in consistency:
            return min(1.0, avg_conf * 1.15)
        elif "低" in consistency or "矛盾" in consistency:
            return avg_conf * 0.70  # 矛盾信号降低置信度
        else:
            return avg_conf * 0.95

    def _generate_action(
        self, score, confidence, consistency, current_position
    ) -> tuple:
        """根据评分、置信度、一致性生成操作建议和目标仓位"""
        # 矛盾信号时，无论评分如何，都倾向保守
        if "矛盾" in consistency or "低" in consistency:
            if current_position > 0.3:
                return "适度减仓", max(0.2, current_position - 0.1)
            else:
                return "持有观望", current_position

        # 根据评分区间给建议
        if score >= 75:
            target = min(0.6, current_position + 0.15)
            return "强烈加仓" if confidence >= 0.75 else "适度加仓", target
        elif score >= 60:
            target = min(0.5, current_position + 0.10)
            return "适度加仓", target
        elif score >= 40:
            return "持有观望", current_position
        elif score >= 25:
            target = max(0.1, current_position - 0.10)
            return "适度减仓", target
        else:
            target = max(0.0, current_position - 0.15)
            return "建议止盈", target

    def _build_advice_text(
        self, results, action, target_position, confidence,
        consistency, current_position, environment
    ) -> str:
        """生成完整建议文本（证据链）"""
        lines = []

        lines.append(f"【市场环境】{environment}，信号一致性：{consistency}")
        lines.append(f"【操作建议】{action}")
        lines.append(f"【建议仓位】当前 {current_position*100:.0f}% → 目标 {target_position*100:.0f}%")
        lines.append(f"【置信度】{confidence*100:.0f}%")
        lines.append("")
        lines.append("【各维度分析】")

        dim_names = {
            "technical": "技术面",
            "valuation": "估值面",
            "fund_flow": "资金面",
            "sentiment": "情绪面"
        }

        for key, name in dim_names.items():
            r = results[key]
            lines.append(f"  {name}：{r.signal}（置信度 {r.confidence*100:.0f}%，评分 {r.score}）")
            for reason in r.reasons[:2]:
                lines.append(f"    - {reason}")

        lines.append("")
        lines.append("【风险提示】")
        if "矛盾" in consistency:
            lines.append("  ⚠ 各维度信号矛盾，方向不明，建议谨慎")
        if results["sentiment"].signal == "看空":
            lines.append("  ⚠ 情绪面显示市场偏热，短期可能有回调")
        lines.append("  ⚠ 建议分批操作，不要一次性调整到位")
        lines.append("  ⚠ 本系统仅供参考，投资需谨慎")

        return "\n".join(lines)