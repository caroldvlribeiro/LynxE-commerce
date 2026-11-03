from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.categories import router as categories_router
from backend.app.api.routes.carts import router as carts_router
from backend.app.api.routes.orders import router as orders_router
from backend.app.api.routes.products import router as products_router
from backend.app.core.config import Settings
from backend.app.db.redis import lifespan


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()

    @asynccontextmanager
    async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = app_settings
        async with lifespan(app):
            yield

    app = FastAPI(
        title="Linx API",
        description="API REST da loja Linx para catálogo e pedidos, com Redis Cloud como banco principal.",
        version="0.1.0",
        lifespan=app_lifespan,
    )
    app.state.settings = app_settings
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(categories_router, prefix="/api/v1")
    app.include_router(carts_router, prefix="/api/v1")
    app.include_router(orders_router, prefix="/api/v1")
    app.include_router(products_router, prefix="/api/v1")

    @app.exception_handler(RedisError)
    async def redis_error_handler(
        request: Request, exc: RedisError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "Redis is unavailable; the request could not be completed."},
        )

    frontend_directory = Path(__file__).resolve().parents[2] / "frontend"
    app.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")

    return app


app = create_app()
