import base64
from datetime import datetime, timezone
from uuid import uuid4

from redis.asyncio import Redis

from backend.app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate

CREATE_CATEGORY_SCRIPT = """
if redis.call('HEXISTS', KEYS[3], ARGV[2]) == 1 then
    return 0
end
redis.call(
    'HSET', KEYS[1],
    'id', ARGV[1],
    'name', ARGV[3],
    'description', ARGV[4],
    'name_token', ARGV[2],
    'created_at', ARGV[5],
    'seller_id', ARGV[6]
)
redis.call('SADD', KEYS[2], ARGV[1])
redis.call('HSET', KEYS[3], ARGV[2], ARGV[1])
return 1
"""

UPDATE_CATEGORY_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 0 then
    return -1
end
if redis.call('HGET', KEYS[1], 'seller_id') ~= ARGV[6] then
    return -2
end
local existing_name = redis.call('HGET', KEYS[1], 'name')
if existing_name ~= ARGV[5] then
    local product_ids = redis.call('SMEMBERS', KEYS[3])
    if ARGV[3] ~= ARGV[2] then
        local existing_id = redis.call('HGET', KEYS[2], ARGV[3])
        if existing_id and existing_id ~= ARGV[1] then
            return 0
        end
    end
    for _, product_id in ipairs(product_ids) do
        local product_key = ARGV[4] .. ':product:' .. product_id
        if redis.call('HGET', product_key, 'seller_id') ~= ARGV[6] then
            return -3
        end
    end
    for _, product_id in ipairs(product_ids) do
        local product_key = ARGV[4] .. ':product:' .. product_id
        redis.call(
            'HSET', product_key,
            'category', ARGV[5],
            'category_index_key', KEYS[4]
        )
        redis.call('SADD', KEYS[4], product_id)
    end
    if ARGV[3] ~= ARGV[2] then
        redis.call('DEL', KEYS[3])
        redis.call('HDEL', KEYS[2], ARGV[2])
        redis.call('HSET', KEYS[2], ARGV[3], ARGV[1])
    end
end
redis.call(
    'HSET', KEYS[1],
    'name', ARGV[5],
    'description', ARGV[7],
    'name_token', ARGV[3]
)
return 1
"""

DELETE_CATEGORY_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 0 then
    return -1
end
if redis.call('HGET', KEYS[1], 'seller_id') ~= ARGV[2] then
    return -2
end
if redis.call('SCARD', KEYS[3]) > 0 then
    return 0
end
local name_token = redis.call('HGET', KEYS[1], 'name_token')
redis.call('HDEL', KEYS[2], name_token)
redis.call('SREM', KEYS[4], ARGV[1])
redis.call('DEL', KEYS[1])
return 1
"""


class CategoryRepository:
    def __init__(self, redis: Redis, key_prefix: str) -> None:
        self.redis = redis
        self.key_prefix = key_prefix

    @property
    def categories_key(self) -> str:
        return f"{self.key_prefix}:categories"

    @property
    def names_key(self) -> str:
        return f"{self.key_prefix}:categories:by_name"

    def category_key(self, category_id: str) -> str:
        return f"{self.key_prefix}:category_record:{category_id}"

    def product_index_key(self, name: str) -> str:
        return f"{self.key_prefix}:category:{self.name_token(name)}:products"

    @staticmethod
    def name_token(name: str) -> str:
        normalized = " ".join(name.casefold().split())
        encoded = base64.urlsafe_b64encode(normalized.encode("utf-8"))
        return encoded.decode("ascii").rstrip("=")

    async def create(
        self,
        data: CategoryCreate,
        seller_id: str,
    ) -> CategoryRead | None:
        category_id = str(uuid4())
        created_at = datetime.now(timezone.utc)
        token = self.name_token(data.name)
        created = await self.redis.eval(
            CREATE_CATEGORY_SCRIPT,
            3,
            self.category_key(category_id),
            self.categories_key,
            self.names_key,
            category_id,
            token,
            data.name,
            data.description,
            created_at.isoformat(),
            seller_id,
        )
        if not created:
            return None
        return CategoryRead(
            id=category_id,
            created_at=created_at,
            seller_id=seller_id,
            **data.model_dump(),
        )

    async def get(self, category_id: str) -> CategoryRead | None:
        record = await self.redis.hgetall(self.category_key(category_id))
        return self._to_category(record) if record else None

    async def get_by_name(self, name: str) -> CategoryRead | None:
        category_id = await self.redis.hget(
            self.names_key,
            self.name_token(name),
        )
        return await self.get(category_id) if category_id else None

    async def list(self) -> list[CategoryRead]:
        category_ids = sorted(await self.redis.smembers(self.categories_key))
        if not category_ids:
            return []
        pipeline = self.redis.pipeline(transaction=False)
        for category_id in category_ids:
            pipeline.hgetall(self.category_key(category_id))
        records = await pipeline.execute()
        return [self._to_category(record) for record in records if record]

    async def update(
        self,
        category_id: str,
        data: CategoryUpdate,
        seller_id: str,
    ) -> str | None:
        existing = await self.get(category_id)
        if existing is None:
            return None

        old_token = self.name_token(existing.name)
        new_token = self.name_token(data.name)
        result = await self.redis.eval(
            UPDATE_CATEGORY_SCRIPT,
            4,
            self.category_key(category_id),
            self.names_key,
            self.product_index_key(existing.name),
            self.product_index_key(data.name),
            category_id,
            old_token,
            new_token,
            self.key_prefix,
            data.name,
            seller_id,
            data.description,
        )
        if result == -1:
            return None
        if result == -2:
            return "forbidden"
        if result == 0:
            return "duplicate"
        if result == -3:
            return "foreign_products"
        return "updated"

    async def delete(self, category_id: str, seller_id: str) -> str:
        category = await self.get(category_id)
        if category is None:
            return "missing"

        result = await self.redis.eval(
            DELETE_CATEGORY_SCRIPT,
            4,
            self.category_key(category_id),
            self.names_key,
            self.product_index_key(category.name),
            self.categories_key,
            category_id,
            seller_id,
        )
        if result == -1:
            return "missing"
        if result == -2:
            return "forbidden"
        if result == 0:
            return "in_use"
        return "deleted"

    @staticmethod
    def _to_category(record: dict[str, str]) -> CategoryRead:
        return CategoryRead(
            id=record["id"],
            name=record["name"],
            description=record["description"],
            created_at=datetime.fromisoformat(record["created_at"]),
            seller_id=record.get("seller_id"),
        )
