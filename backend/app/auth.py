import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from fastapi import Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User, UserSession
from app.services.portfolio_service import seed_default_portfolio
from app.utils.db import AsyncSessionLocal, get_db

_password_hasher = PasswordHasher()
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


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


def _now() -> datetime:
    return datetime.utcnow()


def _jwt_secret() -> str:
    if len(settings.JWT_SECRET) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT_SECRET must contain at least 32 characters",
        )
    return settings.JWT_SECRET


def _unauthorized(detail: str = "Authentication required") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _verify_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return
    configured = settings.CSRF_TRUSTED_ORIGINS or settings.CORS_ORIGINS
    trusted_origins = {value.strip() for value in configured.split(",") if value.strip()}
    if origin not in trusted_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Untrusted request origin")


def _cookie_options(max_age: int, *, path: str, samesite: str = "lax") -> dict:
    return {
        "max_age": max_age,
        "secure": settings.SESSION_SECURE,
        "samesite": samesite,
        "path": path,
    }


def _access_payload(user: User, family_id: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "sub": user.id,
        "role": user.role,
        "sid": family_id,
        "jti": str(uuid4()),
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }


def _create_access_token(user: User, family_id: str) -> str:
    return jwt.encode(_access_payload(user, family_id), _jwt_secret(), algorithm="HS256")


def _decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            _jwt_secret(),
            algorithms=["HS256"],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={"require": ["sub", "sid", "jti", "exp", "iat"]},
        )
    except jwt.ExpiredSignatureError as error:
        raise _unauthorized("Access token expired") from error
    except jwt.InvalidTokenError as error:
        raise _unauthorized("Invalid access token") from error


def _set_access_cookie(response: Response, user: User, family_id: str) -> None:
    response.set_cookie(
        settings.ACCESS_TOKEN_COOKIE_NAME,
        _create_access_token(user, family_id),
        httponly=True,
        **_cookie_options(settings.ACCESS_TOKEN_MINUTES * 60, path="/"),
    )


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        settings.REFRESH_TOKEN_COOKIE_NAME,
        refresh_token,
        httponly=True,
        **_cookie_options(
            settings.REFRESH_TOKEN_DAYS * 24 * 60 * 60,
            path=f"{settings.API_PREFIX}/auth/refresh",
            samesite="strict",
        ),
    )


def _set_csrf_cookie(response: Response, csrf_token: str) -> None:
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        csrf_token,
        httponly=False,
        **_cookie_options(settings.REFRESH_TOKEN_DAYS * 24 * 60 * 60, path="/", samesite="lax"),
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.ACCESS_TOKEN_COOKIE_NAME, path="/")
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE_NAME, path=f"{settings.API_PREFIX}/auth/refresh")
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path="/")


async def _active_family_session(db: AsyncSession, user_id: str, family_id: str) -> UserSession | None:
    return await db.scalar(
        select(UserSession)
        .where(UserSession.user_id == user_id)
        .where(UserSession.family_id == family_id)
        .where(UserSession.revoked_at.is_(None))
        .where(UserSession.expires_at > _now())
        .order_by(UserSession.created_at.desc())
        .limit(1)
    )


async def _verify_csrf(
    request: Request, db: AsyncSession, user_id: str, family_id: str, header_token: str | None,
) -> None:
    _verify_origin(request)
    cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME)
    session = await _active_family_session(db, user_id, family_id)
    if not session or not cookie_token or not header_token or not (
        hmac.compare_digest(session.csrf_token, cookie_token)
        and hmac.compare_digest(session.csrf_token, header_token)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")


async def get_current_user(
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = request.cookies.get(settings.ACCESS_TOKEN_COOKIE_NAME)
    if not token:
        raise _unauthorized()
    payload = _decode_access_token(token)
    user_id = str(payload["sub"])
    family_id = str(payload["sid"])

    if request.method in _UNSAFE_METHODS:
        await _verify_csrf(request, db, user_id, family_id, x_csrf_token)

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise _unauthorized("Account unavailable")
    request.state.access_payload = payload
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user


async def create_session(response: Response, request: Request, db: AsyncSession, user: User) -> None:
    refresh_token = secrets.token_urlsafe(48)
    csrf_token = secrets.token_urlsafe(32)
    family_id = str(uuid4())
    now = _now()
    db.add(UserSession(
        token_hash=_token_hash(refresh_token), user_id=user.id, family_id=family_id,
        csrf_token=csrf_token, expires_at=now + timedelta(days=settings.REFRESH_TOKEN_DAYS),
        last_seen_at=now, user_agent=request.headers.get("user-agent"), ip_address=_client_ip(request),
    ))
    user.last_login_at = now
    await db.commit()
    _set_access_cookie(response, user, family_id)
    _set_refresh_cookie(response, refresh_token)
    _set_csrf_cookie(response, csrf_token)


async def refresh_session(
    request: Request, response: Response, db: AsyncSession, x_csrf_token: str | None,
) -> User:
    raw_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if not raw_token:
        raise _unauthorized("Refresh token missing")
    token_hash = _token_hash(raw_token)
    session = await db.get(UserSession, token_hash)
    now = _now()
    if not session or session.expires_at <= now:
        raise _unauthorized("Refresh token expired")
    if session.revoked_at:
        if session.family_id:
            await revoke_family(db, session.family_id)
            await db.commit()
        raise _unauthorized("Refresh token reuse detected")
    _verify_origin(request)
    cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME)
    if not cookie_token or not x_csrf_token or not (
        hmac.compare_digest(session.csrf_token, cookie_token)
        and hmac.compare_digest(session.csrf_token, x_csrf_token)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
    user = await db.get(User, session.user_id)
    if not user or not user.is_active:
        raise _unauthorized("Account unavailable")

    new_refresh_token = secrets.token_urlsafe(48)
    new_hash = _token_hash(new_refresh_token)
    new_csrf_token = secrets.token_urlsafe(32)
    session.revoked_at = now
    session.replaced_by_hash = new_hash
    session.last_seen_at = now
    db.add(UserSession(
        token_hash=new_hash, user_id=user.id, family_id=session.family_id,
        csrf_token=new_csrf_token, expires_at=now + timedelta(days=settings.REFRESH_TOKEN_DAYS),
        last_seen_at=now, user_agent=request.headers.get("user-agent"), ip_address=_client_ip(request),
    ))
    await db.commit()
    _set_access_cookie(response, user, session.family_id)
    _set_refresh_cookie(response, new_refresh_token)
    _set_csrf_cookie(response, new_csrf_token)
    return user


async def revoke_family(db: AsyncSession, family_id: str) -> None:
    await db.execute(
        update(UserSession)
        .where(UserSession.family_id == family_id)
        .where(UserSession.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


async def revoke_session(request: Request, response: Response, db: AsyncSession) -> None:
    payload = getattr(request.state, "access_payload", None)
    family_id = payload.get("sid") if payload else None
    if family_id:
        await revoke_family(db, str(family_id))
        await db.commit()
    _clear_auth_cookies(response)


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
