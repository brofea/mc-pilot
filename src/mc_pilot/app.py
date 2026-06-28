"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from mc_pilot import __version__
from mc_pilot.api.health import router as health_router
from mc_pilot.api.models import ErrorBody, ErrorResponse
from mc_pilot.api.pages import create_page_router
from mc_pilot.config import Settings, get_settings
from mc_pilot.errors import AppError
from mc_pilot.logging_config import configure_logging
from mc_pilot.storage.qdrant import QdrantProbe
from mc_pilot.storage.sqlite import create_sqlite_engine, initialize_database

logger = logging.getLogger(__name__)
PACKAGE_DIR = Path(__file__).resolve().parent


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an application with explicit, replaceable dependencies."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    sqlite_engine = create_sqlite_engine(resolved_settings.sqlite_url)
    qdrant_probe = QdrantProbe(
        url=resolved_settings.qdrant_url,
        timeout_seconds=resolved_settings.qdrant_timeout_seconds,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        initialize_database(sqlite_engine)
        logger.info("application_started", extra={"version": __version__})
        yield
        qdrant_probe.close()
        sqlite_engine.dispose()
        logger.info("application_stopped")

    app = FastAPI(
        title="Minecraft Pilot API",
        version=__version__,
        description="Local backend for the Minecraft Pilot web client and future Fabric mod.",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.sqlite_engine = sqlite_engine
    app.state.qdrant_probe = qdrant_probe

    templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")
    app.include_router(health_router)
    app.include_router(create_page_router(templates))

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, error: AppError) -> JSONResponse:
        request_id = request.headers.get("x-request-id", str(uuid4()))
        logger.warning(
            "request_failed",
            extra={"request_id": request_id, "error_code": error.code},
        )
        body = ErrorResponse(
            error=ErrorBody(
                code=error.code,
                message=error.message,
                request_id=request_id,
                details=error.details,
            )
        )
        return JSONResponse(status_code=error.status_code, content=body.model_dump(mode="json"))

    return app
