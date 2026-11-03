import asyncio
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.tests.auth_helpers import create_test_client, create_test_seller
from backend.tests.test_products_api import redis_settings


def test_checkout_snapshots_stock_and_cancellation(redis_settings: Settings) -> None:
    asyncio.run(_exercise_checkout(redis_settings))


async def _exercise_checkout(settings: Settings) -> None:
    identity = uuid4().hex
    category_name = f"Pedidos {identity}"
    product_name = f"Produto de pedido {identity}"
    app = create_app(settings)
    product_id: str | None = None
    category_id: str | None = None
    order_id: str | None = None
    seller = None
    buyer = None
    other_client = None

    async with app.router.lifespan_context(app):
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                seller = await create_test_seller(app, settings)
                await seller.login(client)
                category_response = await client.post(
                    "/api/v1/categories",
                    json={"name": category_name},
                )
                assert category_response.status_code == 201
                category_id = category_response.json()["id"]

                product_response = await client.post(
                    "/api/v1/products",
                    json={
                        "name": product_name,
                        "description": "Produto temporário para checkout.",
                        "category": category_name,
                        "price": "12.50",
                        "stock": 5,
                    },
                )
                assert product_response.status_code == 201
                product_id = product_response.json()["id"]

                buyer = await create_test_client(client)
                await buyer.login(client)

                empty_checkout = await client.post("/api/v1/orders")
                assert empty_checkout.status_code == 409

                cart_items = await client.post(
                    "/api/v1/carts/items",
                    json={"product_id": product_id, "quantity": 2},
                )
                assert cart_items.status_code == 200

                checkout = await client.post("/api/v1/orders")
                assert checkout.status_code == 201
                order = checkout.json()
                order_id = order["id"]
                assert order["status"] == "confirmed"
                assert order["total"] == "25.00"
                assert order["items"][0]["unit_price"] == "12.50"
                assert order["items"][0]["quantity"] == 2
                assert (await client.get("/api/v1/carts")).json()[
                    "items"
                ] == []

                product_after_checkout = await client.get(
                    f"/api/v1/products/{product_id}"
                )
                assert product_after_checkout.json()["stock"] == 3

                await seller.login(client)
                changed_product = await client.put(
                    f"/api/v1/products/{product_id}",
                    json={
                        "name": "Nome atualizado após o pedido",
                        "description": "Descrição atualizada.",
                        "category": category_name,
                        "price": "20.00",
                        "stock": 3,
                    },
                )
                assert changed_product.status_code == 200
                await buyer.login(client)

                history = await client.get(f"/api/v1/orders/{order_id}")
                assert history.status_code == 200
                assert history.json()["items"][0]["name"] == product_name
                assert history.json()["items"][0]["unit_price"] == "12.50"

                await seller.login(client)
                blocked_delete = await client.delete(
                    f"/api/v1/products/{product_id}"
                )
                assert blocked_delete.status_code == 409

                await buyer.login(client)
                cancel = await client.patch(
                    f"/api/v1/orders/{order_id}/status",
                    json={"status": "cancelled"},
                )
                assert cancel.status_code == 200
                assert cancel.json()["status"] == "cancelled"
                restored = await client.get(f"/api/v1/products/{product_id}")
                assert restored.json()["stock"] == 5

                duplicate_cancel = await client.patch(
                    f"/api/v1/orders/{order_id}/status",
                    json={"status": "cancelled"},
                )
                assert duplicate_cancel.status_code == 409

                reactivation = await client.patch(
                    f"/api/v1/orders/{order_id}/status",
                    json={"status": "confirmed"},
                )
                assert reactivation.status_code == 409

                listed = await client.get(
                    "/api/v1/orders",
                )
                assert listed.status_code == 200
                assert listed.json()["total"] == 1
                assert listed.json()["items"][0]["id"] == order_id

                other_client = await create_test_client(client)
                await other_client.login(client)
                wrong_owner = await client.get(f"/api/v1/orders/{order_id}")
                assert wrong_owner.status_code == 404

                await seller.login(client)
                assert (
                    await client.delete(f"/api/v1/products/{product_id}")
                ).status_code == 204
                await buyer.login(client)
                persisted_history = await client.get(f"/api/v1/orders/{order_id}")
                assert persisted_history.status_code == 200
                assert persisted_history.json()["items"][0]["name"] == product_name
        finally:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as cleanup_client:
                if buyer is not None:
                    await buyer.login(cleanup_client)
                    await app.state.redis.delete(
                        f"{settings.redis_key_prefix}:cart:{buyer.id}"
                    )
                if order_id is not None:
                    await cleanup_client.patch(
                        f"/api/v1/orders/{order_id}/status",
                        json={"status": "cancelled"},
                    )
                if seller is not None:
                    await seller.login(cleanup_client)
                if product_id is not None:
                    await cleanup_client.delete(
                        f"/api/v1/products/{product_id}"
                    )
                if category_id is not None:
                    await cleanup_client.delete(
                        f"/api/v1/categories/{category_id}"
                    )
                for account in (other_client, buyer, seller):
                    if account is not None:
                        await account.cleanup(
                            app.state.redis,
                            settings.redis_key_prefix,
                        )
