import asyncio
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.app.schemas.user import UserRead, UserRole
from backend.tests.auth_helpers import (
    IntegrationAccount,
    create_test_client,
)
from backend.tests.test_products_api import redis_settings


def test_registration_and_role_specific_profiles(redis_settings: Settings) -> None:
    asyncio.run(_exercise_registration_and_profiles(redis_settings))


async def _exercise_registration_and_profiles(settings: Settings) -> None:
    identity = uuid4().hex
    app = create_app(settings)
    accounts: list[IntegrationAccount] = []
    category_id: str | None = None
    product_id: str | None = None

    async with app.router.lifespan_context(app):
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                origin = {"origin": "http://test"}
                incomplete_seller = await client.post(
                    "/api/v1/auth/register",
                    json={
                        "full_name": "Seller Incomplete",
                        "email": f"incomplete-{identity}@example.com",
                        "password": f"Seller-{identity}-password",
                        "role": "seller",
                    },
                    headers=origin,
                )
                assert incomplete_seller.status_code == 422

                invalid_phone = await client.post(
                    "/api/v1/auth/register",
                    json={
                        "full_name": "Seller Invalid Phone",
                        "email": f"invalid-phone-{identity}@example.com",
                        "password": f"Seller-{identity}-password",
                        "role": "seller",
                        "store_name": "Loja teste",
                        "store_description": "Descrição da loja de teste.",
                        "business_phone": "not-a-phone",
                    },
                    headers=origin,
                )
                assert invalid_phone.status_code == 422

                seller_email = f"seller-{identity}@example.com"
                seller_password = f"Seller-{identity}-password"
                seller_response = await client.post(
                    "/api/v1/auth/register",
                    json={
                        "full_name": "Seller Profile Test",
                        "email": seller_email,
                        "password": seller_password,
                        "role": "seller",
                        "store_name": f"Linx Store {identity[:8]}",
                        "store_description": "Uma loja criada para validar o perfil.",
                        "business_phone": "+55 (11) 99999-1234",
                    },
                    headers=origin,
                )
                assert seller_response.status_code == 201
                seller_user = UserRead.model_validate(seller_response.json())
                assert seller_user.role is UserRole.SELLER
                assert seller_user.store_name == f"Linx Store {identity[:8]}"
                assert seller_user.business_phone == "+55 (11) 99999-1234"
                seller = IntegrationAccount(
                    seller_user,
                    seller_email,
                    seller_password,
                    UserRole.SELLER,
                )
                accounts.append(seller)

                client_account = await create_test_client(client)
                other_client = await create_test_client(client)
                accounts.extend((client_account, other_client))

                duplicate = await client.post(
                    "/api/v1/auth/register",
                    json={
                        "full_name": "Duplicate Seller",
                        "email": seller_email,
                        "password": f"Seller-{identity}-other-password",
                        "role": "seller",
                        "store_name": "Loja duplicada",
                        "store_description": "Não deve ser cadastrada.",
                    },
                    headers=origin,
                )
                assert duplicate.status_code == 409

                await seller.login(client)
                seller_profile = await client.get("/api/v1/auth/me")
                assert seller_profile.status_code == 200
                assert seller_profile.json()["role"] == "seller"
                assert seller_profile.json()["created_at"]
                assert seller_profile.json()["store_description"] == (
                    "Uma loja criada para validar o perfil."
                )

                personal_update = await client.patch(
                    "/api/v1/auth/profile",
                    json={
                        "full_name": "Seller Profile Updated",
                        "email": f"updated-seller-{identity}@example.com",
                    },
                    headers=origin,
                )
                assert personal_update.status_code == 200
                assert personal_update.json()["role"] == "seller"
                assert personal_update.json()["full_name"] == "Seller Profile Updated"
                seller.email = f"updated-seller-{identity}@example.com"

                duplicate_email = await client.patch(
                    "/api/v1/auth/profile",
                    json={"email": client_account.email},
                    headers=origin,
                )
                assert duplicate_email.status_code == 409

                role_escalation = await client.patch(
                    "/api/v1/auth/profile",
                    json={"role": "client"},
                    headers=origin,
                )
                assert role_escalation.status_code == 422
                third_party_profile = await client.patch(
                    f"/api/v1/auth/profile/{client_account.id}",
                    json={"full_name": "Third party"},
                    headers=origin,
                )
                assert third_party_profile.status_code in {404, 405}

                category_response = await client.post(
                    "/api/v1/categories",
                    json={"name": f"Profile {identity}"},
                    headers=origin,
                )
                assert category_response.status_code == 201
                category_id = category_response.json()["id"]
                product_response = await client.post(
                    "/api/v1/products",
                    json={
                        "name": f"Profile product {identity}",
                        "description": "Product ownership must not change.",
                        "category": f"Profile {identity}",
                        "price": "12.50",
                        "stock": 5,
                    },
                    headers=origin,
                )
                assert product_response.status_code == 201
                product_id = product_response.json()["id"]
                assert product_response.json()["seller_id"] == seller.id

                store_update = await client.patch(
                    "/api/v1/auth/seller-profile",
                    json={
                        "store_name": f"Updated Store {identity[:8]}",
                        "store_description": "Descrição comercial atualizada.",
                        "business_phone": None,
                    },
                    headers=origin,
                )
                assert store_update.status_code == 200
                assert store_update.json()["role"] == "seller"
                assert store_update.json()["store_name"] == f"Updated Store {identity[:8]}"
                assert store_update.json()["business_phone"] is None
                listed_products = await client.get("/api/v1/products/mine")
                assert listed_products.status_code == 200
                assert listed_products.json()["total"] == 1
                assert listed_products.json()["items"][0]["id"] == product_id

                wrong_password = await client.post(
                    "/api/v1/auth/password",
                    json={
                        "current_password": "not-the-current-password",
                        "new_password": f"New-{identity}-strong-password",
                    },
                    headers=origin,
                )
                assert wrong_password.status_code == 400
                new_password = f"New-{identity}-strong-password"
                password_change = await client.post(
                    "/api/v1/auth/password",
                    json={
                        "current_password": seller_password,
                        "new_password": new_password,
                    },
                    headers=origin,
                )
                assert password_change.status_code == 204
                seller.password = new_password
                await client.post("/api/v1/auth/logout", headers=origin)

                login_after_change = await client.post(
                    "/api/v1/auth/login",
                    json={"email": seller.email, "password": seller_password},
                    headers=origin,
                )
                assert login_after_change.status_code == 401
                await seller.login(client)
                persisted_profile = await client.get("/api/v1/auth/me")
                assert persisted_profile.status_code == 200
                assert persisted_profile.json()["store_name"] == (
                    f"Updated Store {identity[:8]}"
                )
                assert (await client.get("/api/v1/products/mine")).json()["total"] == 1

                await client_account.login(client)
                assert (
                    await client.patch(
                        "/api/v1/auth/seller-profile",
                        json={"store_name": "Tentativa"},
                        headers=origin,
                    )
                ).status_code == 403
                assert (await client.get("/api/v1/orders")).status_code == 200
                assert (await client.get("/api/v1/carts")).status_code == 200
                other_profile = await client.patch(
                    f"/api/v1/auth/profile/{other_client.id}",
                    json={"full_name": "Third party"},
                    headers=origin,
                )
                assert other_profile.status_code in {404, 405}

                await other_client.login(client)
                assert (await client.get("/api/v1/orders")).json()["total"] == 0
                assert (
                    await client.get("/api/v1/auth/me")
                ).json()["id"] == other_client.id
        finally:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as cleanup_client:
                await accounts[0].login(cleanup_client)
                if product_id is not None:
                    await cleanup_client.delete(
                        f"/api/v1/products/{product_id}",
                        headers={"origin": "http://test"},
                    )
                if category_id is not None:
                    await cleanup_client.delete(
                        f"/api/v1/categories/{category_id}",
                        headers={"origin": "http://test"},
                    )
                for account in accounts:
                    await app.state.redis.delete(
                        f"{settings.redis_key_prefix}:cart:{account.id}"
                    )
                    await account.cleanup(
                        app.state.redis,
                        settings.redis_key_prefix,
                    )
