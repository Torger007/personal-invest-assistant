from datetime import datetime

from fastapi import APIRouter, BackgroundTasks
from app.services.data_collector.scheduler import manual_refresh
from app.services.data_collector.fund_catalog import get_catalog_status, sync_fund_catalog
from app.utils.db import AsyncSessionLocal
import asyncio

router = APIRouter(prefix="/tasks", tags=["任务"])

# 简易任务状态记录（进程内，重启丢失）
_task_status = {"running": False, "last_result": None, "started_at": None}
_catalog_task_status = {"running": False, "last_result": None, "started_at": None}


@router.post("/refresh")
async def manual_refresh_task(background_tasks: BackgroundTasks):
    """手动触发数据更新（后台异步执行）"""
    if _task_status["running"]:
        return {"status": "skipped", "message": "已有更新任务在运行中"}

    _task_status["running"] = True
    _task_status["started_at"] = datetime.now().isoformat(timespec="seconds")
    _task_status["last_result"] = None

    async def _run():
        try:
            _task_status["last_result"] = await manual_refresh()
        except Exception as e:
            _task_status["last_result"] = {
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now().isoformat(timespec="seconds"),
            }
        finally:
            _task_status["running"] = False

    background_tasks.add_task(_run)
    return {"status": "started", "message": "数据更新任务已启动"}


@router.get("/status")
async def get_task_status():
    """获取任务执行状态"""
    return {
        "running": _task_status["running"],
        "started_at": _task_status["started_at"],
        "last_result": _task_status["last_result"],
        "schedule": "每日16:30自动更新（周一至周五）"
    }


@router.post("/fund-catalog/sync")
async def sync_fund_catalog_task(background_tasks: BackgroundTasks):
    """Trigger a catalog refresh without ever blocking a browser search request."""
    if _catalog_task_status["running"]:
        return {"status": "skipped", "message": "基金目录同步任务正在运行中"}

    _catalog_task_status["running"] = True
    _catalog_task_status["started_at"] = datetime.now().isoformat(timespec="seconds")
    _catalog_task_status["last_result"] = None

    async def _run():
        try:
            _catalog_task_status["last_result"] = await sync_fund_catalog()
        finally:
            _catalog_task_status["running"] = False

    background_tasks.add_task(_run)
    return {"status": "started", "message": "基金目录同步任务已启动"}


@router.get("/fund-catalog/status")
async def fund_catalog_status():
    async with AsyncSessionLocal() as session:
        status = await get_catalog_status(session)
    return {**status, "running": _catalog_task_status["running"]}
