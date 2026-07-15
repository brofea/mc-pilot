"""Short-term session memory with budget tracking and history replay."""

from __future__ import annotations

import logging

from mc_pilot.agent.limits import DAILY_TOKEN_LIMIT
from mc_pilot.agent.models import AgentTurn, ToolResult
from mc_pilot.agent.policy import SYSTEM_PROMPT, format_untrusted_tool_result

logger = logging.getLogger(__name__)

MAX_TURNS = 12


class ConversationMemory:
    """Per-session short conversation buffer and token budget."""

    _turns: list[AgentTurn]
    _daily_tokens: int
    _daily_limit: int

    def __init__(self, daily_limit: int = DAILY_TOKEN_LIMIT) -> None:
        self._turns = []
        self._daily_tokens = 0
        self._daily_limit = daily_limit

    def add_user(self, content: str) -> None:
        self._turns.append(AgentTurn(role="user", content=content))
        self._trim()

    def add_assistant(self, content: str) -> None:
        self._turns.append(AgentTurn(role="assistant", content=content))
        self._trim()

    def add_tool_result(self, result: ToolResult) -> None:
        content = result.content if result.success else f"错误: {result.error or '未知错误'}"
        self._turns.append(
            AgentTurn(
                role="tool",
                content=format_untrusted_tool_result(content),
                tool_call_id=result.tool_call_id,
            )
        )
        self._trim()

    def load_history(self, messages: list[dict[str, str]]) -> None:
        """Replay a conversation history from persisted messages (user/assistant only).
        Tool messages are skipped — they are transient within a single agent run."""
        self._turns.clear()
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            if role == "user":
                self._turns.append(AgentTurn(role="user", content=content))
            elif role == "assistant" and content:
                self._turns.append(AgentTurn(role="assistant", content=content))
        self._trim()

    def detach(self) -> ConversationMemory:
        """Create an independent copy that shares the same token budget."""
        clone = ConversationMemory(daily_limit=self._daily_limit)
        clone._daily_tokens = self._daily_tokens
        clone._turns = list(self._turns)
        return clone

    def consume_tokens(self, count: int) -> int:
        self._daily_tokens += count
        return self._daily_tokens

    @property
    def daily_tokens(self) -> int:
        return self._daily_tokens

    @property
    def daily_limit(self) -> int:
        return self._daily_limit

    @property
    def is_over_budget(self) -> bool:
        return self._daily_tokens >= self._daily_limit

    def as_messages(self) -> list[dict[str, object]]:
        import json

        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]
        for turn in self._turns:
            msg: dict[str, object] = {"role": turn.role, "content": turn.content}
            if turn.role == "assistant" and turn.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                        },
                    }
                    for tc in turn.tool_calls
                ]
                msg["content"] = ""
            if turn.role == "tool" and turn.tool_call_id:
                msg["tool_call_id"] = turn.tool_call_id
            messages.append(msg)
        return messages

    def clear(self) -> None:
        self._turns.clear()

    def strip_tool_context(self) -> None:
        """Remove assistant(tool_calls) and tool(tool_result) messages
        left over from a previous incomplete agent loop.  These messages
        form an invalid sequence when a fresh user turn is appended."""
        while True:
            while self._turns and self._turns[-1].role == "tool":
                self._turns.pop()
            if (
                self._turns
                and self._turns[-1].role == "assistant"
                and self._turns[-1].tool_calls
            ):
                self._turns.pop()
            else:
                break

    def _trim(self) -> None:
        while len(self._turns) > MAX_TURNS * 2 + 1:
            self._turns.pop(0)
