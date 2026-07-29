"""In-process task manager for long-running autonomous agent analyses."""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator


@dataclass
class AgentTask:
    task_id: str
    status: str = "queued"
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    result: str | None = None
    error: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)


class AgentTaskManager:
    """Keep task progress in memory for the single-process deployment."""

    def __init__(self):
        self._tasks: dict[str, AgentTask] = {}

    def start(self, event_stream: AsyncIterator[dict[str, Any]]) -> AgentTask:
        task = AgentTask(task_id=uuid.uuid4().hex)
        self._tasks[task.task_id] = task
        asyncio.create_task(self._run(task, event_stream))
        return task

    async def _run(self, task: AgentTask, event_stream: AsyncIterator[dict[str, Any]]) -> None:
        task.status = "running"
        try:
            async for event in event_stream:
                task.events.append(event)
                if event["type"] == "complete":
                    task.status = "completed"
                    task.result = event["answer"]
                elif event["type"] == "error":
                    task.status = "failed"
                    task.error = event["message"]
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.events.append({"type": "error", "message": str(e)})
        finally:
            task.completed_at = datetime.utcnow()

    def get(self, task_id: str) -> AgentTask | None:
        return self._tasks.get(task_id)


agent_task_manager = AgentTaskManager()
