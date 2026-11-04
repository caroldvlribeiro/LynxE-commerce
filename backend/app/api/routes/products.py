from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from redis.asyncio import Redis

from backend.app.db.redis import get_redis
from backend.app.core.auth import CurrentSeller, OptionalUser, verify_same_origin
from backend.app.repositories.category_repository import CategoryRepository
from backend.app.repositories.product_repository import ProductRepository
from backend.app.schemas.product import (
    ProductCreate,
    ProductPage,
    ProductRead,
    ProductUpdate,
)
from backend.app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


def get_product_service(
    request: Request,
    redis: Annotated[Redis, Depends(get_redis)],
) -> ProductService:
    settings = request.app.state.settings
    prefix = settings.redis_key_prefix
    return ProductService(
        ProductRepository(redis, prefix),
        CategoryRepository(redis, prefix),
    )


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    data: ProductCreate,
    request: Request,
    seller: CurrentSeller,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    verify_same_origin(request)
    return await service.create(data, seller)


@router.get("", response_model=ProductPage)
async def list_products(
    service: Annotated[ProductService, Depends(get_product_service)],
    search: Annotated[str | None, Query(max_length=120)] = None,
    category: Annotated[str | None, Query(max_length=80)] = None,
    seller_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProductPage:
    items, total = await service.list(
        search=search,
        category=category,
        seller_id=None,
        seller_filter_id=str(seller_id) if seller_id else None,
        limit=limit,
        offset=offset,
    )
    return ProductPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/mine", response_model=ProductPage)
async def list_my_products(
    seller: CurrentSeller,
    service: Annotated[ProductService, Depends(get_product_service)],
    search: Annotated[str | None, Query(max_length=120)] = None,
    category: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProductPage:
    items, total = await service.list(
        search=search,
        category=category,
        seller_id=str(seller.id),
        seller_filter_id=None,
        limit=limit,
        offset=offset,
    )
    return ProductPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: str,
    user: OptionalUser,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    return await service.get(product_id, user)


@router.put("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: str,
    data: ProductUpdate,
    request: Request,
    seller: CurrentSeller,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRead:
    verify_same_origin(request)
    return await service.update(product_id, data, seller)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    request: Request,
    seller: CurrentSeller,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> Response:
    verify_same_origin(request)
    await service.delete(product_id, seller)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
