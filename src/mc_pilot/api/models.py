"""Shared API response models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ComponentStatus(BaseModel):
    """Readiness of one local component."""

    name: str
    status: Literal["ready", "degraded", "not_configured"]
    detail: str | None = None


class LivenessResponse(BaseModel):
    """Process liveness response."""

    status: Literal["alive"] = "alive"
    version: str


class ReadinessResponse(BaseModel):
    """Aggregate dependency readiness response."""

    status: Literal["ready", "degraded"]
    components: list[ComponentStatus] = Field(default_factory=list)


class ErrorBody(BaseModel):
    """Safe error description."""

    code: str
    message: str
    request_id: str
    details: dict[str, object] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standard API error envelope."""

    error: ErrorBody
