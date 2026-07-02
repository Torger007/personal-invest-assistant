from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.utils.db import get_db
from app.models import AdviceRecord
import json
from datetime import date

router = APIRouter(prefix="/advice", tags=["建议"])

@router.get("/")
async def get_advice_list(db: Session = Depends(get_db)):
    """获取建议列表"""
    records = db.query(AdviceRecord).order_by(AdviceRecord.date.desc()).limit(20).all()
    return {
        "advice": [
            {
                "fund_code": r.fund_code,
                "date": str(r.date),
                "overall_signal": r.overall_signal,
                "confidence": float(r.confidence) if r.confidence else None
            }
            for r in records
        ]
    }

@router.get("/{fund_code}")
async def get_fund_advice(fund_code: str, db: Session = Depends(get_db)):
    """获取单只基金的投资建议"""
    record = db.query(AdviceRecord).filter(
        AdviceRecord.fund_code == fund_code
    ).order_by(AdviceRecord.date.desc()).first()

    if not record:
        return {
            "fund_code": fund_code,
            "advice": None,
            "message": "暂无建议记录，请先采集数据并生成建议"
        }

    advice_detail = json.loads(record.advice_text) if record.advice_text else {}
    return {
        "fund_code": fund_code,
        "date": str(record.date),
        "overall_signal": record.overall_signal,
        "confidence": float(record.confidence) if record.confidence else None,
        "scores": {
            "technical": float(record.technical_score) if record.technical_score else None,
            "valuation": float(record.valuation_score) if record.valuation_score else None,
            "fund_flow": float(record.fund_flow_score) if record.fund_flow_score else None,
            "sentiment": float(record.sentiment_score) if record.sentiment_score else None,
        },
        "advice_text": advice_detail
    }