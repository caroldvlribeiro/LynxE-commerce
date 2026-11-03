import asyncio
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.tests.auth_helpers import (
    IntegrationAccount,
    create_test_client,
    create_test_seller,
)
from backend.tests.test_products_api import redis_settings


def test_role_permissions_and_order_ownership(redis_settings: Settings) -> None:
    asyncio.run(_exercise_permissions(redis_settings))


async def _exercise_permissions(settings: Settings) -> None:
    identity = uuid4().hex
    app = create_app(settings)
    accounts: list[IntegrationAccount] = []
    product_id: str | None = None
    category_id: str | None = None
    order_id: str | None = None
    attempted_product = {
        "name": "Tentativa",
        "description": "Teste.",
        "category": f"Permissões {identity}",
        "price": "1.00",
        "stock": 1,
    }
    async with app.router.lifespan_context(app):
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                seller = await create_test_seller(app, settings)
                other_seller = await create_test_seller(app, settings)
                accounts.extend((seller, other_seller))

                assert (
                    await client.post(
                        "/api/v1/products",
                        json=attempted_product,
                    )
                ).status_code == 401
                assert (
                    await client.post(
                        "/api/v1/orders",
                    )
                ).status_code == 401

                buyer = await create_test_client(client)
                other_buyer = await create_test_client(client)
                accounts.extend((buyer, other_buyer))
                await buyer.login(client)
                assert (
                    await client.post(
                        "/api/v1/products",
                        json=attempted_product,
                    )
                ).status_code == 403
                assert (await client.get("/api/v1/carts")).status_code == 200

                await seller.login(client)
                assert (await client.get("/api/v1/carts")).status_code == 403
                category_response = await client.post(
                    "/api/v1/categories",
                    json={"name": f"Permissões {identity}"},
                )
                assert category_response.status_code == 201
                category_id = category_response.json()["id"]
                product_response = await client.post(
                    "/api/v1/products",
                    json={
                        "name": f"Produto protegido {identity}",
                        "description": "Produto de teste de permissões.",
                        "category": f"Permissões {identity}",
                        "price": "8.75",
                        "stock": 3,
                    },
                )
                assert product_response.status_code == 201
                product_id = product_response.json()["id"]
                assert product_response.json()["seller_id"] == seller.id
                assert (
                    await client.get("/api/v1/products/mine")
                ).json()["items"][0]["id"] == product_id
                assert (
                    await client.post("/api/v1/orders")
                ).status_code == 403

                await other_seller.login(client)
                assert (
                    await client.get("/api/v1/products/mine")
                ).json()["total"] == 0
                update_data = {
                    "name": "Tentativa de alteração",
                    "description": "Não deve alterar.",
                    "category": f"Permissões {identity}",
                    "price": "1.00",
                    "stock": 1,
                }
                assert (
                    await client.put(
                        f"/api/v1/products/{product_id}",
                        json=update_data,
                    )
                ).status_code == 404
                assert (
                    await client.delete(f"/api/v1/products/{product_id}")
                ).status_code == 404

                await buyer.login(client)
                assert (
                    await client.get("/api/v1/products/mine")
                ).status_code == 403
                added = await client.post(
                    "/api/v1/carts/items",
                    json={"product_id": product_id, "quantity": 2},
                )
                assert added.status_code == 200
                assert added.json()["total"] == "17.50"
                checkout = await client.post("/api/v1/orders")
                assert checkout.status_code == 201
                order_id = checkout.json()["id"]
                assert checkout.json()["client_id"] == buyer.id

                await other_buyer.login(client)
                assert (
                    await client.get(f"/api/v1/orders/{order_id}")
                ).status_code == 404
                assert (await client.get("/api/v1/orders")).json()["total"] == 0

                await buyer.login(client)
                assert (await client.get("/api/v1/orders")).json()["total"] == 1
                assert (
                    await client.put(
                        f"/api/v1/products/{product_id}",
                        json=update_data,
                    )
                ).status_code == 403
        finally:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as cleanup_client:
                if len(accounts) > 2:
                    buyer_account = accounts[2]
                    await buyer_account.login(cleanup_client)
                    if order_id is not None:
                        await cleanup_client.patch(
                            f"/api/v1/orders/{order_id}/status",
                            json={"status": "cancelled"},
                        )
                if accounts:
                    await accounts[0].login(cleanup_client)
                if product_id is not None:
                    await cleanup_client.delete(
                        f"/api/v1/products/{product_id}"
                    )
                if category_id is not None:
                    await cleanup_client.delete(
                        f"/api/v1/categories/{category_id}"
                    )
                for account in accounts:
                    await app.state.redis.delete(
                        f"{settings.redis_key_prefix}:cart:{account.id}"
                    )
                    await account.cleanup(
                        app.state.redis,
                        settings.redis_key_prefix,
                    )
