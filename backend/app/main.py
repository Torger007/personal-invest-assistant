from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import funds, market, advice, tasks
from app.config import settings
from app.utils.db import init_db, close_db

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


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    await init_db()


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时关闭数据库连接"""
    await close_db()


@app.get("/")
async def root():
    return {"message": "个人投资助手 API"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}
