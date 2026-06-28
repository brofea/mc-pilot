"""Application boundary tests for the M1 foundation."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mc_pilot.app import create_app
from mc_pilot.config import Settings


class StubQdrantProbe:
    """Deterministic readiness probe used at the API boundary."""

    def __init__(self, ready: bool) -> None:
        self.ready = ready

    def is_ready(self) -> bool:
        return self.ready

    def close(self) -> None:
        return None


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    database = tmp_path / "test.db"
    settings = Settings(
        _env_file=None,
        sqlite_url=f"sqlite:///{database}",
        qdrant_url="http://127.0.0.1:1",
        qdrant_timeout_seconds=1,
    )
    app = create_app(settings)
    original_probe = app.state.qdrant_probe
    app.state.qdrant_probe = StubQdrantProbe(ready=False)
    original_probe.close()
    with TestClient(app) as test_client:
        yield test_client


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
    [("/", "你的本地 Minecraft Pilot"), ("/admin", "开发者后台")],
)
def test_pages_render_without_frontend_build(client: TestClient, path: str, heading: str) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert heading in response.text
    assert "DEEPSEEK_API_KEY" not in response.text
