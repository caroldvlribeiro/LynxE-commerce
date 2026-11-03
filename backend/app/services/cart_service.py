from uuid import UUID

from fastapi import HTTPException, status

from backend.app.repositories.cart_repository import CartRepository
from backend.app.schemas.cart import CartItemChange, CartRead


class CartService:
    def __init__(self, repository: CartRepository) -> None:
        self.repository = repository

    async def get(self, client_id: UUID) -> CartRead:
        return await self.repository.get(str(client_id))

    async def add_item(
        self,
        client_id: UUID,
        item: CartItemChange,
    ) -> CartRead:
        await self._change_item(client_id, item, add=True)
        return await self.get(client_id)

    async def update_item(
        self,
        client_id: UUID,
        item: CartItemChange,
    ) -> CartRead:
        await self._change_item(client_id, item, add=False)
        return await self.get(client_id)

    async def remove_item(self, client_id: UUID, product_id: UUID) -> CartRead:
        await self.repository.remove_item(str(client_id), str(product_id))
        return await self.get(client_id)

    async def _change_item(
        self,
        client_id: UUID,
        item: CartItemChange,
        *,
        add: bool,
    ) -> None:
        result = await self.repository.change_item(
            str(client_id),
            str(item.product_id),
            item.quantity,
            add=add,
        )
        if result == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found.",
            )
        if result == -1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inactive products cannot be added to the cart.",
            )
        if result == -2:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Requested quantity exceeds available stock.",
            )
