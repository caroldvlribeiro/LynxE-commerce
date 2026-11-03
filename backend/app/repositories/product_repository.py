from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from redis.asyncio import Redis

from backend.app.repositories.category_repository import CategoryRepository
from backend.app.schemas.product import (
    ProductCreate,
    ProductRead,
    ProductStatus,
    ProductUpdate,
)

CREATE_PRODUCT_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 1 then
    return 0
end
if redis.call('HEXISTS', KEYS[4], ARGV[10]) == 0 then
    return -1
end
redis.call(
    'HSET', KEYS[1],
    'id', ARGV[1],
    'name', ARGV[2],
    'description', ARGV[3],
    'category', ARGV[4],
    'category_index_key', KEYS[3],
    'price_cents', ARGV[5],
    'stock', ARGV[6],
    'image_url', ARGV[7],
    'status', ARGV[8],
    'created_at', ARGV[9],
    'seller_id', ARGV[11]
)
redis.call('SADD', KEYS[2], ARGV[1])
redis.call('SADD', KEYS[3], ARGV[1])
redis.call('SADD', KEYS[5], ARGV[1])
return 1
"""

UPDATE_PRODUCT_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 0 then
    return 0
end
if redis.call('HGET', KEYS[1], 'seller_id') ~= ARGV[10] then
    return -2
end
if redis.call('HEXISTS', KEYS[4], ARGV[9]) == 0 then
    return -1
end
local old_category_index = redis.call('HGET', KEYS[1], 'category_index_key')
if old_category_index ~= KEYS[3] then
    if old_category_index then
        redis.call('SREM', old_category_index, ARGV[1])
    end
    redis.call('SADD', KEYS[3], ARGV[1])
end
redis.call(
    'HSET', KEYS[1],
    'name', ARGV[2],
    'description', ARGV[3],
    'category', ARGV[4],
    'category_index_key', KEYS[3],
    'price_cents', ARGV[5],
    'stock', ARGV[6],
    'image_url', ARGV[7],
    'status', ARGV[8],
    'seller_id', ARGV[10]
)
return 1
"""

DELETE_PRODUCT_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 0 then
    return 0
end
if redis.call('HGET', KEYS[1], 'seller_id') ~= ARGV[2] then
    return -2
end
if redis.call('SCARD', KEYS[3]) > 0 then
    return -1
end
local category_index = redis.call('HGET', KEYS[1], 'category_index_key')
if category_index then
    redis.call('SREM', category_index, ARGV[1])
end
redis.call('SREM', KEYS[2], ARGV[1])
redis.call('SREM', KEYS[4], ARGV[1])
redis.call('DEL', KEYS[1])
return 1
"""


class ProductRepository:
    def __init__(self, redis: Redis, key_prefix: str) -> None:
        self.redis = redis
        self.key_prefix = key_prefix

    @property
    def products_key(self) -> str:
        return f"{self.key_prefix}:products"

    def product_key(self, product_id: str) -> str:
        return f"{self.key_prefix}:product:{product_id}"

    def category_key(self, category: str) -> str:
        token = CategoryRepository.name_token(category)
        return f"{self.key_prefix}:category:{token}:products"

    @property
    def category_names_key(self) -> str:
        return f"{self.key_prefix}:categories:by_name"

    def seller_products_key(self, seller_id: str) -> str:
        return f"{self.key_prefix}:seller:{seller_id}:products"

    async def create(
        self,
        data: ProductCreate,
        seller_id: str,
    ) -> ProductRead | None:
        product_id = str(uuid4())
        created_at = datetime.now(timezone.utc)
        category_index = self.category_key(data.category)
        created = await self.redis.eval(
            CREATE_PRODUCT_SCRIPT,
            5,
            self.product_key(product_id),
            self.products_key,
            category_index,
            self.category_names_key,
            self.seller_products_key(seller_id),
            product_id,
            data.name,
            data.description,
            data.category,
            self._price_to_cents(data.price),
            data.stock,
            data.image_url or "",
            data.status.value,
            created_at.isoformat(),
            CategoryRepository.name_token(data.category),
            seller_id,
        )
        if created == -1:
            return None
        if not created:
            return None
        return ProductRead(
            id=product_id,
            created_at=created_at,
            seller_id=seller_id,
            **data.model_dump(),
        )

    async def get(self, product_id: str) -> ProductRead | None:
        record = await self.redis.hgetall(self.product_key(product_id))
        return self._to_product(record) if record else None

    async def list(
        self,
        *,
        search: str | None,
        category: str | None,
        seller_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[ProductRead], int]:
        if category:
            product_ids = await self.redis.smembers(self.category_key(category))
        else:
            index_key = (
                self.seller_products_key(seller_id)
                if seller_id is not None
                else self.products_key
            )
            product_ids = await self.redis.smembers(index_key)

        ordered_ids = sorted(product_ids)
        records = await self._get_many(ordered_ids)
        normalized_search = search.casefold().strip() if search else None
        products = [
            product
            for product in records
            if product is not None
            and (
                str(product.seller_id) == seller_id
                if seller_id is not None
                else product.status is ProductStatus.ACTIVE
            )
            and (
                normalized_search is None
                or normalized_search in product.name.casefold()
            )
        ]
        return products[offset : offset + limit], len(products)

    async def update(
        self,
        product_id: str,
        data: ProductUpdate,
        seller_id: str,
    ) -> ProductRead | None:
        existing = await self.get(product_id)
        if existing is None:
            return None

        category_index = self.category_key(data.category)
        updated = await self.redis.eval(
            UPDATE_PRODUCT_SCRIPT,
            4,
            self.product_key(product_id),
            self.products_key,
            category_index,
            self.category_names_key,
            product_id,
            data.name,
            data.description,
            data.category,
            self._price_to_cents(data.price),
            data.stock,
            data.image_url or "",
            data.status.value,
            CategoryRepository.name_token(data.category),
            seller_id,
        )
        if updated == -2:
            return None
        if updated == -1:
            return None
        if not updated:
            return None
        return ProductRead(
            id=product_id,
            created_at=existing.created_at,
            seller_id=seller_id,
            **data.model_dump(),
        )

    async def delete(self, product_id: str, seller_id: str) -> int:
        return int(
            await self.redis.eval(
                DELETE_PRODUCT_SCRIPT,
                4,
                self.product_key(product_id),
                self.products_key,
                f"{self.product_key(product_id)}:active_orders",
                self.seller_products_key(seller_id),
                product_id,
                seller_id,
            )
        )

    async def _get_many(self, product_ids: list[str]) -> list[ProductRead | None]:
        if not product_ids:
            return []
        pipeline = self.redis.pipeline(transaction=False)
        for product_id in product_ids:
            pipeline.hgetall(self.product_key(product_id))
        records = await pipeline.execute()
        return [self._to_product(record) if record else None for record in records]

    @staticmethod
    def _price_to_cents(price: Decimal) -> int:
        return int(price * 100)

    @staticmethod
    def _to_product(record: dict[str, str]) -> ProductRead:
        image_url = record.get("image_url") or None
        return ProductRead(
            id=record["id"],
            name=record["name"],
            description=record["description"],
            category=record["category"],
            price=(Decimal(record["price_cents"]) / Decimal(100)).quantize(
                Decimal("0.01")
            ),
            stock=int(record["stock"]),
            image_url=image_url,
            status=ProductStatus(record["status"]),
            created_at=datetime.fromisoformat(record["created_at"]),
            seller_id=record.get("seller_id"),
        )
