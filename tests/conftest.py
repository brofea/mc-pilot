"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mc_pilot.app import create_app
from mc_pilot.config import Settings


class StubQdrantProbe:
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
        DEEPSEEK_API_KEY="sk-test",
    )
    app = create_app(settings)
    original = app.state.qdrant_probe
    app.state.qdrant_probe = StubQdrantProbe(ready=False)
    original.close()
    with TestClient(app) as c:
        yield c
