"""
用户持仓配置

在此文件中配置你关注的基金列表。
Agent 会优先分析这些基金。
"""

# 用户持仓基金列表
USER_PORTFOLIO = [
    {"code": "008163", "name": "南方红利低波50ETF联接A", "weight": 0.29},
    {"code": "021033", "name": "易方达储能电池ETF联接A", "weight": 0.184},
    {"code": "004400", "name": "金信民兴债券A", "weight": 0.0945},
    {"code": "019172", "name": "摩根纳斯达克100指数QDII A", "weight": 0.066},
    {"code": "021528", "name": "财通成长优选混合C", "weight": 0.1421},
    {"code": "026974", "name": "兴业中证电池主题指数A", "weight": 0.2227},
]


def get_portfolio_codes():
    """获取持仓基金代码列表"""
    return [fund["code"] for fund in USER_PORTFOLIO]


def get_portfolio_weights():
    """获取持仓基金权重"""
    return {fund["code"]: fund["weight"] for fund in USER_PORTFOLIO}


def get_portfolio_info():
    """获取完整持仓信息"""
    return USER_PORTFOLIO