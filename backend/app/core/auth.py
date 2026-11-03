from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyCookie
from redis.asyncio import Redis

from backend.app.db.redis import get_redis
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.user import UserCredentials, UserRole, UserStatus

SESSION_COOKIE_NAME = "viva_session"
session_cookie = APIKeyCookie(
    name=SESSION_COOKIE_NAME,
    scheme_name="RedisSessionCookie",
    description="Opaque session cookie set by POST /api/v1/auth/login.",
    auto_error=False,
)


async def get_current_user(
    request: Request,
    redis: Annotated[Redis, Depends(get_redis)],
    token: Annotated[str | None, Depends(session_cookie)],
) -> UserCredentials:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Cookie"},
        )
    repository = UserRepository(
        redis,
        request.app.state.settings.redis_key_prefix,
    )
    user = await repository.get_session_user(token)
    if user is None or user.status is not UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication session is invalid or expired.",
            headers={"WWW-Authenticate": "Cookie"},
        )
    return user


async def get_optional_current_user(
    request: Request,
    redis: Annotated[Redis, Depends(get_redis)],
) -> UserCredentials | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    repository = UserRepository(
        redis,
        request.app.state.settings.redis_key_prefix,
    )
    user = await repository.get_session_user(token)
    if user is None or user.status is not UserStatus.ACTIVE:
        return None
    return user


def require_role(*roles: UserRole):
    async def role_guard(
        user: Annotated[UserCredentials, Depends(get_current_user)],
    ) -> UserCredentials:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account does not have permission for this operation.",
            )
        return user

    return role_guard


CurrentUser = Annotated[UserCredentials, Depends(get_current_user)]
OptionalUser = Annotated[UserCredentials | None, Depends(get_optional_current_user)]
CurrentClient = Annotated[UserCredentials, Depends(require_role(UserRole.CLIENT))]
CurrentSeller = Annotated[UserCredentials, Depends(require_role(UserRole.SELLER))]


def verify_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin is None:
        return
    if origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-origin state-changing requests are not allowed.",
        )
