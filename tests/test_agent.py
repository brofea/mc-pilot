"""Agent state machine, memory, and tool contract tests."""

from __future__ import annotations

from mc_pilot.agent.memory import ConversationMemory
from mc_pilot.agent.models import (
    AgentResponse,
    AgentState,
    AgentTurn,
    ConnectivityResult,
    SessionMemory,
    ToolCall,
    ToolMessage,
    ToolResult,
    TraceEntry,
)
from mc_pilot.agent.tools import (
    ALL_TOOLS,
    RECIPE_DIRECT_TOOL,
    RECIPE_QUERY_TOOL,
    TOOL_WHITELIST,
    WIKI_SEARCH_TOOL,
)

# ── Tool contract tests ────────────────────────────────────────────────


def test_wiki_search_tool_has_required_fields() -> None:
    assert WIKI_SEARCH_TOOL.name == "wiki_search"
    assert "query" in WIKI_SEARCH_TOOL.parameters.get("required", [])
    assert WIKI_SEARCH_TOOL.parameters["type"] == "object"


def test_recipe_query_tool_has_required_fields() -> None:
    assert RECIPE_QUERY_TOOL.name == "recipe_query"
    assert "item_id" in RECIPE_QUERY_TOOL.parameters.get("required", [])


def test_recipe_direct_tool() -> None:
    assert RECIPE_DIRECT_TOOL.name == "recipe_direct"


def test_all_tools_in_whitelist() -> None:
    for tool in ALL_TOOLS:
        assert tool.name in TOOL_WHITELIST


# ── Memory tests ───────────────────────────────────────────────────────


def test_memory_starts_empty() -> None:
    mem = ConversationMemory()
    messages = mem.as_messages()
    assert len(messages) == 1  # system message
    assert messages[0]["role"] == "system"


def test_memory_adds_turns() -> None:
    mem = ConversationMemory()
    mem.add_user("你好")
    mem.add_assistant("你好！")
    messages = mem.as_messages()
    assert len(messages) == 3
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"


def test_memory_clear_removes_all() -> None:
    mem = ConversationMemory()
    mem.add_user("测试")
    mem.clear()
    messages = mem.as_messages()
    assert len(messages) == 1


def test_memory_token_budget() -> None:
    mem = ConversationMemory(daily_limit=1000)
    mem.consume_tokens(600)
    assert not mem.is_over_budget
    mem.consume_tokens(500)
    assert mem.is_over_budget


def test_memory_adds_tool_result() -> None:
    mem = ConversationMemory()
    result = ToolResult(
        tool_call_id="call_1",
        name="wiki_search",
        success=True,
        content="搜索结果文本...",
    )
    mem.add_tool_result(result)
    assert len(mem._turns) == 1
    assert mem._turns[0].role == "tool"


# ── Model tests ────────────────────────────────────────────────────────


def test_tool_call_model() -> None:
    tc = ToolCall(id="call_1", name="wiki_search", arguments={"query": "石头"})
    assert tc.name == "wiki_search"
    assert tc.arguments["query"] == "石头"


def test_tool_result_model() -> None:
    tr = ToolResult(
        tool_call_id="call_1",
        name="wiki_search",
        success=True,
        content="石头是...",
    )
    assert tr.success
    assert "石头" in tr.content


def test_trace_entry_model() -> None:
    entry = TraceEntry(
        step=0,
        state=AgentState.received,
        event="user_message_received",
    )
    assert entry.state == "received"


def test_agent_response_defaults() -> None:
    resp = AgentResponse(state=AgentState.answered, answer="完成")
    assert resp.state == "answered"
    assert resp.answer == "完成"
    assert resp.trace == ()
    assert resp.stop_reason is None


def test_connectivity_result_success() -> None:
    result = ConnectivityResult(
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
        success=True,
        latency_ms=150.0,
        prompt_tokens=10,
        completion_tokens=5,
        answer="连接成功",
    )
    assert result.success
    assert result.latency_ms > 0


def test_connectivity_result_failure() -> None:
    result = ConnectivityResult(
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
        success=False,
        latency_ms=0,
        error="Connection refused",
    )
    assert not result.success
    assert result.error == "Connection refused"


def test_session_memory_model() -> None:
    sm = SessionMemory()
    assert sm.turns == []
    assert sm.daily_tokens == 0
    assert sm.daily_limit == 500_000


def test_agent_turn_model() -> None:
    turn = AgentTurn(role="user", content="你好")
    assert turn.role == "user"
    assert turn.content == "你好"


# ── ToolMessage schema tests ───────────────────────────────────────────


def test_tool_message_converts_to_openai_format() -> None:
    tool = ToolMessage(
        name="test_tool",
        description="A test tool",
        parameters={"type": "object", "properties": {}},
    )
    from mc_pilot.agent.client import DeepSeekClient

    schemas = DeepSeekClient.build_tool_schema([tool])
    assert len(schemas) == 1
    assert schemas[0]["type"] == "function"
    assert schemas[0]["function"]["name"] == "test_tool"


def test_deepseek_usage_discards_nested_provider_details() -> None:
    from mc_pilot.agent.client import _normalize_usage

    usage = _normalize_usage(
        {
            "prompt_tokens": 640,
            "completion_tokens": 19,
            "total_tokens": 659,
            "prompt_tokens_details": {"cached_tokens": 512},
            "completion_tokens_details": {"reasoning_tokens": 19},
        }
    )

    assert usage == {
        "prompt_tokens": 640,
        "completion_tokens": 19,
        "total_tokens": 659,
    }
