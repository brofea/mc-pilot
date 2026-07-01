"""Developer admin API routes with loopback-only guard."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from ipaddress import ip_address
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from mc_pilot.config import Settings

logger = logging.getLogger(__name__)


def _require_loopback(request: Request) -> None:
    client_host = request.client.host if request.client else ""
    request_host = request.url.hostname or ""

    if request_host not in ("127.0.0.1", "::1", "localhost", "testserver"):
        raise HTTPException(status_code=403, detail="仅允许本机访问")

    try:
        source = ip_address(client_host)
    except ValueError:
        if client_host != "testclient":
            raise HTTPException(status_code=403, detail="仅允许本机访问") from None
        return

    # Docker Desktop forwards a host-loopback request through its private gateway.
    if not (source.is_loopback or source.is_private):
        raise HTTPException(status_code=403, detail="仅允许本机访问")


def create_admin_router(
    settings: Settings,
    recipe_service: Any = None,
    wiki_service: Any = None,
    game_service: Any = None,
    agent_service: Any = None,
) -> APIRouter:
    router = APIRouter(prefix="/admin/api", tags=["admin"])

    @router.get("/status")
    async def system_status(request: Request) -> dict[str, object]:
        _require_loopback(request)
        return {
            "version": "0.1.0",
            "started": datetime.now(UTC).isoformat(),
            "platform": "macOS/Docker",
            "environment": settings.environment,
        }

    @router.get("/game")
    async def game_diag(request: Request) -> dict[str, object]:
        _require_loopback(request)
        if not game_service:
            return {"available": False}
        s = game_service.state
        return {
            "available": True,
            "state": s.state,
            "version_id": s.version_id,
            "player_name": s.player_name,
            "log_path": s.log_path,
            "last_activity": s.last_activity.isoformat() if s.last_activity else None,
            "death_count": s.death_count,
            "ws_clients": s.web_socket_clients,
        }

    @router.get("/recipes")
    async def recipe_diag(request: Request) -> dict[str, object]:
        _require_loopback(request)
        return {
            "available": recipe_service is not None,
            "version_id": recipe_service.version_id if recipe_service else None,
        }

    @router.get("/rag")
    async def rag_diag(request: Request) -> dict[str, object]:
        _require_loopback(request)
        has_wiki = wiki_service is not None
        return {
            "available": has_wiki,
            "index_exists": False,
        }

    @router.get("/llm")
    async def llm_diag(request: Request) -> dict[str, object]:
        _require_loopback(request)
        return {
            "configured": agent_service.is_configured() if agent_service else False,
            "model": settings.deepseek_model,
            "base_url": settings.deepseek_base_url,
        }

    @router.get("/config")
    async def config_diag(request: Request) -> dict[str, str | int | bool]:
        _require_loopback(request)
        return settings.safe_summary()

    @router.get("/health-check")
    async def diag_health(request: Request) -> dict[str, object]:
        _require_loopback(request)
        return {"status": "ok"}

    @router.post("/reconnect-log")
    async def reconnect_log(request: Request) -> dict[str, object]:
        _require_loopback(request)
        if game_service:
            await game_service.start()
        return {"action": "reconnect_log", "status": "done"}

    @router.post("/rebuild-wiki")
    async def rebuild_wiki(request: Request) -> dict[str, object]:
        _require_loopback(request)
        return {"action": "rebuild_wiki", "status": "not_implemented"}

    return router
