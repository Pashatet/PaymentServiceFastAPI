from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config import Settings
from app.database import create_engine, create_session_factory
from app.domain.errors import (
    InvalidStatusTransition,
    InvalidWebhookSignature,
    PaymentNotFound,
    TariffNotFound,
)
from app.payments.dao import SqlAlchemyTariffRepository
from app.payments.router import router


def create_app(
    settings: Settings | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> FastAPI:
    app_settings = settings or Settings()
    owned_engine: AsyncEngine | None = None
    if session_factory is None:
        owned_engine = create_engine(app_settings.database_url)
        session_factory = create_session_factory(owned_engine)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        async with application.state.session_factory() as session:
            await SqlAlchemyTariffRepository(session).ensure_defaults()
        yield
        if application.state.owned_engine is not None:
            await application.state.owned_engine.dispose()

    app = FastAPI(
        title="Payment Service API",
        description="Asynchronous payment API for an online school.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.session_factory = session_factory
    app.state.owned_engine = owned_engine
    app.include_router(router)

    @app.exception_handler(PaymentNotFound)
    @app.exception_handler(TariffNotFound)
    async def not_found_handler(request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(InvalidStatusTransition)
    async def invalid_transition_handler(
        request: Request, error: InvalidStatusTransition
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"error": "invalid_transition"})

    @app.exception_handler(InvalidWebhookSignature)
    async def invalid_signature_handler(
        request: Request, error: InvalidWebhookSignature
    ) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid webhook signature"},
        )

    return app


app = create_app()
