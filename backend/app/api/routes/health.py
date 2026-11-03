from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from backend.app.db.redis import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(redis: Annotated[Redis, Depends(get_redis)]) -> dict[str, str]:
    await redis.ping()
    return {"status": "ok", "redis": "connected"}
