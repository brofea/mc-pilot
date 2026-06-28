"""Qdrant readiness adapter."""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse


class QdrantProbe:
    """Hide Qdrant client details behind a narrow health interface."""

    def __init__(self, *, url: str, timeout_seconds: int) -> None:
        self._client = QdrantClient(url=url, timeout=timeout_seconds)

    def is_ready(self) -> bool:
        """Return whether Qdrant accepts a collection-list request."""

        try:
            self._client.get_collections()
        except (OSError, ResponseHandlingException, RuntimeError, UnexpectedResponse, ValueError):
            return False
        return True

    def close(self) -> None:
        """Release the underlying HTTP client."""

        self._client.close()
