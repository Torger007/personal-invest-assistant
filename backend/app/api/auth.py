from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_session, get_current_user, refresh_session, revoke_session,
    user_to_dict, verify_password,
)
from app.models.user import User
from app.utils.db import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])
_attempts: dict[str, deque[datetime]] = defaultdict(deque)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


def _check_rate_limit(request: Request) -> None:
    key = request.client.host if request.client else "unknown"
    now = datetime.utcnow()
    attempts = _attempts[key]
    while attempts and attempts[0] < now - timedelta(minutes=15):
        attempts.popleft()
    if len(attempts) >= 10:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")
    attempts.append(now)


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    _check_rate_limit(request)
    user = await db.scalar(select(User).where(User.username == payload.username.strip()))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    await create_session(response, request, db, user)
    return {"user": user_to_dict(user)}


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    x_csrf_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    user = await refresh_session(request, response, db, x_csrf_token)
    return {"user": user_to_dict(user)}


@router.post("/logout")
async def logout(request: Request, response: Response, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await revoke_session(request, response, db)
    return {"status": "ok"}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"user": user_to_dict(user)}
