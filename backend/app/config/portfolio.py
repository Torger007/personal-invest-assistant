"""
用户持仓配置

在此文件中配置你关注的基金列表。
Agent 会优先分析这些基金。
"""

# 用户持仓基金列表
USER_PORTFOLIO = [
    {"code": "005827", "name": "易方达蓝筹精选混合", "weight": 0.3},
    {"code": "110011", "name": "易方达中小盘混合", "weight": 0.2},
    {"code": "161725", "name": "招商中证白酒指数", "weight": 0.2},
    {"code": "003834", "name": "华夏能源革新股票", "weight": 0.15},
    {"code": "005612", "name": "中欧医疗健康混合", "weight": 0.15},
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
