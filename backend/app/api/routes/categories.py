from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from redis.asyncio import Redis

from backend.app.db.redis import get_redis
from backend.app.core.auth import (
    CurrentSeller,
    OptionalUser,
    verify_same_origin,
)
from backend.app.repositories.category_repository import CategoryRepository
from backend.app.schemas.category import (
    CategoryCreate,
    CategoryPage,
    CategoryRead,
    CategoryUpdate,
)
from backend.app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


def get_category_service(
    request: Request,
    redis: Annotated[Redis, Depends(get_redis)],
) -> CategoryService:
    settings = request.app.state.settings
    return CategoryService(CategoryRepository(redis, settings.redis_key_prefix))


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    data: CategoryCreate,
    request: Request,
    seller: CurrentSeller,
    service: Annotated[CategoryService, Depends(get_category_service)],
) -> CategoryRead:
    verify_same_origin(request)
    return await service.create(data, seller)


@router.get("", response_model=CategoryPage)
async def list_categories(
    service: Annotated[CategoryService, Depends(get_category_service)],
    user: OptionalUser,
) -> CategoryPage:
    items = await service.list(user)
    return CategoryPage(items=items, total=len(items))


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: str,
    service: Annotated[CategoryService, Depends(get_category_service)],
) -> CategoryRead:
    return await service.get(category_id)


@router.put("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    request: Request,
    seller: CurrentSeller,
    service: Annotated[CategoryService, Depends(get_category_service)],
) -> CategoryRead:
    verify_same_origin(request)
    return await service.update(category_id, data, seller)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    request: Request,
    seller: CurrentSeller,
    service: Annotated[CategoryService, Depends(get_category_service)],
) -> Response:
    verify_same_origin(request)
    await service.delete(category_id, seller)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
