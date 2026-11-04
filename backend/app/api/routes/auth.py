from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from redis.asyncio import Redis

from backend.app.core.auth import (
    SESSION_COOKIE_NAME,
    CurrentUser,
    CurrentSeller,
    verify_same_origin,
)
from backend.app.db.redis import get_redis
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.user import (
    PasswordChange,
    SellerOption,
    SellerProfileUpdate,
    UserLogin,
    UserProfileUpdate,
    UserRead,
    UserRegistration,
)
from backend.app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


def get_auth_service(
    request: Request,
    redis: Annotated[Redis, Depends(get_redis)],
) -> AuthService:
    settings = request.app.state.settings
    return AuthService(
        UserRepository(redis, settings.redis_key_prefix),
        settings.auth_session_ttl_seconds,
    )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_account(
    data: UserRegistration,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserRead:
    verify_same_origin(request)
    return await service.register_account(data)


@router.post("/login", response_model=UserRead)
async def login(
    data: UserLogin,
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserRead:
    verify_same_origin(request)
    user, token = await service.login(str(data.email), data.password)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=request.app.state.settings.auth_cookie_secure,
        samesite="strict",
        max_age=request.app.state.settings.auth_session_ttl_seconds,
        path="/",
    )
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    verify_same_origin(request)
    await service.logout(request.cookies.get(SESSION_COOKIE_NAME))
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=request.app.state.settings.auth_cookie_secure,
        samesite="strict",
        path="/",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUser) -> UserRead:
    return user


@router.get("/sellers", response_model=list[SellerOption])
async def list_sellers(
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> list[SellerOption]:
    return await service.list_sellers()


@router.patch("/profile", response_model=UserRead)
async def update_profile(
    data: UserProfileUpdate,
    request: Request,
    user: CurrentUser,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserRead:
    verify_same_origin(request)
    return await service.update_profile(user, data)


@router.patch("/seller-profile", response_model=UserRead)
async def update_seller_profile(
    data: SellerProfileUpdate,
    request: Request,
    seller: CurrentSeller,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserRead:
    verify_same_origin(request)
    return await service.update_seller_profile(seller, data)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: PasswordChange,
    request: Request,
    response: Response,
    user: CurrentUser,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    verify_same_origin(request)
    await service.change_password(
        user,
        data.current_password,
        data.new_password,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
