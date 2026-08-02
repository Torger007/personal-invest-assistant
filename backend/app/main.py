from app.startup_patch import *  # noqa: F401,F403

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import advice, agent, funds, market, tasks
from app.api import auth as auth_api
from app.auth import get_current_user, provision_bootstrap_admin, require_admin
from app.config import settings
from app.services.data_collector.scheduler import start_scheduler, stop_scheduler
from app.utils.db import close_db, run_migrations

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_api.router, prefix=settings.API_PREFIX)
app.include_router(funds.router, prefix=settings.API_PREFIX, dependencies=[Depends(get_current_user)])
app.include_router(market.router, prefix=settings.API_PREFIX, dependencies=[Depends(get_current_user)])
app.include_router(advice.router, prefix=settings.API_PREFIX, dependencies=[Depends(get_current_user)])
app.include_router(agent.router, prefix=settings.API_PREFIX, dependencies=[Depends(get_current_user)])
app.include_router(tasks.router, prefix=settings.API_PREFIX, dependencies=[Depends(require_admin)])


@app.on_event("startup")
async def startup_event():
    if settings.RUN_MIGRATIONS_ON_STARTUP:
        await run_migrations()
    await provision_bootstrap_admin()
    if settings.SCHEDULER_ENABLED:
        start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    stop_scheduler()
    await close_db()


@app.get("/")
async def root():
    return {"message": "Personal Investment Assistant API"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}
