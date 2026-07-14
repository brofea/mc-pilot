"""Tests for conversation persistence, SSE streaming, and memory fix."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine

from mc_pilot.agent.loop import AgentLoop
from mc_pilot.agent.memory import ConversationMemory
from mc_pilot.agent.models import AgentTurn, ToolCall
from mc_pilot.storage.sqlite import ConversationStore, initialize_database


def _cid(conv: dict[str, object]) -> str:
    return str(conv["id"])


# ── ConversationStore tests ────────────────────────────────────────────


class TestConversationStore:
    @pytest.fixture(autouse=True)
    def _store(self, tmp_path: Path) -> None:
        self._db_path = tmp_path / "store_test.db"
        eng = create_engine(f"sqlite:///{self._db_path}")
        initialize_database(eng)
        self._store_obj = ConversationStore(eng)

    def test_create_conversation(self) -> None:
        conv = self._store_obj.create_conversation("测试对话")
        assert conv["title"] == "测试对话"
        assert conv["id"]

    def test_create_conversation_default_title(self) -> None:
        conv = self._store_obj.create_conversation()
        assert conv["title"] == "新对话"

    def test_list_conversations_empty(self) -> None:
        result = self._store_obj.list_conversations()
        assert isinstance(result, list)
        assert len(result) == 0

    def test_list_conversations_ordered(self) -> None:
        c1 = self._store_obj.create_conversation("第一")
        self._store_obj.create_conversation("第二")
        c3 = self._store_obj.create_conversation("第三")
        result = self._store_obj.list_conversations()
        assert len(result) == 3
        assert result[0]["id"] == c3["id"]
        assert result[2]["id"] == c1["id"]

    def test_get_conversation_not_found(self) -> None:
        assert self._store_obj.get_conversation("nonexistent") is None

    def test_get_conversation_with_messages(self) -> None:
        conv = self._store_obj.create_conversation("带消息的对话")
        self._store_obj.add_message(_cid(conv), "user", "你好")
        self._store_obj.add_message(_cid(conv), "assistant", "你好！")
        retrieved = self._store_obj.get_conversation(_cid(conv))
        assert retrieved is not None
        assert len(retrieved["messages"]) == 2  # type: ignore[arg-type]
        assert retrieved["messages"][0]["role"] == "user"  # type: ignore[index]
        assert retrieved["messages"][1]["role"] == "assistant"  # type: ignore[index]

    def test_add_message_to_nonexistent_conversation(self) -> None:
        result = self._store_obj.add_message("nonexistent", "user", "hi")
        assert result is None

    def test_add_message_updates_conversation_timestamp(self) -> None:
        conv = self._store_obj.create_conversation("时间戳测试")
        original = self._store_obj.get_conversation(_cid(conv))
        assert original is not None
        self._store_obj.add_message(_cid(conv), "user", "hello")
        updated = self._store_obj.get_conversation(_cid(conv))
        assert updated is not None
        assert updated["updated_at"] != original["updated_at"]

    def test_update_title(self) -> None:
        conv = self._store_obj.create_conversation("旧标题")
        ok = self._store_obj.update_title(_cid(conv), "新标题")
        assert ok
        retrieved = self._store_obj.get_conversation(_cid(conv))
        assert retrieved is not None
        assert retrieved["title"] == "新标题"

    def test_update_title_nonexistent(self) -> None:
        ok = self._store_obj.update_title("nonexistent", "标题")
        assert not ok

    def test_delete_conversation(self) -> None:
        conv = self._store_obj.create_conversation("待删除")
        self._store_obj.add_message(_cid(conv), "user", "test")
        ok = self._store_obj.delete_conversation(_cid(conv))
        assert ok
        assert self._store_obj.get_conversation(_cid(conv)) is None

    def test_delete_conversation_nonexistent(self) -> None:
        ok = self._store_obj.delete_conversation("nonexistent")
        assert not ok

    def test_delete_cascades_messages(self) -> None:
        conv = self._store_obj.create_conversation("级联删除")
        msg = self._store_obj.add_message(_cid(conv), "user", "will be deleted")
        assert msg is not None
        self._store_obj.delete_conversation(_cid(conv))
        messages = self._store_obj.get_messages(_cid(conv))
        assert len(messages) == 0

    def test_get_messages_ordered(self) -> None:
        conv = self._store_obj.create_conversation("排序测试")
        self._store_obj.add_message(_cid(conv), "user", "1")
        self._store_obj.add_message(_cid(conv), "assistant", "2")
        self._store_obj.add_message(_cid(conv), "user", "3")
        messages = self._store_obj.get_messages(_cid(conv))
        assert len(messages) == 3
        assert [m["content"] for m in messages] == ["1", "2", "3"]

    def test_multiple_conversations_isolation(self) -> None:
        c1 = self._store_obj.create_conversation("A")
        c2 = self._store_obj.create_conversation("B")
        self._store_obj.add_message(_cid(c1), "user", "msg to A")
        self._store_obj.add_message(_cid(c2), "user", "msg to B")
        assert len(self._store_obj.get_messages(_cid(c1))) == 1
        assert len(self._store_obj.get_messages(_cid(c2))) == 1


# ── strip_tool_context fix tests ──────────────────────────────────────


class TestStripToolContext:
    def test_keeps_normal_user_and_assistant(self) -> None:
        mem = ConversationMemory()
        mem.add_user("Q1")
        mem.add_assistant("A1")
        assert len(mem._turns) == 2
        mem.strip_tool_context()
        assert len(mem._turns) == 2
        assert mem._turns[0].role == "user"
        assert mem._turns[1].role == "assistant"

    def test_removes_stale_tool_results(self) -> None:
        mem = ConversationMemory()
        mem._turns = [
            AgentTurn(role="user", content="Q1"),
            AgentTurn(
                role="assistant",
                content="",
                tool_calls=(
                    ToolCall(id="c1", name="wiki_search", arguments={"query": "石头"}),
                ),
            ),
            AgentTurn(role="tool", content="搜索结果", tool_call_id="c1"),
        ]
        mem.strip_tool_context()
        assert len(mem._turns) == 1
        assert mem._turns[0].role == "user"

    def test_removes_trail_of_multi_tool_messages(self) -> None:
        mem = ConversationMemory()
        mem._turns = [
            AgentTurn(role="user", content="Q1"),
            AgentTurn(
                role="assistant",
                content="",
                tool_calls=(ToolCall(id="c1", name="wiki_search", arguments={}),),
            ),
            AgentTurn(role="tool", content="r1", tool_call_id="c1"),
            AgentTurn(
                role="assistant",
                content="",
                tool_calls=(ToolCall(id="c2", name="recipe_query", arguments={}),),
            ),
            AgentTurn(role="tool", content="r2", tool_call_id="c2"),
        ]
        mem.strip_tool_context()
        assert len(mem._turns) == 1
        assert mem._turns[0].role == "user"

    def test_keeps_assistant_without_tool_calls_after_user(self) -> None:
        mem = ConversationMemory()
        mem._turns = [
            AgentTurn(role="user", content="Q1"),
            AgentTurn(role="assistant", content="A1"),
            AgentTurn(role="user", content="Q2"),
            AgentTurn(role="assistant", content="A2"),
        ]
        mem.strip_tool_context()
        assert len(mem._turns) == 4

    def test_strip_on_empty_does_nothing(self) -> None:
        mem = ConversationMemory()
        mem.strip_tool_context()
        assert len(mem._turns) == 0

    def test_strip_preserves_normal_conversation_flow(self) -> None:
        mem = ConversationMemory()
        mem.add_user("Q1")
        mem.add_assistant("A1")
        mem.strip_tool_context()
        mem.add_user("Q2")
        messages = mem.as_messages()
        assert len(messages) == 4
        assert messages[1]["content"] == "Q1"
        assert messages[2]["content"] == "A1"
        assert messages[3]["content"] == "Q2"


# ── Streaming event tests ─────────────────────────────────────────────


class TestAgentLoopStreaming:
    def make_client(self) -> MagicMock:
        client = MagicMock()
        response = MagicMock()
        response.usage = {"total_tokens": 100}
        choice = MagicMock()
        choice.message = {"content": "测试回答"}
        choice.finish_reason = "stop"
        response.choices = [choice]
        client.chat = AsyncMock(return_value=response)
        return client

    def make_tool_executor(self) -> AsyncMock:
        return AsyncMock(return_value="工具结果")

    def test_emits_thinking_start(self) -> None:
        events: list[dict[str, Any]] = []

        async def capture(event_type: str, data: dict[str, Any]) -> None:
            events.append({"type": event_type, **data})

        client = self.make_client()
        memory = ConversationMemory()
        loop = AgentLoop(
            client=client,
            memory=memory,
            tool_executor=self.make_tool_executor(),
            exported_tools=[],
            on_event=capture,
        )
        asyncio.run(loop.run("测试"))
        event_types = [e["type"] for e in events]
        assert "status" in event_types
        assert "thinking" in event_types
        assert "done" in event_types

    def test_emits_tool_events_when_tool_called(self) -> None:
        events: list[dict[str, Any]] = []

        async def capture(event_type: str, data: dict[str, Any]) -> None:
            events.append({"type": event_type, **data})

        client = self.make_client()
        choice = MagicMock()
        choice.message = {
            "content": "",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "wiki_search",
                        "arguments": json.dumps({"query": "石头"}),
                    },
                }
            ],
        }
        choice.finish_reason = "tool_calls"
        client.chat.side_effect = [
            MagicMock(usage={"total_tokens": 100}, choices=[choice]),
            MagicMock(
                usage={"total_tokens": 50},
                choices=[MagicMock(message={"content": "最终回答"}, finish_reason="stop")],
            ),
        ]

        memory = ConversationMemory()
        loop = AgentLoop(
            client=client,
            memory=memory,
            tool_executor=self.make_tool_executor(),
            exported_tools=[],
            on_event=capture,
        )
        asyncio.run(loop.run("查询石头"))
        event_types = [e["type"] for e in events]
        assert "tool_start" in event_types
        assert "tool_end" in event_types
        assert "done" in event_types

    def test_done_event_contains_answer(self) -> None:
        events: list[dict[str, Any]] = []

        async def capture(event_type: str, data: dict[str, Any]) -> None:
            events.append({"type": event_type, **data})

        client = self.make_client()
        memory = ConversationMemory()
        loop = AgentLoop(
            client=client,
            memory=memory,
            tool_executor=self.make_tool_executor(),
            exported_tools=[],
            on_event=capture,
        )
        asyncio.run(loop.run("你好"))
        done_events = [e for e in events if e["type"] == "done"]
        assert len(done_events) == 1
        assert done_events[0]["answer"] == "测试回答"

    def test_no_events_when_no_callback(self) -> None:
        client = self.make_client()
        memory = ConversationMemory()
        loop = AgentLoop(
            client=client,
            memory=memory,
            tool_executor=self.make_tool_executor(),
            exported_tools=[],
            on_event=None,
        )
        result = asyncio.run(loop.run("测试"))
        assert result.state.value == "answered"
        assert result.answer == "测试回答"

    def test_budget_exceeded_emits_no_events(self) -> None:
        events: list[dict[str, Any]] = []

        async def capture(event_type: str, data: dict[str, Any]) -> None:
            events.append({"type": event_type, **data})

        client = self.make_client()
        memory = ConversationMemory(daily_limit=10)
        memory.consume_tokens(10)

        loop = AgentLoop(
            client=client,
            memory=memory,
            tool_executor=self.make_tool_executor(),
            exported_tools=[],
            on_event=capture,
        )
        asyncio.run(loop.run("测试"))
        assert client.chat.call_count == 0


# ── API conversation endpoint tests ────────────────────────────────────


class TestConversationAPI:
    def test_list_conversations_empty(self, client: Any) -> None:
        resp = client.get("/api/conversations")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_and_list_conversations(self, client: Any) -> None:
        resp = client.post("/api/conversations")
        assert resp.status_code == 200
        conv = resp.json()
        assert "id" in conv
        assert "title" in conv

        resp2 = client.get("/api/conversations")
        assert resp2.status_code == 200
        assert len(resp2.json()) >= 1

    def test_get_nonexistent_conversation(self, client: Any) -> None:
        resp = client.get("/api/conversations/nonexistent")
        assert resp.status_code == 404

    def test_get_conversation_with_messages(self, client: Any) -> None:
        resp = client.post("/api/conversations")
        conv_id = resp.json()["id"]

        chat_resp = client.post(
            "/api/chat",
            json={"message": "/pilot help", "conversation_id": conv_id},
        )
        assert chat_resp.status_code == 200

        conv_resp = client.get(f"/api/conversations/{conv_id}")
        assert conv_resp.status_code == 200
        data = conv_resp.json()
        assert len(data["messages"]) >= 2

    def test_delete_conversation(self, client: Any) -> None:
        resp = client.post("/api/conversations")
        conv_id = resp.json()["id"]

        del_resp = client.delete(f"/api/conversations/{conv_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True

        get_resp = client.get(f"/api/conversations/{conv_id}")
        assert get_resp.status_code == 404

    def test_update_conversation_title(self, client: Any) -> None:
        resp = client.post("/api/conversations")
        conv_id = resp.json()["id"]

        patch_resp = client.patch(
            f"/api/conversations/{conv_id}",
            json={"title": "改名测试"},
        )
        assert patch_resp.status_code == 200

        get_resp = client.get(f"/api/conversations/{conv_id}")
        assert get_resp.json()["title"] == "改名测试"

    def test_update_title_empty_rejected(self, client: Any) -> None:
        resp = client.post("/api/conversations")
        conv_id = resp.json()["id"]

        patch_resp = client.patch(
            f"/api/conversations/{conv_id}",
            json={"title": ""},
        )
        assert patch_resp.status_code == 400
