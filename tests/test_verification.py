"""Acceptance verification: API routes, redaction, agent limits, degradation."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from mc_pilot.agent.memory import ConversationMemory
from mc_pilot.agent.models import AgentState
from mc_pilot.agent.tools import TOOL_WHITELIST
from mc_pilot.config import Settings
from mc_pilot.recipes.models import RecipeInfo

# ── API route smoke tests ──────────────────────────────────────────────


def test_chat_route_rejects_empty_message(client: TestClient) -> None:
    resp = client.post("/api/chat", json={"message": ""})
    assert resp.status_code == 400


def test_recipes_direct_route_works(client: TestClient) -> None:
    resp = client.get("/api/recipes/minecraft:stone")
    assert resp.status_code == 200
    data = resp.json()
    assert "item_id" in data


def test_game_state_route_works(client: TestClient) -> None:
    resp = client.get("/api/game-state")
    assert resp.status_code == 200
    data = resp.json()
    assert "state" in data


def test_agent_status_route(client: TestClient) -> None:
    resp = client.get("/api/agent-status")
    assert resp.status_code == 200
    assert "configured" in resp.json()


def test_admin_status_route(client: TestClient) -> None:
    resp = client.get("/admin/api/status")
    assert resp.status_code == 200
    assert "version" in resp.json()


def test_admin_rejects_non_loopback_host(client: TestClient) -> None:
    resp = client.get("http://example.com/admin/api/status")
    assert resp.status_code == 403


def test_admin_config_route_does_not_leak_secret(client: TestClient) -> None:
    resp = client.get("/admin/api/config")
    assert resp.status_code == 200
    data = resp.json()
    for val in data.values():
        assert "sk-test" not in str(val)


# ── Config redaction tests ──────────────────────────────────────────────


def test_safe_summary_never_exposes_api_key() -> None:
    settings = Settings(
        _env_file=None,
        DEEPSEEK_API_KEY="sk-secret-key-123",
    )
    summary = settings.safe_summary()
    assert summary["deepseek_configured"] is True
    for v in summary.values():
        assert "sk-secret" not in str(v)


def test_safe_summary_when_key_missing() -> None:
    settings = Settings(_env_file=None)
    summary = settings.safe_summary()
    assert summary["deepseek_configured"] is False


# ── Agent limits and safety tests ──────────────────────────────────────


def test_tool_whitelist_blocks_unknown_tools() -> None:
    assert "delete_files" not in TOOL_WHITELIST
    assert "execute_code" not in TOOL_WHITELIST
    assert "wiki_search" in TOOL_WHITELIST
    assert "recipe_query" in TOOL_WHITELIST
    assert "recipe_direct" in TOOL_WHITELIST
    assert len(TOOL_WHITELIST) == 3


def test_conversation_memory_token_budget_exceeded() -> None:
    mem = ConversationMemory(daily_limit=100)
    mem.consume_tokens(90)
    assert not mem.is_over_budget
    mem.consume_tokens(20)
    assert mem.is_over_budget
    assert mem.daily_tokens == 110


def test_conversation_memory_clear_works() -> None:
    mem = ConversationMemory()
    mem.add_user("msg1")
    mem.add_assistant("reply1")
    assert len(mem._turns) == 2
    mem.clear()
    assert len(mem._turns) == 0


def test_agent_state_values() -> None:
    states = list(AgentState)
    expected = ["received", "deciding", "tool_running", "observing",
                "answered", "stopped", "failed"]
    assert sorted(states) == sorted(expected)


# ── Recipe model tests ─────────────────────────────────────────────────


def test_recipe_determinism() -> None:
    import json

    from mc_pilot.recipes.extractor import parse_recipe

    data = json.loads((Path(__file__).parent / "fixtures" / "sample_recipes.json").read_text())
    raw = data["shaped_enchanting_table"]
    r1 = parse_recipe(raw)
    r2 = parse_recipe(raw)
    assert r1 is not None
    assert r2 is not None
    assert r1.result_item_id == r2.result_item_id
    assert r1.recipe_type == r2.recipe_type


def test_recipe_info_immutable_fields() -> None:
    r = RecipeInfo(
        recipe_id="test",
        recipe_type="minecraft:crafting_shaped",
        result_item_id="minecraft:stone",
    )
    assert r.model_config.get("frozen") is True
    assert r.recipe_id == "test"


# ── Docker compose validation ───────────────────────────────────────────


def test_docker_compose_config_is_valid() -> None:
    compose_path = Path(__file__).parent.parent / "compose.yaml"
    assert compose_path.exists()
    content = compose_path.read_text()
    assert "qdrant" in content
    assert "127.0.0.1" in content
    assert "read_only: true" in content
    assert "MC_PILOT_GAME_LOG_PATH: /minecraft/logs/latest.log" in content
    assert "HF_HOME: /app/data/models" in content


def test_docker_image_contains_operator_scripts() -> None:
    dockerfile = Path(__file__).parent.parent / "Dockerfile"
    content = dockerfile.read_text(encoding="utf-8")
    assert "COPY scripts ./scripts" in content


def test_browser_scripts_do_not_render_external_content_with_inner_html() -> None:
    static_dir = Path(__file__).parent.parent / "src" / "mc_pilot" / "static" / "js"
    for script_name in ("chat.js", "admin.js"):
        content = (static_dir / script_name).read_text(encoding="utf-8")
        assert "textContent" in content
        if ".innerHTML" in content:
            assert "DOMPurify" in content, (
                f"{script_name} uses .innerHTML — must sanitize via DOMPurify first"
            )


# ── Degradation states ──────────────────────────────────────────────────


def test_game_state_starts_disconnected(client: TestClient) -> None:
    resp = client.get("/api/game-state")
    assert resp.status_code == 200
    assert resp.json()["state"] == "disconnected"


def test_health_live_unaffected_by_qdrant(client: TestClient) -> None:
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"
