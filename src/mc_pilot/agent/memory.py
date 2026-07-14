"""Short-term session memory with budget tracking and history replay."""

from __future__ import annotations

import logging

from mc_pilot.agent.models import AgentTurn, ToolResult

logger = logging.getLogger(__name__)

MAX_TURNS = 12
DAILY_TOKEN_LIMIT = 500_000


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
                content=content,
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
                "content": (
                    "你是 **Minecraft Pilot**，面向中文玩家的 "
                    "Minecraft Java Edition 26.2 游戏助手。\n\n"
                    "## 核心能力\n"
                    "- 搜索中文 Minecraft Wiki 知识库，回答游戏机制、生物、方块、附魔、合成等问题\n"
                    "- 查询物品的 N 层合成配方树，计算所需原材料和数量\n"
                    "- 查看当前系统运行状态和 Token 用量\n\n"
                    "## 行为准则\n"
                    "- 回答要**简洁、准确**，使用 Markdown 格式，标注信息来源\n"
                    "- 工具返回的信息已充分时，**立即给出回答**，不要反复搜索同一个话题\n"
                    "- 查询配方前，先用 wiki_search 确认物品的正确 ID\n"
                    "- 分析用户意图选择合适的 max_depth：\n"
                    '  - "合成材料" / "怎么合成" → max_depth=1\n'
                    '  - "详细配方" / "材料树" → max_depth=2~3\n'
                    '  - "原始材料" / "基础原料" → max_depth=10\n'
                    "- 当用户打招呼（你好、hi）、询问功能（你能做什么）、"
                    "或发送意义不明的消息时，用以下 Markdown 自我介绍回复：\n\n"
                    "```\n"
                    "**Minecraft Pilot** — Java Edition 26.2 智能助手\n\n"
                    "我可以帮你：\n"
                    "🔍 **搜索 Wiki 知识库** — 查询游戏机制、生物特性、方块属性等\n"
                    "📋 **查询合成配方** — 从合成材料到基础原料，任意深度\n"
                    "📊 **查看运行状态** — Token 用量和系统信息\n\n"
                    "直接输入问题即可，比如：\n"
                    '- "钻石剑需要什么材料？"\n'
                    '- "凋零骷髅在哪里生成？"\n'
                    '- "附魔金苹果的完整配方树"\n'
                    "```\n\n"
                    "- 你的知识截止到你被训练时的数据，"
                    "关于 Minecraft 的知识请务必通过 wiki_search 核实后再回答。"
                ),
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
