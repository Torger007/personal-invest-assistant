from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.utils.db import get_db
from app.models import Fund

router = APIRouter(prefix="/funds", tags=["基金"])

@router.get("/")
async def get_funds(db: AsyncSession = Depends(get_db)):
    """获取基金列表"""
    result = await db.execute(select(Fund))
    funds = result.scalars().all()
    return {"funds": [{"code": f.code, "name": f.name, "type": f.type} for f in funds]}

@router.get("/{fund_code}")
async def get_fund(fund_code: str, db: AsyncSession = Depends(get_db)):
    """获取单只基金详情"""
    result = await db.execute(select(Fund).where(Fund.code == fund_code))
    fund = result.scalar_one_or_none()
    if not fund:
        return {"error": "基金不存在"}
    return {
        "code": fund.code,
        "name": fund.name,
        "type": fund.type,
        "manager": fund.manager,
        "company": fund.company
    }