"""Application error contracts."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for safe, user-facing domain failures."""

    code = "internal_error"
    status_code = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DependencyUnavailable(AppError):
    """A required external dependency is temporarily unavailable."""

    code = "dependency_unavailable"
    status_code = 503
