from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.db import get_db
from app.services.data_collector.storage import DataStorage

router = APIRouter(prefix="/market", tags=["市场"])

# 指数代码与名称映射
INDEX_MAP = [
    {"code": "000001", "name": "上证指数"},
    {"code": "399001", "name": "深证成指"},
    {"code": "399006", "name": "创业板指"},
]


@router.get("/overview")
async def get_market_overview(db: AsyncSession = Depends(get_db)):
    """获取市场概览：主要指数最新点位与涨跌幅"""
    storage = DataStorage(db)
    indices = []

    try:
        for item in INDEX_MAP:
            recent = await storage.get_latest_index_data(item["code"], days=2)
            if len(recent) >= 1:
                latest = recent[0]
                prev = recent[1] if len(recent) >= 2 else None
                change = None
                change_pct = None
                if prev and prev["close"] and prev["close"] != 0:
                    change = float(latest["close"]) - float(prev["close"])
                    change_pct = change / float(prev["close"]) * 100
                indices.append({
                    "name": item["name"],
                    "code": item["code"],
                    "value": float(latest["close"]),
                    "change": round(change, 2) if change is not None else None,
                    "change_pct": round(change_pct, 2) if change_pct is not None else None,
                    "date": str(latest["date"]),
                    "volume": int(latest["volume"]) if latest["volume"] else None,
                })
            else:
                indices.append({
                    "name": item["name"],
                    "code": item["code"],
                    "value": None,
                    "change": None,
                    "change_pct": None,
                    "date": None,
                    "volume": None,
                })

        # 最新资金流向
        flow_history = await storage.get_fund_flow_history(days=1)
        latest_flow = flow_history[0] if flow_history else None

        return {
            "indices": indices,
            "fund_flow": {
                "date": str(latest_flow["date"]) if latest_flow else None,
                "north_flow": float(latest_flow["north_flow"]) if latest_flow else None,
                "main_flow": float(latest_flow["main_flow"]) if latest_flow else None,
            } if latest_flow else None,
            "update_time": indices[0]["date"] if indices and indices[0]["date"] else None,
        }
    except Exception as e:
        return {"error": str(e), "indices": [], "fund_flow": None, "update_time": None}


@router.get("/index/{code}")
async def get_index_detail(code: str, days: int = 30, db: AsyncSession = Depends(get_db)):
    """获取单只指数的K线数据（近N日）"""
    storage = DataStorage(db)
    try:
        data = await storage.get_latest_index_data(code, days=days)
        # 倒序转为正序（便于前端绘制K线）
        klines = list(reversed(data))
        return {
            "code": code,
            "klines": klines,
            "count": len(klines)
        }
    except Exception as e:
        return {"error": str(e), "code": code, "klines": [], "count": 0}


@router.get("/fund-flow")
async def get_fund_flow(days: int = 30, db: AsyncSession = Depends(get_db)):
    """获取资金流向历史数据"""
    storage = DataStorage(db)
    try:
        data = await storage.get_fund_flow_history(days=days)
        # 倒序转为正序
        flows = list(reversed(data))
        return {
            "flows": flows,
            "count": len(flows)
        }
    except Exception as e:
        return {"error": str(e), "flows": [], "count": 0}


@router.get("/sectors")
async def get_sectors(db: AsyncSession = Depends(get_db)):
    """获取板块数据（暂未采集，返回占位）"""
    return {
        "sectors": [],
        "update_time": None,
        "message": "板块数据采集功能开发中"
    }