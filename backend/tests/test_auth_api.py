import asyncio
import hashlib
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.tests.test_products_api import redis_settings


def test_client_registration_login_and_logout(redis_settings: Settings) -> None:
    asyncio.run(_exercise_auth(redis_settings))


async def _exercise_auth(settings: Settings) -> None:
    identity = uuid4().hex
    email = f"auth-{identity}@example.com"
    password = f"Secure-{identity}-pass"
    app = create_app(settings)
    openapi = app.openapi()
    cookie_security = openapi["components"]["securitySchemes"]["RedisSessionCookie"]
    assert cookie_security["type"] == "apiKey"
    assert cookie_security["in"] == "cookie"
    assert cookie_security["name"] == "viva_session"
    assert any(
        "RedisSessionCookie" in requirement
        for requirement in openapi["paths"]["/api/v1/products"]["post"]["security"]
    )
    assert "security" not in openapi["paths"]["/api/v1/products"]["get"]
    assert "security" not in openapi["paths"]["/api/v1/products/{product_id}"]["get"]
    assert "security" not in openapi["paths"]["/api/v1/categories"]["get"]

    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            protected = await client.get("/api/v1/auth/me")
            assert protected.status_code == 401

            registered = await client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Test Client",
                    "email": email.upper(),
                    "password": password,
                },
                headers={"origin": "http://test"},
            )
            assert registered.status_code == 201
            user = registered.json()
            assert user["role"] == "client"
            assert user["email"] == email
            assert "password" not in user
            assert "password_hash" not in user

            duplicate = await client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Duplicate Client",
                    "email": email,
                    "password": password,
                },
                headers={"origin": "http://test"},
            )
            assert duplicate.status_code == 409

            unsupported_role = await client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Unsupported role",
                    "email": f"unsupported-{identity}@example.com",
                    "password": password,
                    "role": "admin",
                },
            )
            assert unsupported_role.status_code == 422

            wrong_password = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "wrong-password"},
                headers={"origin": "http://test"},
            )
            assert wrong_password.status_code == 401

            login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
                headers={"origin": "http://test"},
            )
            assert login.status_code == 200
            assert login.json()["id"] == user["id"]
            cookie = login.headers["set-cookie"]
            assert "httponly" in cookie.lower()
            assert "samesite=strict" in cookie.lower()

            current_user = await client.get("/api/v1/auth/me")
            assert current_user.status_code == 200
            assert current_user.json()["id"] == user["id"]

            raw_token = client.cookies.get("viva_session")
            assert raw_token
            session_digest = hashlib.sha256(raw_token.encode()).hexdigest()
            stored_session_key = (
                f"{settings.redis_key_prefix}:session:{session_digest}"
            )
            assert await app.state.redis.get(stored_session_key) == user["id"]
            assert raw_token not in stored_session_key

            cross_origin = await client.post(
                "/api/v1/auth/logout",
                headers={"origin": "https://attacker.example"},
            )
            assert cross_origin.status_code == 403

            logout = await client.post(
                "/api/v1/auth/logout",
                headers={"origin": "http://test"},
            )
            assert logout.status_code == 204
            assert (await client.get("/api/v1/auth/me")).status_code == 401

            user_record = await app.state.redis.hgetall(
                f"{settings.redis_key_prefix}:user:{user['id']}"
            )
            assert user_record["password_hash"] != password
            assert user_record["password_hash"].startswith("$argon2id$")
            await app.state.redis.delete(
                f"{settings.redis_key_prefix}:user:{user['id']}"
            )
            await app.state.redis.hdel(
                f"{settings.redis_key_prefix}:users:by_email",
                email,
            )
            await app.state.redis.srem(
                f"{settings.redis_key_prefix}:users",
                user["id"],
            )
            await app.state.redis.srem(
                f"{settings.redis_key_prefix}:users:role:client",
                user["id"],
            )


def test_registration_rejects_invalid_password(redis_settings: Settings) -> None:
    asyncio.run(_reject_invalid_password(redis_settings))


async def _reject_invalid_password(settings: Settings) -> None:
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Test Client",
                    "email": f"short-{uuid4().hex}@example.com",
                    "password": "short",
                },
            )
            weak_password = await client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Test Client",
                    "email": f"weak-{uuid4().hex}@example.com",
                    "password": "onlylowercase",
                },
            )
            invalid_email = await client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Test Client",
                    "email": "not-an-email",
                    "password": "Strong-Password-123",
                },
            )
    assert response.status_code == 422
    assert weak_password.status_code == 422
    assert invalid_email.status_code == 422
