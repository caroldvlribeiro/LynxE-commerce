import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.tests.auth_helpers import create_test_seller


@pytest.fixture
def redis_settings() -> Settings:
    settings = Settings()
    if settings.redis_url is None and settings.redis_host is None:
        pytest.skip("Configure Redis Cloud in .env to run integration tests.")
    settings.require_redis_url()
    return settings


def test_product_crud_and_redis_persistence(redis_settings: Settings) -> None:
    asyncio.run(_exercise_product_crud(redis_settings))


async def _exercise_product_crud(redis_settings: Settings) -> None:
    client_id = str(uuid4())
    original_category_name = f"Teste {client_id}"
    updated_category_name = f"Categoria atualizada {client_id}"
    product_data = {
        "name": f"Produto de teste {client_id}",
        "description": "Registro temporário para teste de integração.",
        "category": original_category_name,
        "price": "25.90",
        "stock": 8,
        "image_url": "/images/test-product.png",
        "status": "active",
    }

    product_id: str | None = None
    category_ids: list[str] = []
    seller = None
    app = create_app(redis_settings)
    try:
        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                seller = await create_test_seller(app, redis_settings)
                await seller.login(client)
                category_response = await client.post(
                    "/api/v1/categories",
                    json={"name": original_category_name},
                )
                assert category_response.status_code == 201
                category_ids.append(category_response.json()["id"])
                created_response = await client.post(
                    "/api/v1/products", json=product_data
                )
                assert created_response.status_code == 201
                created = created_response.json()
                product_id = created["id"]
                assert created["price"] == "25.90"
                assert created["stock"] == 8
                assert (
                    await client.get(f"/api/v1/products/{product_id}")
                ).json() == created

                listing = await client.get(
                    "/api/v1/products",
                    params={
                        "search": product_data["name"],
                        "category": product_data["category"],
                    },
                )
                assert listing.status_code == 200
                assert listing.json()["total"] == 1
                assert listing.json()["items"][0]["id"] == product_id

                rename_category = await client.put(
                    f"/api/v1/categories/{category_ids[0]}",
                    json={
                        "name": f"Nome revisado {client_id}",
                        "description": "Renomeada durante teste.",
                    },
                )
                assert rename_category.status_code == 200
                renamed_name = rename_category.json()["name"]
                renamed_product = await client.get(
                    f"/api/v1/products/{product_id}"
                )
                assert renamed_product.json()["category"] == renamed_name

                blocked_delete = await client.delete(
                    f"/api/v1/categories/{category_ids[0]}"
                )
                assert blocked_delete.status_code == 409

        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as second_client:
                assert seller is not None
                await seller.login(second_client)
                persisted = await second_client.get(
                    f"/api/v1/products/{product_id}"
                )
                assert persisted.status_code == 200
                assert persisted.json()["name"] == product_data["name"]

                new_category_response = await second_client.post(
                    "/api/v1/categories",
                    json={"name": updated_category_name},
                )
                assert new_category_response.status_code == 201
                category_ids.append(new_category_response.json()["id"])

                updated_data = {
                    **product_data,
                    "name": f"Produto atualizado {client_id}",
                    "category": updated_category_name,
                    "price": "31.50",
                    "stock": 4,
                }
                updated = await second_client.put(
                    f"/api/v1/products/{product_id}",
                    json=updated_data,
                )
                assert updated.status_code == 200
                assert updated.json()["price"] == "31.50"
                assert updated.json()["stock"] == 4

                old_category = await second_client.get(
                    "/api/v1/products",
                    params={"category": original_category_name},
                )
                renamed_category = await second_client.get(
                    "/api/v1/products",
                    params={"category": renamed_name},
                )
                new_category = await second_client.get(
                    "/api/v1/products",
                    params={"category": updated_data["category"]},
                )
                assert all(
                    item["id"] != product_id
                    for item in old_category.json()["items"]
                )
                assert all(
                    item["id"] != product_id
                    for item in renamed_category.json()["items"]
                )
                assert any(
                    item["id"] == product_id
                    for item in new_category.json()["items"]
                )

                deleted = await second_client.delete(
                    f"/api/v1/products/{product_id}"
                )
                assert deleted.status_code == 204
                blocked_delete = await second_client.delete(
                    f"/api/v1/categories/{category_ids[1]}"
                )
                assert blocked_delete.status_code == 204
                missing = await second_client.get(
                    f"/api/v1/products/{product_id}"
                )
                assert missing.status_code == 404
                for category_id in category_ids:
                    category_deleted = await second_client.delete(
                        f"/api/v1/categories/{category_id}"
                    )
                    assert category_deleted.status_code in {204, 404}
    finally:
        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as cleanup_client:
                if seller is not None:
                    await seller.login(cleanup_client)
                if product_id is not None:
                    await cleanup_client.delete(
                        f"/api/v1/products/{product_id}"
                    )
                for category_id in category_ids:
                    await cleanup_client.delete(
                        f"/api/v1/categories/{category_id}"
                    )
                if seller is not None:
                    await seller.cleanup(
                        app.state.redis,
                        redis_settings.redis_key_prefix,
                    )


def test_product_api_rejects_invalid_input(redis_settings: Settings) -> None:
    asyncio.run(_reject_invalid_product(redis_settings))


async def _reject_invalid_product(settings: Settings) -> None:
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            seller = await create_test_seller(app, settings)
            await seller.login(client)
            response = await client.post(
                "/api/v1/products",
                json={
                    "name": "Produto inválido",
                    "description": "Descrição",
                    "category": "Teste",
                    "price": "-1",
                    "stock": -1,
                },
            )
            unknown_category = await client.post(
                "/api/v1/products",
                json={
                    "name": "Produto sem categoria cadastrada",
                    "description": "Descrição válida",
                    "category": f"Inexistente {uuid4()}",
                    "price": "1.00",
                    "stock": 1,
                },
            )
            await seller.cleanup(app.state.redis, settings.redis_key_prefix)
    assert response.status_code == 422
    assert unknown_category.status_code == 422
