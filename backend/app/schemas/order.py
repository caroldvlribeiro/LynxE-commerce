from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


class OrderStatus(StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemRead(BaseModel):
    product_id: UUID
    name: str
    category: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    image_url: str | None


class OrderRead(BaseModel):
    id: UUID
    client_id: UUID
    status: OrderStatus
    items: list[OrderItemRead]
    total: Decimal
    created_at: datetime
    cancelled_at: datetime | None = None


class OrderPage(BaseModel):
    items: list[OrderRead]
    total: int
    limit: int
    offset: int


OrderLimit = Annotated[int, Field(ge=1, le=100)]
