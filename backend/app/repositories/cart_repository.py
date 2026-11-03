from decimal import Decimal

from redis.asyncio import Redis

from backend.app.repositories.product_repository import ProductRepository
from backend.app.schemas.cart import CartItemRead, CartRead

CART_CHANGE_SCRIPT = """
if redis.call('EXISTS', KEYS[2]) == 0 then
    return 0
end
if redis.call('HGET', KEYS[2], 'status') ~= 'active' then
    return -1
end
local available = tonumber(redis.call('HGET', KEYS[2], 'stock') or '-1')
local requested = tonumber(ARGV[2])
local current = tonumber(redis.call('HGET', KEYS[1], ARGV[1]) or '0')
local target = requested
if ARGV[3] == 'add' then
    target = current + requested
end
if available < 0 or target > available then
    return -2
end
redis.call('HSET', KEYS[1], ARGV[1], target)
redis.call('EXPIRE', KEYS[1], ARGV[4])
return 1
"""

CART_REMOVE_SCRIPT = """
local removed = redis.call('HDEL', KEYS[1], ARGV[1])
if redis.call('HLEN', KEYS[1]) == 0 then
    redis.call('DEL', KEYS[1])
end
return removed
"""

CART_TTL_SECONDS = 7 * 24 * 60 * 60


class CartRepository:
    def __init__(
        self,
        redis: Redis,
        key_prefix: str,
        product_repository: ProductRepository,
    ) -> None:
        self.redis = redis
        self.key_prefix = key_prefix
        self.product_repository = product_repository

    def cart_key(self, client_id: str) -> str:
        return f"{self.key_prefix}:cart:{client_id}"

    async def change_item(
        self,
        client_id: str,
        product_id: str,
        quantity: int,
        *,
        add: bool,
    ) -> int:
        return int(
            await self.redis.eval(
                CART_CHANGE_SCRIPT,
                2,
                self.cart_key(client_id),
                self.product_repository.product_key(product_id),
                product_id,
                quantity,
                "add" if add else "set",
                CART_TTL_SECONDS,
            )
        )

    async def get(self, client_id: str) -> CartRead:
        cart_items = await self.redis.hgetall(self.cart_key(client_id))
        if not cart_items:
            return CartRead(
                client_id=client_id,
                items=[],
                total_items=0,
                total=0,
            )

        product_ids = list(cart_items)
        pipeline = self.redis.pipeline(transaction=False)
        for product_id in product_ids:
            pipeline.hgetall(self.product_repository.product_key(product_id))
        records = await pipeline.execute()

        items: list[CartItemRead] = []
        total = 0
        total_items = 0
        has_unavailable_items = False
        for product_id, record in zip(product_ids, records):
            quantity = int(cart_items[product_id])
            total_items += quantity
            if not record:
                has_unavailable_items = True
                items.append(
                    CartItemRead(
                        product_id=product_id,
                        name="Produto indisponível",
                        category="",
                        quantity=quantity,
                        unit_price=Decimal("0.00"),
                        subtotal=Decimal("0.00"),
                        image_url=None,
                        available=False,
                    )
                )
                continue
            unit_price = int(record["price_cents"])
            available = (
                record.get("status") == "active"
                and int(record.get("stock", "0")) >= quantity
            )
            subtotal = unit_price * quantity if available else 0
            if not available:
                has_unavailable_items = True
            else:
                total += subtotal
            items.append(
                CartItemRead(
                    product_id=product_id,
                    name=record["name"],
                    category=record["category"],
                    quantity=quantity,
                    unit_price=(Decimal(unit_price) / Decimal(100)).quantize(
                        Decimal("0.01")
                    ),
                    subtotal=(Decimal(subtotal) / Decimal(100)).quantize(
                        Decimal("0.01")
                    ),
                    image_url=record.get("image_url") or None,
                    available=available,
                )
            )
        return CartRead(
            client_id=client_id,
            items=items,
            total_items=total_items,
            total=(Decimal(total) / Decimal(100)).quantize(Decimal("0.01")),
            has_unavailable_items=has_unavailable_items
            or any(not item.available for item in items),
        )

    async def remove_item(self, client_id: str, product_id: str) -> bool:
        return bool(
            await self.redis.eval(
                CART_REMOVE_SCRIPT,
                1,
                self.cart_key(client_id),
                product_id,
            )
        )
