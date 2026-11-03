import json
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from redis.asyncio import Redis

from backend.app.schemas.order import (
    OrderItemRead,
    OrderRead,
    OrderStatus,
)

CREATE_ORDER_SCRIPT = """
if redis.call('HLEN', KEYS[1]) == 0 then
    return -3
end
if redis.call('HLEN', KEYS[1]) ~= tonumber(ARGV[4]) then
    return -2
end
if redis.call('EXISTS', KEYS[2]) == 1 then
    return -4
end
local items = {}
local total = 0
for i = 1, tonumber(ARGV[4]) do
    local argument_index = 5 + ((i - 1) * 2)
    local product_id = ARGV[argument_index]
    local quantity = tonumber(ARGV[argument_index + 1])
    if tonumber(redis.call('HGET', KEYS[1], product_id) or '0') ~= quantity then
        return -2
    end
    local product_key = KEYS[4 + i]
    if redis.call('EXISTS', product_key) == 0
        or redis.call('HGET', product_key, 'status') ~= 'active' then
        return -1
    end
    local stock = tonumber(redis.call('HGET', product_key, 'stock') or '-1')
    if stock < quantity then
        return -1
    end
    local unit_price = tonumber(redis.call('HGET', product_key, 'price_cents'))
    local subtotal = unit_price * quantity
    total = total + subtotal
    items[i] = {
        product_id = product_id,
        name = redis.call('HGET', product_key, 'name'),
        category = redis.call('HGET', product_key, 'category'),
        quantity = quantity,
        unit_price_cents = unit_price,
        subtotal_cents = subtotal,
        image_url = redis.call('HGET', product_key, 'image_url')
    }
end
for i = 1, tonumber(ARGV[4]) do
    local argument_index = 5 + ((i - 1) * 2)
    local product_id = ARGV[argument_index]
    local quantity = tonumber(ARGV[argument_index + 1])
    local product_key = KEYS[4 + i]
    redis.call('HINCRBY', product_key, 'stock', -quantity)
    redis.call('SADD', product_key .. ':active_orders', ARGV[1])
end
redis.call(
    'HSET', KEYS[2],
    'id', ARGV[1],
    'client_id', ARGV[2],
    'status', 'confirmed',
    'items', cjson.encode(items),
    'total_cents', total,
    'created_at', ARGV[3]
)
redis.call('SADD', KEYS[3], ARGV[1])
redis.call('SADD', KEYS[4], ARGV[1])
redis.call('DEL', KEYS[1])
return total
"""

CANCEL_ORDER_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 0 then
    return -1
end
if redis.call('HGET', KEYS[1], 'status') ~= 'confirmed' then
    return 0
end
local items = cjson.decode(redis.call('HGET', KEYS[1], 'items'))
for i, item in ipairs(items) do
    if redis.call('EXISTS', KEYS[i + 1]) == 0 then
        return -2
    end
end
for i, item in ipairs(items) do
    local product_key = KEYS[i + 1]
    redis.call('HINCRBY', product_key, 'stock', item.quantity)
    redis.call('SREM', product_key .. ':active_orders', ARGV[1])
end
redis.call(
    'HSET', KEYS[1],
    'status', 'cancelled',
    'cancelled_at', ARGV[2]
)
return 1
"""


class OrderRepository:
    def __init__(self, redis: Redis, key_prefix: str) -> None:
        self.redis = redis
        self.key_prefix = key_prefix

    @property
    def orders_key(self) -> str:
        return f"{self.key_prefix}:orders"

    def order_key(self, order_id: str) -> str:
        return f"{self.key_prefix}:order:{order_id}"

    def cart_key(self, client_id: str) -> str:
        return f"{self.key_prefix}:cart:{client_id}"

    def client_orders_key(self, client_id: str) -> str:
        return f"{self.key_prefix}:client:{client_id}:orders"

    def product_key(self, product_id: str) -> str:
        return f"{self.key_prefix}:product:{product_id}"

    async def create_from_cart(self, client_id: UUID) -> tuple[int, str]:
        client_id_text = str(client_id)
        cart_key = self.cart_key(client_id_text)
        cart = await self.redis.hgetall(cart_key)
        product_ids = sorted(cart)
        order_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        keys = [
            cart_key,
            self.order_key(order_id),
            self.orders_key,
            self.client_orders_key(client_id_text),
            *(self.product_key(product_id) for product_id in product_ids),
        ]
        arguments: list[str | int] = [
            order_id,
            client_id_text,
            created_at,
            len(product_ids),
        ]
        for product_id in product_ids:
            arguments.extend((product_id, cart[product_id]))

        result = int(await self.redis.eval(CREATE_ORDER_SCRIPT, len(keys), *keys, *arguments))
        return result, order_id

    async def get(self, order_id: UUID) -> OrderRead | None:
        record = await self.redis.hgetall(self.order_key(str(order_id)))
        return self._to_order(record) if record else None

    async def list_for_client(
        self,
        client_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[OrderRead], int]:
        order_ids = sorted(
            await self.redis.smembers(self.client_orders_key(str(client_id))),
            reverse=True,
        )
        selected_ids = order_ids[offset : offset + limit]
        if not selected_ids:
            return [], len(order_ids)

        pipeline = self.redis.pipeline(transaction=False)
        for order_id in selected_ids:
            pipeline.hgetall(self.order_key(order_id))
        records = await pipeline.execute()
        return (
            [self._to_order(record) for record in records if record],
            len(order_ids),
        )

    async def cancel(self, order: OrderRead) -> int:
        keys = [
            self.order_key(str(order.id)),
            *(self.product_key(str(item.product_id)) for item in order.items),
        ]
        return int(
            await self.redis.eval(
                CANCEL_ORDER_SCRIPT,
                len(keys),
                *keys,
                str(order.id),
                datetime.now(timezone.utc).isoformat(),
            )
        )

    @staticmethod
    def _to_order(record: dict[str, str]) -> OrderRead:
        raw_items = json.loads(record["items"])
        items = [
            OrderItemRead(
                product_id=item["product_id"],
                name=item["name"],
                category=item["category"],
                quantity=int(item["quantity"]),
                unit_price=(
                    Decimal(item["unit_price_cents"]) / Decimal(100)
                ).quantize(Decimal("0.01")),
                subtotal=(
                    Decimal(item["subtotal_cents"]) / Decimal(100)
                ).quantize(Decimal("0.01")),
                image_url=item.get("image_url") or None,
            )
            for item in raw_items
        ]
        cancelled_at = record.get("cancelled_at")
        return OrderRead(
            id=record["id"],
            client_id=record["client_id"],
            status=OrderStatus(record["status"]),
            items=items,
            total=(
                Decimal(record["total_cents"]) / Decimal(100)
            ).quantize(Decimal("0.01")),
            created_at=datetime.fromisoformat(record["created_at"]),
            cancelled_at=(
                datetime.fromisoformat(cancelled_at) if cancelled_at else None
            ),
        )
