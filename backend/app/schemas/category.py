from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryFields(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, max_length=80)]
    description: Annotated[str, Field(max_length=500)] = ""

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("Category name must not be blank.")
        return value


class CategoryCreate(CategoryFields):
    pass


class CategoryUpdate(CategoryFields):
    pass


class CategoryRead(CategoryFields):
    id: str
    created_at: datetime
    seller_id: UUID | None = None


class CategoryPage(BaseModel):
    items: list[CategoryRead]
    total: int
