from fastapi import APIRouter, BackgroundTasks
from app.services.data_collector.scheduler import manual_refresh
import asyncio

router = APIRouter(prefix="/tasks", tags=["任务"])

# 简易任务状态记录（进程内，重启丢失）
_task_status = {"running": False, "last_result": None}


@router.post("/refresh")
async def manual_refresh_task(background_tasks: BackgroundTasks):
    """手动触发数据更新（后台异步执行）"""
    if _task_status["running"]:
        return {"status": "skipped", "message": "已有更新任务在运行中"}

    async def _run():
        _task_status["running"] = True
        try:
            await manual_refresh()
            _task_status["last_result"] = "success"
        except Exception as e:
            _task_status["last_result"] = f"failed: {e}"
        finally:
            _task_status["running"] = False

    background_tasks.add_task(_run)
    return {"status": "started", "message": "数据更新任务已启动"}


@router.get("/status")
async def get_task_status():
    """获取任务执行状态"""
    return {
        "running": _task_status["running"],
        "last_result": _task_status["last_result"],
        "schedule": "每日16:30自动更新（周一至周五）"
    }