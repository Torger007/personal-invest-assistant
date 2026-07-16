# 启动补丁：必须在所有其他 import 之前执行
# 解决 akshare 访问东方财富等网站的 TLS 连接问题
from app.startup_patch import *

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import funds, market, advice, tasks, agent
from app.config import settings
from app.utils.db import close_db, run_migrations
from app.services.data_collector.scheduler import start_scheduler, stop_scheduler

app = FastAPI(
    title=settings.APP_NAME,
    description="轻量化投资分析系统",
    version=settings.APP_VERSION
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(funds.router, prefix=settings.API_PREFIX)
app.include_router(market.router, prefix=settings.API_PREFIX)
app.include_router(advice.router, prefix=settings.API_PREFIX)
app.include_router(tasks.router, prefix=settings.API_PREFIX)
app.include_router(agent.router, prefix=settings.API_PREFIX)


@app.on_event("startup")
async def startup_event():
    """应用启动时执行数据库迁移并启动调度器"""
    await run_migrations()
    start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时停止调度器并关闭数据库连接"""
    stop_scheduler()
    await close_db()


@app.get("/")
async def root():
    return {"message": "个人投资助手 API"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}