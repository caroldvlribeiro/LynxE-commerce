from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


def _strip_required_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("This field must not be blank.")
    return value


class ProductFields(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, max_length=120)]
    description: Annotated[str, Field(min_length=1, max_length=2000)]
    category: Annotated[str, Field(min_length=1, max_length=80)]
    price: Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
    stock: Annotated[int, Field(ge=0, le=1_000_000)]
    image_url: Annotated[str | None, Field(max_length=2048)] = None
    status: ProductStatus = ProductStatus.ACTIVE

    @field_validator("name", "description", "category")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        return _strip_required_text(value)

    @field_validator("image_url")
    @classmethod
    def image_path_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("image_url must be omitted or contain a path or URL.")
        return value


class ProductCreate(ProductFields):
    pass


class ProductUpdate(ProductFields):
    pass


class ProductRead(ProductFields):
    id: str
    created_at: datetime
    seller_id: UUID | None = None


class ProductPage(BaseModel):
    items: list[ProductRead]
    total: int
    limit: int
    offset: int
