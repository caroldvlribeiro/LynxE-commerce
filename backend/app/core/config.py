from urllib.parse import quote, urlsplit

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    redis_url: SecretStr | None = None
    redis_host: str | None = None
    redis_port: int | None = None
    redis_username: str | None = None
    redis_password: SecretStr | None = None
    redis_key_prefix: str = "ecommerce"
    auth_session_ttl_seconds: int = 604800
    auth_cookie_secure: bool = False

    def require_redis_url(self) -> str:
        if self.redis_url is not None:
            url = self.redis_url.get_secret_value().strip()
        elif (
            self.redis_host
            and self.redis_port
            and self.redis_password is not None
        ):
            username = quote(self.redis_username or "default", safe="")
            password = quote(
                self.redis_password.get_secret_value(),
                safe="",
            )
            host = self.redis_host.strip()
            url = f"redis://{username}:{password}@{host}:{self.redis_port}"
        else:
            raise RuntimeError(
                "Configure REDIS_URL or REDIS_HOST, REDIS_PORT, and "
                "REDIS_PASSWORD in .env."
            )

        try:
            parsed_url = urlsplit(url)
            valid_url = (
                parsed_url.scheme == "redis"
                and parsed_url.hostname is not None
                and parsed_url.port is not None
            )
        except ValueError as exc:
            raise RuntimeError("Redis connection URL is invalid.") from exc

        if not valid_url:
            raise RuntimeError(
                "Redis Cloud settings must use redis:// and include a host and port."
            )
        return url
