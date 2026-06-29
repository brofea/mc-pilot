"""Short-term session memory with budget tracking."""

from __future__ import annotations

import logging

from mc_pilot.agent.models import AgentTurn, ToolResult

logger = logging.getLogger(__name__)

MAX_TURNS = 6
DAILY_TOKEN_LIMIT = 200_000


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
        summary = (
            result.content[:200] + "..."
            if len(result.content) > 200
            else result.content
        )
        self._turns.append(
            AgentTurn(
                role="tool",
                content=f"[{result.name}] {summary}",
                tool_call_id=result.tool_call_id,
            )
        )
        self._trim()

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
        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": (
                    "你是 Minecraft Pilot，一个面向中文玩家的 Minecraft 游戏助手。"
                    "你可以搜索 Wiki 知识库和查询合成配方。"
                    "回答要简洁、准确，带有来源引用。"
                    "不确定时明确说明，不编造信息。"
                ),
            }
        ]
        for turn in self._turns:
            msg: dict[str, object] = {"role": turn.role, "content": turn.content}
            if turn.role == "tool" and turn.tool_call_id:
                msg["tool_call_id"] = turn.tool_call_id
            messages.append(msg)
        return messages

    def clear(self) -> None:
        self._turns.clear()

    def _trim(self) -> None:
        while len(self._turns) > MAX_TURNS * 2 + 1:
            self._turns.pop(0)
