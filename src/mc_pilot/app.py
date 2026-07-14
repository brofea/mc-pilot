"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from mc_pilot import __version__
from mc_pilot.admin.routes import create_admin_router
from mc_pilot.agent.client import DeepSeekClient
from mc_pilot.agent.service import AgentService
from mc_pilot.api.chat import create_chat_router
from mc_pilot.api.game_state import create_game_router
from mc_pilot.api.health import router as health_router
from mc_pilot.api.models import ErrorBody, ErrorResponse
from mc_pilot.api.pages import create_page_router
from mc_pilot.api.recipes import create_recipe_router
from mc_pilot.config import Settings, get_settings
from mc_pilot.errors import AppError
from mc_pilot.game.service import GameStateService
from mc_pilot.logging_config import configure_logging
from mc_pilot.rag.service import WikiService
from mc_pilot.recipes.service import RecipeService
from mc_pilot.storage.qdrant import QdrantProbe
from mc_pilot.storage.sqlite import ConversationStore, create_sqlite_engine, initialize_database

logger = logging.getLogger(__name__)
PACKAGE_DIR = Path(__file__).resolve().parent


def _build_services(settings: Settings, sqlite_engine: Any) -> dict[str, Any]:
    services: dict[str, Any] = {}

    services["recipe"] = RecipeService(engine=sqlite_engine)

    services["wiki"] = WikiService(
        qdrant_url=settings.qdrant_url,
        cache_dir=Path("data/wiki/cache"),
    )

    api_key = (
        settings.deepseek_api_key.get_secret_value()
        if settings.deepseek_api_key
        else ""
    )
    services["agent"] = AgentService(
        deepseek_base_url=settings.deepseek_base_url,
        deepseek_api_key=api_key,
        deepseek_model=settings.deepseek_model,
        recipe_service=services["recipe"],
        wiki_service=services["wiki"],
    )

    death_client = (
        DeepSeekClient(
            base_url=settings.deepseek_base_url,
            api_key=api_key,
            model=settings.deepseek_model,
            max_tokens=400,
        )
        if api_key
        else None
    )
    services["game"] = GameStateService(
        deepseek_client=death_client,
        configured_log_path=settings.game_log_path,
    )

    return services


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an application with explicit, replaceable dependencies."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    sqlite_engine = create_sqlite_engine(resolved_settings.sqlite_url)
    conversation_store = ConversationStore(sqlite_engine)
    qdrant_probe = QdrantProbe(
        url=resolved_settings.qdrant_url,
        timeout_seconds=resolved_settings.qdrant_timeout_seconds,
    )

    services = _build_services(resolved_settings, sqlite_engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        initialize_database(sqlite_engine)
        await services["game"].start()
        logger.info("application_started", extra={"version": __version__})
        try:
            yield
        finally:
            await services["game"].stop()
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
    app.state.conversation_store = conversation_store
    app.state.qdrant_probe = qdrant_probe
    app.state.services = services

    templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")
    app.include_router(health_router)
    app.include_router(create_page_router(templates))
    app.include_router(
        create_chat_router(
            services["agent"], conversation_store,
            services["recipe"], services["wiki"],
        )
    )
    app.include_router(create_recipe_router(services["recipe"]))
    app.include_router(create_game_router(services["game"]))
    app.include_router(
        create_admin_router(
            settings=resolved_settings,
            recipe_service=services["recipe"],
            wiki_service=services["wiki"],
            game_service=services["game"],
            agent_service=services["agent"],
        )
    )

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
