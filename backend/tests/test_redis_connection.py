import asyncio
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from backend.app.core.config import Settings
from backend.app.db.redis import create_redis_client


def test_redis_cloud_connection_and_persistence() -> None:
    settings = Settings()
    if settings.redis_url is None and settings.redis_host is None:
        pytest.skip("Configure Redis Cloud in .env to test the connection.")
    asyncio.run(_check_connection_and_persistence(settings))


async def _check_connection_and_persistence(settings: Settings) -> None:
    key = f"{settings.redis_key_prefix}:test:connection:{uuid4()}"
    value = str(uuid4())
    writer = create_redis_client(settings, ssl=False)
    reader: Redis | None = None

    try:
        assert await writer.ping() is True
        assert await writer.set(key, value, ex=60, nx=True) is True
        await writer.aclose()

        reader = create_redis_client(settings, ssl=False)
        assert await reader.get(key) == value
        assert await reader.delete(key) == 1
        assert await reader.get(key) is None
    finally:
        try:
            await (reader or writer).delete(key)
        finally:
            if reader is not None:
                try:
                    await reader.aclose()
                finally:
                    await writer.aclose()
            else:
                await writer.aclose()
