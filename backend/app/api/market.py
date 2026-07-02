from fastapi import APIRouter
from datetime import date

router = APIRouter(prefix="/market", tags=["市场"])

@router.get("/overview")
async def get_market_overview():
    """获取市场概览"""
    # TODO: 从数据库获取最新数据
    return {
        "indices": [
            {"name": "上证指数", "code": "000001", "value": None, "change": None},
            {"name": "深证成指", "code": "399001", "value": None, "change": None},
            {"name": "创业板指", "code": "399006", "value": None, "change": None}
        ],
        "update_time": None
    }

@router.get("/sectors")
async def get_sectors():
    """获取板块数据"""
    # TODO: 从数据库获取板块数据
    return {
        "sectors": [],
        "update_time": None
    }
