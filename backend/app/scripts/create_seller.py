import argparse
import asyncio
from getpass import getpass

from pydantic import ValidationError

from backend.app.core.config import Settings
from backend.app.db.redis import create_redis_client
from backend.app.schemas.user import UserRegistration
from backend.app.services.auth_service import AuthService
from backend.app.repositories.user_repository import UserRepository


async def create_seller(
    *,
    full_name: str,
    email: str,
    password: str,
) -> str:
    settings = Settings()
    redis = create_redis_client(settings, ssl=False)
    try:
        await redis.ping()
        service = AuthService(
            UserRepository(redis, settings.redis_key_prefix),
            settings.auth_session_ttl_seconds,
        )
        seller = await service.provision_seller(
            full_name=full_name,
            email=email,
            password=password,
        )
        return str(seller.id)
    finally:
        await redis.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a seller account using the configured Redis Cloud."
    )
    parser.add_argument("--name", required=True, help="Seller's full name")
    parser.add_argument("--email", required=True, help="Seller's e-mail address")
    args = parser.parse_args()

    password = getpass("Password (minimum 12 characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        parser.error("Passwords do not match.")
    try:
        registration = UserRegistration(
            full_name=args.name,
            email=args.email,
            password=password,
        )
    except ValidationError as exc:
        parser.error(f"Invalid seller account data: {exc}")

    try:
        seller_id = asyncio.run(
            create_seller(
                full_name=registration.full_name,
                email=str(registration.email),
                password=registration.password,
            )
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Seller account created. User ID: {seller_id}")


if __name__ == "__main__":
    main()
