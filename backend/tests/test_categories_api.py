import asyncio
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.tests.auth_helpers import create_test_seller
from backend.tests.test_products_api import redis_settings


def test_category_crud_and_duplicate_name(redis_settings: Settings) -> None:
    asyncio.run(_exercise_category_crud(redis_settings))


async def _exercise_category_crud(settings: Settings) -> None:
    name = f"Categoria {uuid4()}"
    updated_name = f"Categoria atualizada {uuid4()}"
    app = create_app(settings)
    category_ids: list[str] = []
    seller = None

    try:
        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                seller = await create_test_seller(app, settings)
                await seller.login(client)
                created_response = await client.post(
                    "/api/v1/categories",
                    json={"name": name, "description": "Categoria de teste."},
                )
                assert created_response.status_code == 201
                created = created_response.json()
                category_id = created["id"]
                category_ids.append(category_id)
                assert created["name"] == name

                duplicate = await client.post(
                    "/api/v1/categories",
                    json={"name": name.swapcase()},
                )
                assert duplicate.status_code == 409

                second_category_response = await client.post(
                    "/api/v1/categories",
                    json={"name": updated_name},
                )
                assert second_category_response.status_code == 201
                second_category_id = second_category_response.json()["id"]
                category_ids.append(second_category_id)

                duplicate_update = await client.put(
                    f"/api/v1/categories/{category_id}",
                    json={"name": updated_name},
                )
                assert duplicate_update.status_code == 409

                fetched = await client.get(f"/api/v1/categories/{category_id}")
                assert fetched.status_code == 200
                assert fetched.json() == created

                listed = await client.get("/api/v1/categories")
                assert listed.status_code == 200
                assert any(
                    category["id"] == category_id
                    for category in listed.json()["items"]
                )

                final_name = f"Categoria final {uuid4()}"
                updated = await client.put(
                    f"/api/v1/categories/{category_id}",
                    json={
                        "name": final_name,
                        "description": "Descrição atualizada.",
                    },
                )
                assert updated.status_code == 200
                assert updated.json()["name"] == final_name
                assert updated.json()["description"] == "Descrição atualizada."

                for category_to_delete in category_ids:
                    deleted = await client.delete(
                        f"/api/v1/categories/{category_to_delete}"
                    )
                    assert deleted.status_code == 204
                assert (
                    await client.get(f"/api/v1/categories/{category_id}")
                ).status_code == 404
    finally:
        if category_ids or seller is not None:
            async with app.router.lifespan_context(app):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as cleanup_client:
                    if seller is not None:
                        await seller.login(cleanup_client)
                    for category_to_delete in category_ids:
                        await cleanup_client.delete(
                            f"/api/v1/categories/{category_to_delete}"
                        )
                    if seller is not None:
                        await seller.cleanup(
                            app.state.redis,
                            settings.redis_key_prefix,
                        )
