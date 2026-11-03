from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


class CartItemChange(BaseModel):
    product_id: UUID
    quantity: Annotated[int, Field(ge=1, le=1_000_000)]


class CartQuantityUpdate(BaseModel):
    quantity: Annotated[int, Field(ge=1, le=1_000_000)]


class CartItemRead(BaseModel):
    product_id: UUID
    name: str
    category: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    image_url: str | None
    available: bool = True


class CartRead(BaseModel):
    client_id: UUID
    items: list[CartItemRead]
    total_items: int
    total: Decimal
    has_unavailable_items: bool = False
