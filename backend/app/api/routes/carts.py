from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from redis.asyncio import Redis

from backend.app.db.redis import get_redis
from backend.app.core.auth import CurrentClient, verify_same_origin
from backend.app.repositories.cart_repository import CartRepository
from backend.app.repositories.product_repository import ProductRepository
from backend.app.schemas.cart import CartItemChange, CartQuantityUpdate, CartRead
from backend.app.services.cart_service import CartService

router = APIRouter(prefix="/carts", tags=["carts"])


def get_cart_service(
    request: Request,
    redis: Annotated[Redis, Depends(get_redis)],
) -> CartService:
    prefix = request.app.state.settings.redis_key_prefix
    products = ProductRepository(redis, prefix)
    return CartService(CartRepository(redis, prefix, products))


@router.get("", response_model=CartRead)
async def get_cart(
    client: CurrentClient,
    service: Annotated[CartService, Depends(get_cart_service)],
) -> CartRead:
    return await service.get(client.id)


@router.post("/items", response_model=CartRead)
async def add_cart_item(
    item: CartItemChange,
    request: Request,
    client: CurrentClient,
    service: Annotated[CartService, Depends(get_cart_service)],
) -> CartRead:
    verify_same_origin(request)
    return await service.add_item(client.id, item)


@router.put("/items/{product_id}", response_model=CartRead)
async def update_cart_item(
    product_id: UUID,
    data: CartQuantityUpdate,
    request: Request,
    client: CurrentClient,
    service: Annotated[CartService, Depends(get_cart_service)],
) -> CartRead:
    verify_same_origin(request)
    return await service.update_item(
        client.id,
        CartItemChange(product_id=product_id, quantity=data.quantity),
    )


@router.delete(
    "/items/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_cart_item(
    product_id: UUID,
    request: Request,
    client: CurrentClient,
    service: Annotated[CartService, Depends(get_cart_service)],
) -> Response:
    verify_same_origin(request)
    await service.remove_item(client.id, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
