from dataclasses import dataclass, field
from uuid import uuid4

from httpx import AsyncClient
from redis.asyncio import Redis

from backend.app.core.config import Settings
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.user import UserRole, UserRead
from backend.app.services.auth_service import AuthService


@dataclass
class IntegrationAccount:
    user: UserRead
    email: str
    password: str
    role: UserRole
    session_tokens: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return str(self.user.id)

    async def login(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": self.email, "password": self.password},
            headers={"origin": str(client.base_url).rstrip("/")},
        )
        assert response.status_code == 200
        token = client.cookies.get("viva_session")
        assert token is not None
        self.session_tokens.append(token)

    async def cleanup(self, redis: Redis, key_prefix: str) -> None:
        repository = UserRepository(redis, key_prefix)
        for token in self.session_tokens:
            await redis.delete(repository.session_key(token))
        await redis.delete(repository.user_key(self.id))
        await redis.hdel(repository.email_index_key, self.email)
        await redis.srem(repository.users_key, self.id)
        await redis.srem(repository.role_index_key(self.role), self.id)


async def create_test_seller(
    app,
    settings: Settings,
) -> IntegrationAccount:
    identity = uuid4().hex
    email = f"seller-{identity}@example.com"
    password = f"Seller-{identity}-test-password"
    service = AuthService(
        UserRepository(app.state.redis, settings.redis_key_prefix),
        settings.auth_session_ttl_seconds,
    )
    user = await service.provision_seller(
        full_name="Integration Test Seller",
        email=email,
        password=password,
    )
    return IntegrationAccount(user, email, password, UserRole.SELLER)


async def create_test_client(client: AsyncClient) -> IntegrationAccount:
    identity = uuid4().hex
    email = f"client-{identity}@example.com"
    password = f"Client-{identity}-test-password"
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Integration Test Client",
            "email": email,
            "password": password,
        },
        headers={"origin": str(client.base_url).rstrip("/")},
    )
    assert response.status_code == 201
    user = UserRead.model_validate(response.json())
    return IntegrationAccount(user, email, password, UserRole.CLIENT)
