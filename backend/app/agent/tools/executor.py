"""
工具执行器模块

实现工具执行逻辑，调用现有的数据采集和分析函数。
所有同步方法通过 asyncio.to_thread 包装为异步调用。
"""

import asyncio
import pandas as pd
from typing import Any

from app.services.data_collector.akshare_source import AkShareSource
from app.services.analyzer.technical import TechnicalAnalyzer


async def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """
    执行指定工具

    Args:
        tool_name: 工具名称
        tool_input: 工具输入参数

    Returns:
        dict: 包含 status/data/error/count 的执行结果
    """
    try:
        if tool_name == "get_index_data":
            return await _execute_get_index_data(tool_input)

        elif tool_name == "get_fund_nav":
            return await _execute_get_fund_nav(tool_input)

        elif tool_name == "get_fund_info":
            return await _execute_get_fund_info(tool_input)

        elif tool_name == "analyze_technical":
            return await _execute_analyze_technical(tool_input)

        elif tool_name == "get_fund_flow":
            return await _execute_get_fund_flow(tool_input)

        else:
            return {
                "status": "error",
                "error": f"未知工具: {tool_name}"
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def _execute_get_index_data(tool_input: dict) -> dict:
    """获取指数历史行情数据"""
    index_code = tool_input["index_code"]
    days = tool_input.get("days", 30)

    source = AkShareSource()
    data = await asyncio.to_thread(source.get_index_daily, index_code, days)

    return {
        "status": "success",
        "data": data,
        "count": len(data)
    }


async def _execute_get_fund_nav(tool_input: dict) -> dict:
    """获取基金历史净值数据"""
    fund_code = tool_input["fund_code"]
    days = tool_input.get("days", 30)

    source = AkShareSource()
    data = await asyncio.to_thread(source.get_fund_nav, fund_code, days)

    return {
        "status": "success",
        "data": data,
        "count": len(data)
    }


async def _execute_get_fund_info(tool_input: dict) -> dict:
    """获取基金基本信息"""
    fund_code = tool_input["fund_code"]

    source = AkShareSource()
    data = await asyncio.to_thread(source.get_fund_info, fund_code)

    return {
        "status": "success",
        "data": data
    }


async def _execute_analyze_technical(tool_input: dict) -> dict:
    """对行情数据做技术分析"""
    raw_data = tool_input["data"]

    if not raw_data:
        return {
            "status": "error",
            "error": "数据为空，无法进行技术分析"
        }

    # 将字典数组转换为 DataFrame
    df = pd.DataFrame(raw_data)

    # 确保有必要的列
    required_columns = ["date", "open", "high", "low", "close", "volume"]
    for col in required_columns:
        if col not in df.columns:
            return {
                "status": "error",
                "error": f"缺少必要字段: {col}"
            }

    # 转换数值类型
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 删除有空值的行
    df = df.dropna()

    if df.empty or len(df) < 30:
        return {
            "status": "error",
            "error": "有效数据不足 30 条，无法进行技术分析"
        }

    analyzer = TechnicalAnalyzer()
    result = await asyncio.to_thread(analyzer.analyze, df)

    return {
        "status": "success",
        "data": {
            "dimension": result.dimension,
            "signal": result.signal,
            "confidence": result.confidence,
            "score": result.score,
            "reasons": result.reasons,
            "details": result.details
        }
    }


async def _execute_get_fund_flow(tool_input: dict) -> dict:
    """获取北向资金历史数据"""
    days = tool_input.get("days", 30)

    source = AkShareSource()
    data = await asyncio.to_thread(source.get_fund_flow, days)

    return {
        "status": "success",
        "data": data,
        "count": len(data)
    }
