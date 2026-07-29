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
        "description": "获取市场资金流向历史数据（主力资金、散户资金；北向资金字段可能因数据源限制为 0）",
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
    },
    {
        "name": "get_portfolio",
        "description": "读取用户当前持仓基金、名称和权重",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_latest_advice",
        "description": "读取系统化建议引擎生成的最新结构化投资建议，可查询单只基金或整个持仓组合",
        "input_schema": {
            "type": "object",
            "properties": {
                "fund_code": {
                    "type": "string",
                    "description": "基金代码。留空时返回当前持仓基金的最新建议"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回历史建议条数。查询单只基金时生效，默认 1"
                }
            },
            "required": []
        }
    },
    {
        "name": "generate_advice",
        "description": "触发 deterministic 系统化建议生成器，为当前持仓基金生成或刷新结构化建议",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_market_overview",
        "description": "从数据库读取市场概览，包括主要指数最新点位、涨跌幅和最新资金流",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_sector_trend",
        "description": "读取板块轮动趋势分析，支持概念板块或行业板块",
        "input_schema": {
            "type": "object",
            "properties": {
                "sector_type": {
                    "type": "string",
                    "enum": ["concept", "industry"],
                    "description": "板块类型：concept=概念板块，industry=行业板块。默认 concept"
                },
                "limit": {
                    "type": "integer",
                    "description": "分析排名靠前的板块数量，默认 50"
                }
            },
            "required": []
        }
    },
    {
        "name": "compare_funds",
        "description": "基于持仓权重和最新结构化建议横向比较多只基金",
        "input_schema": {
            "type": "object",
            "properties": {
                "fund_codes": {
                    "type": "array",
                    "description": "要比较的基金代码列表。留空时比较当前持仓基金",
                    "items": {"type": "string"}
                }
            },
            "required": []
        }
    },
    {
        "name": "get_analysis_history",
        "description": "读取 LLM Agent 历史分析和问答记录，帮助引用历史判断",
        "input_schema": {
            "type": "object",
            "properties": {
                "analysis_type": {
                    "type": "string",
                    "enum": ["autonomous", "interactive"],
                    "description": "历史类型。留空时返回全部类型"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回条数，默认 5"
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
