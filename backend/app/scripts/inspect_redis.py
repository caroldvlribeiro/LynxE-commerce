import argparse
import asyncio
import json

from redis.asyncio import Redis

from backend.app.core.config import Settings
from backend.app.db.redis import create_redis_client

MAX_LIMIT = 1000
REDACTED = "[redacted]"


async def describe_key(redis: Redis, key: str, limit: int) -> dict[str, object]:
    key_type = await redis.type(key)
    result: dict[str, object] = {
        "key": key,
        "type": key_type,
        "ttl_seconds": await redis.ttl(key),
    }

    if key_type == "none":
        return result
    if key_type == "hash":
        result["field_count"] = await redis.hlen(key)
        fields: dict[str, str] = {}
        truncated = False
        async for field, value in redis.hscan_iter(key, count=min(limit, 100)):
            if len(fields) >= limit:
                truncated = True
                break
            fields[field] = REDACTED if field == "password_hash" else value
        result["fields"] = fields
        result["truncated"] = truncated
    elif key_type == "set":
        result["member_count"] = await redis.scard(key)
        members: list[str] = []
        truncated = False
        async for member in redis.sscan_iter(key, count=min(limit, 100)):
            if len(members) >= limit:
                truncated = True
                break
            members.append(member)
        result["members"] = sorted(members)
        result["truncated"] = truncated
    elif key_type == "string":
        result["value"] = (
            REDACTED
            if ":session:" in key
            else await redis.get(key)
        )
    else:
        result["detail"] = "This Redis structure is not used by the Linx application."
    return result


async def inspect(settings: Settings, key: str | None, pattern: str, limit: int) -> None:
    redis = create_redis_client(settings, ssl=False)
    try:
        await redis.ping()
        if key is not None:
            results = [await describe_key(redis, key, limit)]
            output = {"results": results}
        else:
            keys: list[str] = []
            async for scanned_key in redis.scan_iter(match=pattern, count=100):
                keys.append(scanned_key)
                if len(keys) >= limit:
                    break
            pipeline = redis.pipeline(transaction=False)
            for scanned_key in keys:
                pipeline.type(scanned_key)
                pipeline.ttl(scanned_key)
            metadata = await pipeline.execute()
            results = [
                {
                    "key": scanned_key,
                    "type": metadata[index * 2],
                    "ttl_seconds": metadata[index * 2 + 1],
                }
                for index, scanned_key in enumerate(keys)
            ]
            output = {
                "results": results,
                "limit": limit,
                "possibly_truncated": len(keys) >= limit,
            }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    finally:
        await redis.aclose()


def main() -> None:
    settings = Settings()
    namespace = f"{settings.redis_key_prefix}:"
    parser = argparse.ArgumentParser(
        description="Inspect Linx Redis keys without changing stored data."
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--key",
        help="Inspect one exact key inside the configured Linx namespace.",
    )
    selection.add_argument(
        "--pattern",
        help=f"SCAN pattern restricted to {namespace}* (default: {namespace}*).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help=f"Maximum keys or fields/members to print (1-{MAX_LIMIT}; default: 100).",
    )
    args = parser.parse_args()

    if not 1 <= args.limit <= MAX_LIMIT:
        parser.error(f"--limit must be between 1 and {MAX_LIMIT}.")
    if args.key is not None and not args.key.startswith(namespace):
        parser.error(f"--key must start with the configured namespace {namespace!r}.")
    pattern = args.pattern or f"{namespace}*"
    if args.pattern is not None and not args.pattern.startswith(namespace):
        parser.error(
            f"--pattern must start with the configured namespace {namespace!r}."
        )

    asyncio.run(inspect(settings, args.key, pattern, args.limit))


if __name__ == "__main__":
    main()
