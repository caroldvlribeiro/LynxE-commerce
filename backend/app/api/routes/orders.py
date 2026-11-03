from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from redis.asyncio import Redis

from backend.app.db.redis import get_redis
from backend.app.core.auth import CurrentClient, verify_same_origin
from backend.app.repositories.order_repository import OrderRepository
from backend.app.schemas.order import OrderPage, OrderRead, OrderStatusUpdate
from backend.app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


def get_order_service(
    request: Request,
    redis: Annotated[Redis, Depends(get_redis)],
) -> OrderService:
    prefix = request.app.state.settings.redis_key_prefix
    return OrderService(OrderRepository(redis, prefix))


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
)
async def checkout(
    request: Request,
    client: CurrentClient,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderRead:
    verify_same_origin(request)
    return await service.checkout(client.id)


@router.get("", response_model=OrderPage)
async def list_orders(
    client: CurrentClient,
    service: Annotated[OrderService, Depends(get_order_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OrderPage:
    items, total = await service.list_for_client(
        client.id,
        limit=limit,
        offset=offset,
    )
    return OrderPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: UUID,
    client: CurrentClient,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderRead:
    return await service.get(order_id, client.id)


@router.patch("/{order_id}/status", response_model=OrderRead)
async def update_order_status(
    order_id: UUID,
    data: OrderStatusUpdate,
    request: Request,
    client: CurrentClient,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderRead:
    verify_same_origin(request)
    return await service.update_status(order_id, client.id, data)
