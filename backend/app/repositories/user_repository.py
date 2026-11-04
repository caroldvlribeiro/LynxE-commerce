import hashlib
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from redis.asyncio import Redis

from backend.app.schemas.user import (
    SellerOption,
    UserCredentials,
    UserRead,
    UserRole,
    UserStatus,
)

CREATE_USER_SCRIPT = """
if redis.call('HEXISTS', KEYS[2], ARGV[3]) == 1 then
    return 0
end
redis.call(
    'HSET', KEYS[1],
    'id', ARGV[1],
    'full_name', ARGV[2],
    'email', ARGV[3],
    'password_hash', ARGV[4],
    'role', ARGV[5],
    'status', 'active',
    'created_at', ARGV[6],
    'store_name', ARGV[7],
    'store_description', ARGV[8],
    'business_phone', ARGV[9]
)
redis.call('HSET', KEYS[2], ARGV[3], ARGV[1])
redis.call('SADD', KEYS[3], ARGV[1])
redis.call('SADD', KEYS[4], ARGV[1])
return 1
"""

UPDATE_PROFILE_SCRIPT = """
local old_email = redis.call('HGET', KEYS[1], 'email')
if old_email ~= ARGV[2] and redis.call('HEXISTS', KEYS[2], ARGV[2]) == 1 then
    return 0
end
if old_email ~= ARGV[2] then
    redis.call('HDEL', KEYS[2], old_email)
end
redis.call(
    'HSET', KEYS[1],
    'full_name', ARGV[1],
    'email', ARGV[2]
)
redis.call('HSET', KEYS[2], ARGV[2], ARGV[3])
return 1
"""

CREATE_SESSION_SCRIPT = """
if redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2], 'NX') then
    return 1
end
return 0
"""


class UserRepository:
    def __init__(self, redis: Redis, key_prefix: str) -> None:
        self.redis = redis
        self.key_prefix = key_prefix

    @property
    def users_key(self) -> str:
        return f"{self.key_prefix}:users"

    @property
    def email_index_key(self) -> str:
        return f"{self.key_prefix}:users:by_email"

    def user_key(self, user_id: str) -> str:
        return f"{self.key_prefix}:user:{user_id}"

    def role_index_key(self, role: UserRole) -> str:
        return f"{self.key_prefix}:users:role:{role.value}"

    def session_key(self, token: str) -> str:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return f"{self.key_prefix}:session:{digest}"

    async def create(
        self,
        *,
        full_name: str,
        email: str,
        password_hash: str,
        role: UserRole,
        store_name: str | None = None,
        store_description: str | None = None,
        business_phone: str | None = None,
    ) -> UserRead | None:
        normalized_email = self.normalize_email(email)
        user_id = str(uuid4())
        created_at = datetime.now(timezone.utc)
        created = await self.redis.eval(
            CREATE_USER_SCRIPT,
            4,
            self.user_key(user_id),
            self.email_index_key,
            self.users_key,
            self.role_index_key(role),
            user_id,
            full_name.strip(),
            normalized_email,
            password_hash,
            role.value,
            created_at.isoformat(),
            store_name or "",
            store_description or "",
            business_phone or "",
        )
        if not created:
            return None
        return UserRead(
            id=user_id,
            full_name=full_name.strip(),
            email=normalized_email,
            role=role,
            status=UserStatus.ACTIVE,
            created_at=created_at,
            store_name=store_name,
            store_description=store_description,
            business_phone=business_phone,
        )

    async def update_profile(
        self,
        *,
        user_id: str,
        full_name: str,
        email: str,
    ) -> bool:
        normalized_email = self.normalize_email(email)
        updated = await self.redis.eval(
            UPDATE_PROFILE_SCRIPT,
            2,
            self.user_key(user_id),
            self.email_index_key,
            full_name.strip(),
            normalized_email,
            user_id,
        )
        return bool(updated)

    async def update_seller_profile(
        self,
        *,
        user_id: str,
        changes: dict[str, str | None],
    ) -> None:
        if not changes:
            return
        fields = {
            key: value or ""
            for key, value in changes.items()
        }
        await self.redis.hset(self.user_key(user_id), mapping=fields)

    async def update_password(self, user_id: str, password_hash: str) -> None:
        await self.redis.hset(
            self.user_key(user_id),
            "password_hash",
            password_hash,
        )

    async def get(self, user_id: str) -> UserCredentials | None:
        record = await self.redis.hgetall(self.user_key(user_id))
        return self._to_user(record) if record else None

    async def get_by_email(self, email: str) -> UserCredentials | None:
        normalized_email = self.normalize_email(email)
        user_id = await self.redis.hget(self.email_index_key, normalized_email)
        return await self.get(user_id) if user_id else None

    async def list_sellers(self) -> list[SellerOption]:
        user_ids = sorted(
            await self.redis.smembers(self.role_index_key(UserRole.SELLER))
        )
        if not user_ids:
            return []

        pipeline = self.redis.pipeline(transaction=False)
        for user_id in user_ids:
            pipeline.hgetall(self.user_key(user_id))
        records = await pipeline.execute()
        sellers = []
        for record in records:
            if not record:
                continue
            user = self._to_user(record)
            if user.status is UserStatus.ACTIVE:
                sellers.append(
                    SellerOption(
                        id=user.id,
                        name=user.store_name or user.full_name,
                    )
                )
        return sorted(sellers, key=lambda seller: seller.name.casefold())

    async def create_session(self, user_id: str, ttl_seconds: int) -> str:
        for _ in range(3):
            token = secrets.token_urlsafe(32)
            created = await self.redis.eval(
                CREATE_SESSION_SCRIPT,
                1,
                self.session_key(token),
                user_id,
                ttl_seconds,
            )
            if created:
                return token
        raise RuntimeError("Could not allocate a unique authentication session.")

    async def get_session_user(self, token: str) -> UserCredentials | None:
        user_id = await self.redis.get(self.session_key(token))
        return await self.get(user_id) if user_id else None

    async def delete_session(self, token: str) -> None:
        await self.redis.delete(self.session_key(token))

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().casefold()

    @staticmethod
    def _to_user(record: dict[str, str]) -> UserCredentials:
        return UserCredentials(
            id=record["id"],
            full_name=record["full_name"],
            email=record["email"],
            password_hash=record["password_hash"],
            role=UserRole(record["role"]),
            status=UserStatus(record["status"]),
            created_at=datetime.fromisoformat(record["created_at"]),
            store_name=record.get("store_name") or None,
            store_description=record.get("store_description") or None,
            business_phone=record.get("business_phone") or None,
        )
