import asyncio
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.tests.auth_helpers import create_test_client, create_test_seller
from backend.tests.test_products_api import redis_settings


def test_cart_crud_stock_validation_and_totals(redis_settings: Settings) -> None:
    asyncio.run(_exercise_cart(redis_settings))


async def _exercise_cart(settings: Settings) -> None:
    identity = uuid4().hex
    category_name = f"Carrinho {identity}"
    app = create_app(settings)
    product_id: str | None = None
    stale_product_id: str | None = None
    category_id: str | None = None
    seller = None
    buyer = None
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
                        "name": f"Produto de carrinho {identity}",
                        "description": "Produto temporário para teste.",
                        "category": category_name,
                        "price": "12.50",
                        "stock": 5,
                    },
                )
                assert product_response.status_code == 201
                product_id = product_response.json()["id"]

                buyer = await create_test_client(client)
                await buyer.login(client)
                client_id = buyer.id
                cart_url = "/api/v1/carts"
                empty_cart = await client.get(cart_url)
                assert empty_cart.status_code == 200
                assert empty_cart.json()["items"] == []
                assert empty_cart.json()["total"] == "0"

                add_url = f"{cart_url}/items"
                first_add = await client.post(
                    add_url,
                    json={"product_id": product_id, "quantity": 2},
                )
                assert first_add.status_code == 200
                assert first_add.json()["total_items"] == 2
                assert first_add.json()["total"] == "25.00"

                second_add = await client.post(
                    add_url,
                    json={"product_id": product_id, "quantity": 2},
                )
                assert second_add.status_code == 200
                assert second_add.json()["items"][0]["quantity"] == 4
                assert second_add.json()["total"] == "50.00"

                too_many = await client.post(
                    add_url,
                    json={"product_id": product_id, "quantity": 2},
                )
                assert too_many.status_code == 409

                updated = await client.put(
                    f"{cart_url}/items/{product_id}",
                    json={"quantity": 5},
                )
                assert updated.status_code == 200
                assert updated.json()["total"] == "62.50"
                assert updated.json()["items"][0]["subtotal"] == "62.50"

                ttl = await app.state.redis.ttl(
                    f"{settings.redis_key_prefix}:cart:{client_id}"
                )
                assert 0 < ttl <= 7 * 24 * 60 * 60

                over_stock = await client.put(
                    f"{cart_url}/items/{product_id}",
                    json={"quantity": 6},
                )
                assert over_stock.status_code == 409

                await seller.login(client)
                inactive_product = await client.put(
                    f"/api/v1/products/{product_id}",
                    json={
                        "name": f"Produto de carrinho {identity}",
                        "description": "Produto temporário para teste.",
                        "category": category_name,
                        "price": "12.50",
                        "stock": 5,
                        "status": "inactive",
                    },
                )
                assert inactive_product.status_code == 200
                await buyer.login(client)
                inactive_cart = await client.get(cart_url)
                assert inactive_cart.json()["has_unavailable_items"] is True
                assert inactive_cart.json()["items"][0]["available"] is False
                assert inactive_cart.json()["total"] == "0.00"
                inactive_add = await client.post(
                    add_url,
                    json={"product_id": product_id, "quantity": 1},
                )
                assert inactive_add.status_code == 409
                deleted_item = await client.delete(
                    f"{cart_url}/items/{product_id}"
                )
                assert deleted_item.status_code == 204
                assert (await client.get(cart_url)).json()["items"] == []

                missing_add = await client.post(
                    add_url,
                    json={"product_id": str(uuid4()), "quantity": 1},
                )
                assert missing_add.status_code == 404

                await seller.login(client)
                stale_product_response = await client.post(
                    "/api/v1/products",
                    json={
                        "name": f"Produto removido {identity}",
                        "description": "Teste de item obsoleto no carrinho.",
                        "category": category_name,
                        "price": "4.00",
                        "stock": 2,
                    },
                )
                assert stale_product_response.status_code == 201
                stale_product_id = stale_product_response.json()["id"]
                await buyer.login(client)
                assert (
                    await client.post(
                        add_url,
                        json={"product_id": stale_product_id, "quantity": 1},
                    )
                ).status_code == 200
                await seller.login(client)
                assert (
                    await client.delete(
                        f"/api/v1/products/{stale_product_id}"
                    )
                ).status_code == 204
                await buyer.login(client)
                stale_cart = await client.get(cart_url)
                assert stale_cart.status_code == 200
                assert stale_cart.json()["has_unavailable_items"] is True
                assert stale_cart.json()["items"][0]["available"] is False
                assert stale_cart.json()["total"] == "0.00"
                assert (
                    await client.delete(
                        f"{cart_url}/items/{stale_product_id}"
                    )
                ).status_code == 204
        finally:
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
                if stale_product_id is not None:
                    await cleanup_client.delete(
                        f"/api/v1/products/{stale_product_id}"
                    )
                if category_id is not None:
                    await cleanup_client.delete(
                        f"/api/v1/categories/{category_id}"
                    )
                if buyer is not None:
                    await app.state.redis.delete(
                        f"{settings.redis_key_prefix}:cart:{buyer.id}"
                    )
                    await buyer.cleanup(
                        app.state.redis,
                        settings.redis_key_prefix,
                    )
                if seller is not None:
                    await seller.cleanup(
                        app.state.redis,
                        settings.redis_key_prefix,
                    )
