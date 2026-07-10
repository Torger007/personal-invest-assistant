"""
Agent API 路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agent.service import agent_service

router = APIRouter(prefix="/agent", tags=["Agent"])


class ChatRequest(BaseModel):
    question: str


@router.post("/analyze")
async def trigger_analysis():
    """触发自主分析：分析用户持仓基金，生成投资建议"""
    try:
        result = await agent_service.analyze_portfolio()
        return {
            "status": "success",
            "message": "分析完成",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat(request: ChatRequest):
    """问答交互：回答用户投资问题"""
    try:
        result = await agent_service.ask_question(request.question)
        return {
            "status": "success",
            "answer": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history(limit: int = 10):
    """获取分析历史"""
    try:
        history = await agent_service.get_latest_analysis(limit)
        return {
            "status": "success",
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))