import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from fastapi import Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User, UserSession
from app.services.portfolio_service import seed_default_portfolio
from app.utils.db import AsyncSessionLocal, get_db

_password_hasher = PasswordHasher()


def user_to_dict(user: User) -> dict:
    return {"id": user.id, "username": user.username, "role": user.role}


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHash, VerifyMismatchError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _unauthorized(detail: str = "Authentication required") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


async def get_current_user(
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        raise _unauthorized()

    session = await db.get(UserSession, _token_hash(token))
    now = datetime.utcnow()
    if not session or session.expires_at <= now:
        if session:
            await db.delete(session)
            await db.commit()
        raise _unauthorized("Session expired")

    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
        if not csrf_cookie or not x_csrf_token or not (
            hmac.compare_digest(session.csrf_token, csrf_cookie)
            and hmac.compare_digest(session.csrf_token, x_csrf_token)
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")

    user = await db.get(User, session.user_id)
    if not user or not user.is_active:
        raise _unauthorized("Account unavailable")
    session.last_seen_at = now
    await db.commit()
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user


async def create_session(response: Response, db: AsyncSession, user: User) -> None:
    raw_token = secrets.token_urlsafe(48)
    csrf_token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    db.add(UserSession(
        token_hash=_token_hash(raw_token), user_id=user.id, csrf_token=csrf_token,
        expires_at=now + timedelta(days=settings.SESSION_DAYS), last_seen_at=now,
    ))
    user.last_login_at = now
    await db.commit()
    cookie_options = {
        "max_age": settings.SESSION_DAYS * 24 * 60 * 60,
        "secure": settings.SESSION_SECURE,
        "samesite": "lax",
        "path": "/",
    }
    response.set_cookie(settings.SESSION_COOKIE_NAME, raw_token, httponly=True, **cookie_options)
    response.set_cookie(settings.CSRF_COOKIE_NAME, csrf_token, httponly=False, **cookie_options)


async def revoke_session(request: Request, response: Response, db: AsyncSession) -> None:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if token:
        await db.execute(delete(UserSession).where(UserSession.token_hash == _token_hash(token)))
        await db.commit()
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path="/")


async def provision_bootstrap_admin() -> None:
    username = settings.BOOTSTRAP_ADMIN_USERNAME.strip()
    password = settings.BOOTSTRAP_ADMIN_PASSWORD
    if not username or not password:
        return
    if len(password) < 12:
        raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD must contain at least 12 characters")
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.username == username))
        if user:
            return
        user = User(id=str(uuid4()), username=username, password_hash=hash_password(password), role="admin")
        db.add(user)
        await seed_default_portfolio(db, user.id)
        await db.commit()
