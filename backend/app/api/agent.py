"""
Agent API 路由
"""
import asyncio
import json
import time
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.agent.service import agent_service
from app.agent.task_manager import agent_task_manager
from app.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/agent", tags=["Agent"])
_task_owners: dict[str, str] = {}


class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None


@router.post("/analyze")
async def trigger_analysis(user: User = Depends(get_current_user)):
    """Start autonomous analysis in the background and return its task ID."""
    task = agent_task_manager.start(agent_service.stream_portfolio_analysis(user.id))
    _task_owners[task.task_id] = user.id
    return {"status": "started", "task_id": task.task_id}


@router.post("/chat")
async def chat(request: ChatRequest, user: User = Depends(get_current_user)):
    """Stream tool progress and answer tokens for an interactive question."""
    async def events():
        async for event in _events_with_generation_status(
            agent_service.stream_question(request.question, user.id, request.conversation_id)
        ):
            yield _encode_sse(event)
        yield "event: close\ndata: {}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/conversations")
async def create_conversation(user: User = Depends(get_current_user)):
    """Create an empty interactive conversation."""
    return await agent_service.create_conversation(user.id)


@router.get("/conversations")
async def list_conversations(limit: int = 30, user: User = Depends(get_current_user)):
    return {"conversations": await agent_service.list_conversations(user.id, limit)}


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, user: User = Depends(get_current_user)):
    try:
        return await agent_service.get_conversation(user.id, conversation_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/conversations/{conversation_id}/archive")
async def archive_conversation(conversation_id: str, user: User = Depends(get_current_user)):
    try:
        await agent_service.archive_conversation(user.id, conversation_id)
        return {"status": "archived"}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/reports/{analysis_id}")
async def get_analysis_report(analysis_id: int, user: User = Depends(get_current_user)):
    try:
        return await agent_service.get_analysis_report(user.id, analysis_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/analyze/{task_id}")
async def get_analysis_task(task_id: str, user: User = Depends(get_current_user)):
    if _task_owners.get(task_id) != user.id:
        raise HTTPException(status_code=404, detail="Task not found")
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
async def stream_analysis_task(task_id: str, user: User = Depends(get_current_user)):
    if _task_owners.get(task_id) != user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    task = agent_task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    async def events():
        index = 0
        summarizing_started_at: float | None = None
        last_waiting_second = -1
        while True:
            current = agent_task_manager.get(task_id)
            if not current:
                yield _encode_sse({"type": "error", "message": "任务已过期"})
                return
            while index < len(current.events):
                event = current.events[index]
                if event["type"] == "summarizing":
                    summarizing_started_at = time.monotonic()
                yield _encode_sse(event)
                index += 1
            if current.status in {"completed", "failed"}:
                yield "event: close\ndata: {}\n\n"
                return
            if summarizing_started_at is not None:
                elapsed_seconds = int(time.monotonic() - summarizing_started_at)
                if elapsed_seconds > last_waiting_second:
                    last_waiting_second = elapsed_seconds
                    yield _encode_sse({
                        "type": "waiting",
                        "stage": "summarizing",
                        "elapsed_ms": elapsed_seconds * 1000,
                    })
            yield ": keepalive\n\n"
            await asyncio.sleep(0.25)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/history")
async def get_history(limit: int = 10, user: User = Depends(get_current_user)):
    """获取分析历史"""
    try:
        history = await agent_service.get_latest_analysis(user.id, limit)
        return {
            "status": "success",
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _encode_sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"


async def _events_with_generation_status(
    event_stream: AsyncIterator[dict[str, Any]],
) -> AsyncIterator[dict[str, Any]]:
    """Keep chat SSE responsive while an upstream provider waits for its first token."""
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    summarizing_started_at: float | None = None

    async def pump() -> None:
        try:
            async for event in event_stream:
                await queue.put(event)
        finally:
            await queue.put(None)

    pump_task = asyncio.create_task(pump())
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1)
            except asyncio.TimeoutError:
                if summarizing_started_at is not None:
                    yield {
                        "type": "waiting",
                        "stage": "summarizing",
                        "elapsed_ms": round((time.monotonic() - summarizing_started_at) * 1000),
                    }
                else:
                    yield {"type": "keepalive"}
                continue

            if event is None:
                return
            if event["type"] == "summarizing":
                summarizing_started_at = time.monotonic()
            yield event
    finally:
        if not pump_task.done():
            pump_task.cancel()
            await asyncio.gather(pump_task, return_exceptions=True)
