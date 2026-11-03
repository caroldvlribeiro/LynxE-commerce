from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from redis.asyncio import Redis
from redis.asyncio.connection import Connection
from redis.exceptions import RedisError

from backend.app.core.config import Settings


def create_redis_client(settings: Settings, *, ssl: bool = False) -> Redis:
    if ssl:
        raise RuntimeError(
            "The configured Redis Cloud Essentials Free endpoint does not support TLS."
        )
    return Redis.from_url(
        settings.require_redis_url(),
        connection_class=Connection,
        decode_responses=True,
        health_check_interval=30,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    redis = create_redis_client(settings, ssl=False)
    try:
        await redis.ping()
    except RedisError:
        await redis.aclose()
        raise

    app.state.redis = redis
    try:
        yield
    finally:
        await redis.aclose()


def get_redis(request: Request) -> Redis:
    return request.app.state.redis
