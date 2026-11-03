from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings
from backend.app.schemas.product import ProductCreate, ProductStatus


def test_product_schema_trims_text_and_applies_defaults() -> None:
    product = ProductCreate(
        name="  Caneca  ",
        description=" Cerâmica ",
        category=" Casa ",
        price="19.90",
        stock=3,
    )

    assert product.name == "Caneca"
    assert product.description == "Cerâmica"
    assert product.category == "Casa"
    assert product.price == Decimal("19.90")
    assert product.status is ProductStatus.ACTIVE


def test_redis_settings_build_tls_url_from_connection_fields() -> None:
    settings = Settings(
        _env_file=None,
        redis_host="redis.example.test",
        redis_port=12345,
        redis_username="user@example",
        redis_password="p@ssword",
    )

    assert settings.require_redis_url() == (
        "redis://user%40example:p%40ssword@redis.example.test:12345"
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "  "},
        {"description": ""},
        {"category": " "},
        {"price": "0"},
        {"price": "-2.00"},
        {"price": "1.999"},
        {"stock": -1},
    ],
)
def test_product_schema_rejects_invalid_values(
    overrides: dict[str, object],
) -> None:
    data: dict[str, object] = {
        "name": "Caneca",
        "description": "Cerâmica",
        "category": "Casa",
        "price": "19.90",
        "stock": 3,
    }
    data.update(overrides)

    with pytest.raises(ValidationError):
        ProductCreate(**data)
