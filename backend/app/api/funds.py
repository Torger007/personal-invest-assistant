from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.utils.db import get_db
from app.models import Fund

router = APIRouter(prefix="/funds", tags=["基金"])

@router.get("/")
async def get_funds(db: Session = Depends(get_db)):
    """获取基金列表"""
    funds = db.query(Fund).all()
    return {"funds": [{"code": f.code, "name": f.name, "type": f.type} for f in funds]}

@router.get("/{fund_code}")
async def get_fund(fund_code: str, db: Session = Depends(get_db)):
    """获取单只基金详情"""
    fund = db.query(Fund).filter(Fund.code == fund_code).first()
    if not fund:
        return {"error": "基金不存在"}
    return {
        "code": fund.code,
        "name": fund.name,
        "type": fund.type,
        "manager": fund.manager,
        "company": fund.company
    }
