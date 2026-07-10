"""
工具定义模块

定义所有可供 Agent 调用的工具的 JSON Schema。
每个工具包含名称、描述和输入参数规范。
"""

TOOL_DEFINITIONS = [
    {
        "name": "get_index_data",
        "description": "获取指数历史行情数据（K线）",
        "input_schema": {
            "type": "object",
            "properties": {
                "index_code": {
                    "type": "string",
                    "description": "指数代码，如 000001（上证）、399001（深证）、399006（创业板）"
                },
                "days": {
                    "type": "integer",
                    "description": "获取最近多少天数据，默认 30"
                }
            },
            "required": ["index_code"]
        }
    },
    {
        "name": "get_fund_nav",
        "description": "获取基金历史净值数据",
        "input_schema": {
            "type": "object",
            "properties": {
                "fund_code": {
                    "type": "string",
                    "description": "基金代码，如 005827"
                },
                "days": {
                    "type": "integer",
                    "description": "获取最近多少天数据，默认 30"
                }
            },
            "required": ["fund_code"]
        }
    },
    {
        "name": "get_fund_info",
        "description": "获取基金基本信息",
        "input_schema": {
            "type": "object",
            "properties": {
                "fund_code": {
                    "type": "string",
                    "description": "基金代码，如 005827"
                }
            },
            "required": ["fund_code"]
        }
    },
    {
        "name": "analyze_technical",
        "description": "对行情数据做技术分析（均线、MACD、RSI、量价等）",
        "input_schema": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "description": "K线数据数组，每项包含 date/open/high/low/close/volume",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string"},
                            "open": {"type": "number"},
                            "high": {"type": "number"},
                            "low": {"type": "number"},
                            "close": {"type": "number"},
                            "volume": {"type": "number"}
                        }
                    }
                }
            },
            "required": ["data"]
        }
    },
    {
        "name": "get_fund_flow",
        "description": "获取北向资金历史数据",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "获取最近多少天数据，默认 30"
                }
            },
            "required": []
        }
    }
]


def get_tool_definitions() -> list:
    """返回所有工具定义"""
    return TOOL_DEFINITIONS


def get_tool_definition(tool_name: str) -> dict | None:
    """根据工具名称获取单个工具定义"""
    for tool in TOOL_DEFINITIONS:
        if tool["name"] == tool_name:
            return tool
    return None
