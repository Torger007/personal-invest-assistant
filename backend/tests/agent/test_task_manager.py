import asyncio

from app.agent.task_manager import AgentTaskManager


async def test_task_manager_retains_progress_and_result():
    async def event_stream():
        yield {"type": "tool_started", "name": "get_fund_nav"}
        yield {"type": "complete", "answer": "done"}

    manager = AgentTaskManager()
    task = manager.start(event_stream())
    await asyncio.sleep(0)

    saved_task = manager.get(task.task_id)
    assert saved_task is not None
    assert saved_task.status == "completed"
    assert saved_task.result == "done"
    assert saved_task.events == [
        {"type": "tool_started", "name": "get_fund_nav"},
        {"type": "complete", "answer": "done"},
    ]
