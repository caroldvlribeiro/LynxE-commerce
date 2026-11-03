import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class UserRole(StrEnum):
    CLIENT = "client"
    SELLER = "seller"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


def _validate_password_strength(value: str) -> str:
    if not (
        re.search(r"[a-z]", value)
        and re.search(r"[A-Z]", value)
        and re.search(r"\d", value)
    ):
        raise ValueError(
            "Password must include uppercase and lowercase letters and a number."
        )
    return value


def _validate_business_phone(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    digits = re.sub(r"\D", "", normalized)
    if not re.fullmatch(r"[+()0-9 .-]{8,30}", normalized) or not 8 <= len(digits) <= 15:
        raise ValueError("Enter a valid business phone number.")
    return normalized


class UserRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: Annotated[str, Field(min_length=2, max_length=120)]
    email: EmailStr
    password: Annotated[str, Field(min_length=12, max_length=128)]
    role: UserRole = UserRole.CLIENT
    store_name: Annotated[str | None, Field(min_length=2, max_length=120)] = None
    store_description: Annotated[str | None, Field(min_length=2, max_length=1000)] = None
    business_phone: Annotated[str | None, Field(max_length=30)] = None

    @field_validator("full_name")
    @classmethod
    def full_name_must_not_be_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("Full name must not be blank.")
        return value

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, value: str) -> str:
        return _validate_password_strength(value)

    @field_validator("store_name", "store_description")
    @classmethod
    def store_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("This field must not be blank.")
        return value

    @field_validator("business_phone")
    @classmethod
    def business_phone_must_be_valid(cls, value: str | None) -> str | None:
        return _validate_business_phone(value)

    @model_validator(mode="after")
    def seller_details_are_required(self) -> "UserRegistration":
        if self.role is UserRole.SELLER and (
            self.store_name is None or self.store_description is None
        ):
            raise ValueError(
                "Store name and description are required for seller accounts."
            )
        if self.role is UserRole.CLIENT and any(
            value is not None
            for value in (self.store_name, self.store_description, self.business_phone)
        ):
            raise ValueError("Store details are only valid for seller accounts.")
        return self


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: Annotated[str | None, Field(min_length=2, max_length=120)] = None
    email: EmailStr | None = None

    @field_validator("full_name")
    @classmethod
    def full_name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("Full name must not be blank.")
        return value

    @model_validator(mode="after")
    def at_least_one_field_is_required(self) -> "UserProfileUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one profile field to update.")
        return self


class SellerProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    store_name: Annotated[str | None, Field(min_length=2, max_length=120)] = None
    store_description: Annotated[str | None, Field(min_length=2, max_length=1000)] = None
    business_phone: Annotated[str | None, Field(max_length=30)] = None

    @field_validator("store_name", "store_description")
    @classmethod
    def store_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("This field must not be blank.")
        return value

    @field_validator("business_phone")
    @classmethod
    def business_phone_must_be_valid(cls, value: str | None) -> str | None:
        return _validate_business_phone(value)

    @model_validator(mode="after")
    def at_least_one_field_is_required(self) -> "SellerProfileUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one store field to update.")
        return self


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: Annotated[str, Field(min_length=1, max_length=128)]
    new_password: Annotated[str, Field(min_length=12, max_length=128)]

    @field_validator("new_password")
    @classmethod
    def password_must_be_strong(cls, value: str) -> str:
        return _validate_password_strength(value)


class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=128)]


class UserRead(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    role: UserRole
    status: UserStatus
    created_at: datetime
    store_name: str | None = None
    store_description: str | None = None
    business_phone: str | None = None


class UserCredentials(UserRead):
    password_hash: str
