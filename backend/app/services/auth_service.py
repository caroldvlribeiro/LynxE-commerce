from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import HTTPException, status

from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.user import (
    UserCredentials,
    UserRead,
    UserProfileUpdate,
    UserRegistration,
    SellerProfileUpdate,
    UserRole,
    UserStatus,
)

password_hasher = PasswordHasher()


class AuthService:
    def __init__(
        self,
        repository: UserRepository,
        session_ttl_seconds: int,
    ) -> None:
        self.repository = repository
        self.session_ttl_seconds = session_ttl_seconds

    async def register_account(self, data: UserRegistration) -> UserRead:
        user = await self.repository.create(
            full_name=data.full_name,
            email=str(data.email),
            password_hash=password_hasher.hash(data.password),
            role=data.role,
            store_name=data.store_name,
            store_description=data.store_description,
            business_phone=data.business_phone,
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )
        return user

    async def provision_seller(
        self,
        *,
        full_name: str,
        email: str,
        password: str,
        store_name: str | None = None,
        store_description: str | None = None,
        business_phone: str | None = None,
    ) -> UserRead:
        user = await self.repository.create(
            full_name=full_name,
            email=email,
            password_hash=password_hasher.hash(password),
            role=UserRole.SELLER,
            store_name=store_name,
            store_description=store_description,
            business_phone=business_phone,
        )
        if user is None:
            raise ValueError("An account with this email already exists.")
        return user

    async def update_profile(
        self,
        user: UserCredentials,
        data: UserProfileUpdate,
    ) -> UserRead:
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        updated = await self.repository.update_profile(
            user_id=str(user.id),
            full_name=changes.get("full_name", user.full_name),
            email=str(changes.get("email", user.email)),
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )
        refreshed = await self.repository.get(str(user.id))
        if refreshed is None:
            raise RuntimeError("The authenticated account could not be reloaded.")
        return self._public_user(refreshed)

    async def update_seller_profile(
        self,
        user: UserCredentials,
        data: SellerProfileUpdate,
    ) -> UserRead:
        changes = data.model_dump(exclude_unset=True)
        await self.repository.update_seller_profile(
            user_id=str(user.id),
            changes=changes,
        )
        refreshed = await self.repository.get(str(user.id))
        if refreshed is None:
            raise RuntimeError("The authenticated account could not be reloaded.")
        return self._public_user(refreshed)

    async def change_password(
        self,
        user: UserCredentials,
        current_password: str,
        new_password: str,
    ) -> None:
        if not self._verify_password(current_password, user):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The current password is incorrect.",
            )
        if self._verify_password(new_password, user):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Choose a password different from the current password.",
            )
        await self.repository.update_password(
            str(user.id),
            password_hasher.hash(new_password),
        )

    async def login(self, email: str, password: str) -> tuple[UserRead, str]:
        user = await self.repository.get_by_email(email)
        if user is None or not self._verify_password(password, user):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email or password is incorrect.",
                headers={"WWW-Authenticate": "Cookie"},
            )
        if user.status is not UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is disabled.",
            )

        if password_hasher.check_needs_rehash(user.password_hash):
            await self.repository.redis.hset(
                self.repository.user_key(str(user.id)),
                "password_hash",
                password_hasher.hash(password),
            )
        token = await self.repository.create_session(
            str(user.id),
            self.session_ttl_seconds,
        )
        return self._public_user(user), token

    async def logout(self, token: str | None) -> None:
        if token:
            await self.repository.delete_session(token)

    @staticmethod
    def _verify_password(password: str, user: UserCredentials) -> bool:
        try:
            return password_hasher.verify(user.password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    @staticmethod
    def _public_user(user: UserCredentials) -> UserRead:
        return UserRead(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role,
            status=user.status,
            created_at=user.created_at,
            store_name=user.store_name,
            store_description=user.store_description,
            business_phone=user.business_phone,
        )
