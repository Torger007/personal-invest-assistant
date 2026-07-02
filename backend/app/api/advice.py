from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.utils.db import get_db
from app.models import AdviceRecord

router = APIRouter(prefix="/advice", tags=["建议"])

@router.get("/")
async def get_advice_list(db: Session = Depends(get_db)):
    """获取建议列表"""
    # TODO: 实现建议生成逻辑
    return {
        "advice": [],
        "message": "建议生成模块开发中"
    }

@router.get("/{fund_code}")
async def get_fund_advice(fund_code: str, db: Session = Depends(get_db)):
    """获取单只基金的投资建议"""
    # TODO: 实现单只基金的建议生成
    return {
        "fund_code": fund_code,
        "advice": None,
        "message": "建议生成模块开发中"
    }
