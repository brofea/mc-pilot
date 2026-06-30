"""Application boundary tests for the M1 foundation."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_liveness_is_independent_of_qdrant(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive", "version": "0.1.0"}


def test_readiness_reports_degraded_dependency(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["components"] == [
        {"name": "sqlite", "status": "ready", "detail": None},
        {
            "name": "qdrant",
            "status": "degraded",
            "detail": "Vector database is unavailable.",
        },
    ]


@pytest.mark.parametrize(
    ("path", "heading"),
    [("/", "Minecraft Pilot"), ("/admin", "开发者后台")],
)
def test_pages_render_without_frontend_build(
    client: TestClient, path: str, heading: str
) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert heading in response.text
    assert "DEEPSEEK_API_KEY" not in response.text
