"""Game log tailer, death parser, and detector tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mc_pilot.app import create_app
from mc_pilot.config import Settings
from mc_pilot.game.death_parser import parse_death
from mc_pilot.game.detector import (
    extract_player_from_log,
    extract_version_from_log,
)
from mc_pilot.game.models import DeathCategory, DeathEvent, GameState
from mc_pilot.game.tailer import LogTailer

# ── Death parser tests ─────────────────────────────────────────────────


def test_parse_en_fall_death() -> None:
    line = "[10:00:00] [Server thread/INFO]: TestPlayer fell from a high place"
    event = parse_death(line, "TestPlayer")
    assert event is not None
    assert event.category == DeathCategory.fall
    assert event.player_name == "TestPlayer"
    assert event.source == "en_us"


def test_parse_en_mob_death() -> None:
    line = "[10:00:00] [Server thread/INFO]: TestPlayer was slain by Zombie"
    event = parse_death(line, "TestPlayer")
    assert event is not None
    assert event.category == DeathCategory.mob
    assert event.raw_message == "TestPlayer was slain by Zombie"


def test_parse_en_lava_death() -> None:
    line = "[10:00:00] [Server thread/INFO]: TestPlayer tried to swim in lava"
    event = parse_death(line, "TestPlayer")
    assert event is not None
    assert event.category == DeathCategory.lava


def test_parse_en_drowning_death() -> None:
    line = "[10:00:00] [Server thread/INFO]: TestPlayer drowned"
    event = parse_death(line, "TestPlayer")
    assert event is not None
    assert event.category == DeathCategory.drowning


def test_parse_en_starvation_death() -> None:
    line = "[10:00:00] [Server thread/INFO]: TestPlayer starved to death"
    event = parse_death(line, "TestPlayer")
    assert event is not None
    assert event.category == DeathCategory.starvation


def test_parse_en_void_death() -> None:
    line = "[10:00:00] [Server thread/INFO]: TestPlayer fell out of the world"
    event = parse_death(line, "TestPlayer")
    assert event is not None
    assert event.category == DeathCategory.void


def test_parse_en_freeze_death() -> None:
    line = "[10:00:00] [Server thread/INFO]: TestPlayer froze to death"
    event = parse_death(line, "TestPlayer")
    assert event is not None
    assert event.category == DeathCategory.freeze


def test_parse_zh_fall_death() -> None:
    line = "[10:00:00] [Server thread/INFO]: TestPlayer从高处摔了下来"
    event = parse_death(line, "TestPlayer")
    assert event is not None
    assert event.category == DeathCategory.fall
    assert event.source == "zh_cn"


def test_parse_zh_mob_death() -> None:
    line = "[10:00:00] [Server thread/INFO]: TestPlayer被僵尸杀死了"
    event = parse_death(line, "TestPlayer")
    assert event is not None
    assert event.category == DeathCategory.mob


def test_parse_zh_lava_death() -> None:
    line = "[10:00:00] [Server thread/INFO]: TestPlayer试图在熔岩里游泳"
    event = parse_death(line, "TestPlayer")
    assert event is not None
    assert event.category == DeathCategory.lava


def test_parse_zh_starvation_death() -> None:
    line = "[10:00:00] [Server thread/INFO]: TestPlayer饿死了"
    event = parse_death(line, "TestPlayer")
    assert event is not None
    assert event.category == DeathCategory.starvation


def test_parse_zh_void_death() -> None:
    line = "[10:00:00] [Server thread/INFO]: TestPlayer掉出了这个世界"
    event = parse_death(line, "TestPlayer")
    assert event is not None
    assert event.category == DeathCategory.void


def test_parse_non_death_line_returns_none() -> None:
    line = "[10:00:00] [Server thread/INFO]: TestPlayer has made the advancement [Stone Age]"
    event = parse_death(line, "TestPlayer")
    assert event is None


def test_parse_other_player_death_ignored() -> None:
    line = "[10:00:00] [Server thread/INFO]: OtherPlayer was slain by Zombie"
    event = parse_death(line, "TestPlayer")
    assert event is None


def test_parse_unknown_death_with_player_name() -> None:
    line = "[10:00:00] [Server thread/INFO]: TestPlayer died"
    event = parse_death(line, "TestPlayer")
    assert event is not None
    assert event.category == DeathCategory.unknown
    assert event.confidence == 0.3


# ── Log tailer tests ───────────────────────────────────────────────────


def test_tailer_reads_new_lines(tmp_path: Path) -> None:
    log_file = tmp_path / "latest.log"
    log_file.write_text("line1\nline2\n", encoding="utf-8")

    tailer = LogTailer(log_file)
    tailer._offset = 0  # force reading from start
    lines = tailer.poll()
    assert len(lines) == 2
    assert lines == ["line1", "line2"]


def test_tailer_only_reads_appended_content(tmp_path: Path) -> None:
    log_file = tmp_path / "latest.log"
    log_file.write_text("line1\n", encoding="utf-8")

    tailer = LogTailer(log_file)
    # After init, offset is at end
    lines = tailer.poll()
    assert lines == []

    with open(log_file, "a") as f:
        f.write("line2\n")

    lines = tailer.poll()
    assert lines == ["line2"]


def test_tailer_detects_truncation(tmp_path: Path) -> None:
    log_file = tmp_path / "latest.log"
    log_file.write_text("long line of text that fills the file\n", encoding="utf-8")

    tailer = LogTailer(log_file)
    # Move offset past where the truncated file would end
    tailer._offset = 1000

    log_file.write_text("short\n", encoding="utf-8")
    lines = tailer.poll()
    assert lines == ["short"]
    assert tailer.truncation_count >= 1


def test_tailer_empty_lines_filtered(tmp_path: Path) -> None:
    log_file = tmp_path / "latest.log"
    log_file.write_text("line1\n\n\nline2\n", encoding="utf-8")

    tailer = LogTailer(log_file)
    tailer._offset = 0
    lines = tailer.poll()
    assert lines == ["line1", "line2"]


# ── Detector tests ─────────────────────────────────────────────────────


def test_extract_version() -> None:
    lines = [
        "[09:00:00] [Render thread/INFO]: Setting user: TestPlayer",
        "[09:00:01] [Render thread/INFO]: LWJGL: 3.3.3",
        "[09:00:02] [Render thread/INFO]: Backend library: NVIDIA",
        "[09:00:03] [Render thread/INFO]: Narrator library: Flite",
        "[09:00:04] [Render thread/INFO]: Reloading ResourceManager: vanilla",
        "[09:00:05] [Render thread/INFO]: Minecraft 26.2",
    ]
    version = extract_version_from_log(lines)
    assert version == "26.2"


def test_extract_version_none() -> None:
    lines = ["[09:00:00] [Render thread/INFO]: Setting user: TestPlayer"]
    version = extract_version_from_log(lines)
    assert version is None


def test_extract_player() -> None:
    lines = [
        "[09:00:00] [Render thread/INFO]: Setting user: TestPlayer",
        "[09:00:10] [Server thread/INFO]: TestPlayer joined the world",
    ]
    player = extract_player_from_log(lines)
    assert player == "TestPlayer"


def test_extract_player_en_locale() -> None:
    lines = [
        "[09:00:10] [Server thread/INFO]: CoolSteve joined the game",
    ]
    player = extract_player_from_log(lines)
    assert player == "CoolSteve"


def test_extract_player_none() -> None:
    lines = ["[09:00:00] [Render thread/INFO]: Starting Minecraft"]
    player = extract_player_from_log(lines)
    assert player is None


def test_extract_player_from_client_setting() -> None:
    lines = ["[09:00:00] [Render thread/INFO]: Setting user: LocalSteve"]
    assert extract_player_from_log(lines) == "LocalSteve"


def test_extract_player_chinese_name() -> None:
    lines = [
        "[09:00:10] [Server thread/INFO]: 我的世界玩家 joined the game",
    ]
    player = extract_player_from_log(lines)
    assert player == "我的世界玩家"


# ── Model tests ────────────────────────────────────────────────────────


def test_death_event_deduplication() -> None:
    ts = datetime.now(UTC)
    e1 = DeathEvent.build_event_id("Player", "fell from a high place", ts)
    e2 = DeathEvent.build_event_id("Player", "fell from a high place", ts)
    assert e1 == e2

    e3 = DeathEvent.build_event_id("Player", "was slain by Zombie", ts)
    assert e1 != e3


def test_repeated_log_line_has_stable_event_id() -> None:
    line = "[10:00:00] [Server thread/INFO]: Player fell from a high place"
    first = parse_death(line, "Player", datetime(2026, 1, 1, tzinfo=UTC))
    second = parse_death(line, "Player", datetime(2026, 1, 2, tzinfo=UTC))
    assert first is not None and second is not None
    assert first.event_id == second.event_id


def test_game_state_defaults() -> None:
    state = GameState()
    assert state.state == "disconnected"
    assert state.death_count == 0
    assert state.player_name == ""


def test_app_lifespan_starts_and_stops_configured_listener(tmp_path: Path) -> None:
    log_file = tmp_path / "latest.log"
    log_file.write_text("[Render thread/INFO]: Minecraft 26.2\n", encoding="utf-8")
    settings = Settings(
        _env_file=None,
        sqlite_url=f"sqlite:///{tmp_path / 'app.db'}",
        qdrant_url="http://127.0.0.1:1",
        game_log_path=str(log_file),
        DEEPSEEK_API_KEY="sk-test",
    )
    app = create_app(settings)
    game_service = app.state.services["game"]

    assert game_service.is_running is False
    with TestClient(app):
        assert game_service.is_running is True
        assert game_service.advice_enabled is True
    assert game_service.is_running is False


def test_app_without_api_key_disables_death_advice(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        sqlite_url=f"sqlite:///{tmp_path / 'app.db'}",
        qdrant_url="http://127.0.0.1:1",
    )
    app = create_app(settings)

    assert app.state.services["game"].advice_enabled is False


def test_websocket_disconnect_removes_advice_callback(client: TestClient) -> None:
    assert isinstance(client.app, FastAPI)
    game_service = client.app.state.services["game"]
    assert game_service.advice_subscriber_count == 0
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("ping")
        assert websocket.receive_json() == {"type": "pong"}
        assert game_service.advice_subscriber_count == 1
    assert game_service.advice_subscriber_count == 0
