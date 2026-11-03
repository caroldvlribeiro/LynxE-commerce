from uuid import UUID

from fastapi import HTTPException, status

from backend.app.repositories.order_repository import OrderRepository
from backend.app.schemas.order import OrderRead, OrderStatus, OrderStatusUpdate


class OrderService:
    def __init__(self, repository: OrderRepository) -> None:
        self.repository = repository

    async def checkout(self, client_id: UUID) -> OrderRead:
        result, order_id = await self.repository.create_from_cart(client_id)
        if result == -3:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot create an order from an empty cart.",
            )
        if result == -2:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cart changed during checkout; review it and try again.",
            )
        if result == -1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A product is unavailable or no longer has enough stock.",
            )
        if result < 0:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not create the order; please retry.",
            )

        order = await self.repository.get(UUID(order_id))
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Order was created but could not be loaded.",
            )
        return order

    async def get(self, order_id: UUID, client_id: UUID) -> OrderRead:
        order = await self.repository.get(order_id)
        if order is None or order.client_id != client_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found.",
            )
        return order

    async def list_for_client(
        self,
        client_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[OrderRead], int]:
        return await self.repository.list_for_client(
            client_id,
            limit=limit,
            offset=offset,
        )

    async def update_status(
        self,
        order_id: UUID,
        client_id: UUID,
        data: OrderStatusUpdate,
    ) -> OrderRead:
        order = await self.get(order_id, client_id)
        if data.status is OrderStatus.CONFIRMED:
            if order.status is OrderStatus.CANCELLED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A cancelled order cannot be confirmed again.",
                )
            return order

        result = await self.repository.cancel(order)
        if result == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only confirmed orders can be cancelled.",
            )
        if result == -2:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Order stock cannot be restored because a product is missing.",
            )
        if result < 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found.",
            )
        updated = await self.repository.get(order_id)
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Updated order could not be loaded.",
            )
        return updated
