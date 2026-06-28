"""Health and readiness routes."""

from __future__ import annotations

from typing import Protocol

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from mc_pilot import __version__
from mc_pilot.api.models import ComponentStatus, LivenessResponse, ReadinessResponse
from mc_pilot.storage.sqlite import sqlite_is_ready

router = APIRouter(prefix="/health", tags=["health"])


class ReadyProbe(Protocol):
    """Minimal dependency readiness interface."""

    def is_ready(self) -> bool: ...


@router.get("/live", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    """Report whether the process can serve requests."""

    return LivenessResponse(version=__version__)


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(request: Request) -> ReadinessResponse:
    """Report local storage and optional dependency readiness."""

    sqlite_ready = await run_in_threadpool(sqlite_is_ready, request.app.state.sqlite_engine)
    qdrant_ready = await run_in_threadpool(request.app.state.qdrant_probe.is_ready)
    components = [
        ComponentStatus(
            name="sqlite",
            status="ready" if sqlite_ready else "degraded",
            detail=None if sqlite_ready else "Local state database is unavailable.",
        ),
        ComponentStatus(
            name="qdrant",
            status="ready" if qdrant_ready else "degraded",
            detail=None if qdrant_ready else "Vector database is unavailable.",
        ),
    ]
    overall = "ready" if all(item.status == "ready" for item in components) else "degraded"
    return ReadinessResponse(status=overall, components=components)
