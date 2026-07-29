"""
Agent API 路由
"""
import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.agent.service import agent_service
from app.agent.task_manager import agent_task_manager

router = APIRouter(prefix="/agent", tags=["Agent"])


class ChatRequest(BaseModel):
    question: str


@router.post("/analyze")
async def trigger_analysis():
    """Start autonomous analysis in the background and return its task ID."""
    task = agent_task_manager.start(agent_service.stream_portfolio_analysis())
    return {"status": "started", "task_id": task.task_id}


@router.post("/chat")
async def chat(request: ChatRequest):
    """Stream tool progress and answer tokens for an interactive question."""
    async def events():
        async for event in agent_service.stream_question(request.question):
            yield _encode_sse(event)
        yield "event: close\ndata: {}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/analyze/{task_id}")
async def get_analysis_task(task_id: str):
    task = agent_task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    return {
        "task_id": task.task_id,
        "status": task.status,
        "result": task.result,
        "error": task.error,
        "created_at": task.created_at.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


@router.get("/analyze/{task_id}/events")
async def stream_analysis_task(task_id: str):
    task = agent_task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    async def events():
        index = 0
        while True:
            current = agent_task_manager.get(task_id)
            if not current:
                yield _encode_sse({"type": "error", "message": "任务已过期"})
                return
            while index < len(current.events):
                yield _encode_sse(current.events[index])
                index += 1
            if current.status in {"completed", "failed"}:
                yield "event: close\ndata: {}\n\n"
                return
            yield ": keepalive\n\n"
            await asyncio.sleep(0.25)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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


def _encode_sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
