"""AgentService: high-level entry point for routing /pilot commands."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from mc_pilot.agent.client import DeepSeekClient
from mc_pilot.agent.loop import AgentLoop
from mc_pilot.agent.memory import ConversationMemory
from mc_pilot.agent.models import (
    AgentResponse,
    AgentState,
    ConnectivityResult,
    ToolMessage,
)
from mc_pilot.agent.tools import (
    GET_STATUS_TOOL,
    RECIPE_DIRECT_TOOL,
    RECIPE_QUERY_TOOL,
    WIKI_SEARCH_TOOL,
)

logger = logging.getLogger(__name__)


class AgentService:
    """Owns the agent loop, tool executors, memory, and routing."""

    _deepseek_base_url: str
    _deepseek_api_key: str
    _deepseek_model: str
    _memory: ConversationMemory
    _recipe_service: Any
    _wiki_service: Any

    def __init__(
        self,
        *,
        deepseek_base_url: str,
        deepseek_api_key: str,
        deepseek_model: str = "deepseek-v4-flash",
        recipe_service: Any = None,
        wiki_service: Any = None,
    ) -> None:
        self._deepseek_base_url = deepseek_base_url
        self._deepseek_api_key = deepseek_api_key
        self._deepseek_model = deepseek_model
        self._memory = ConversationMemory()
        self._recipe_service = recipe_service
        self._wiki_service = wiki_service

    def is_configured(self) -> bool:
        return bool(self._deepseek_api_key)

    async def connectivity_test(self) -> ConnectivityResult:
        client = self._build_client()
        try:
            result = await client.connect_test()
            return ConnectivityResult(
                model=result["model"],
                base_url=self._deepseek_base_url,
                success=True,
                latency_ms=result["latency_ms"],
                prompt_tokens=result.get("prompt_tokens", 0),
                completion_tokens=result.get("completion_tokens", 0),
                answer=result.get("answer", ""),
            )
        except Exception as exc:
            return ConnectivityResult(
                model=self._deepseek_model,
                base_url=self._deepseek_base_url,
                success=False,
                latency_ms=0,
                error=str(exc),
            )

    async def handle_pilot(self, message: str) -> AgentResponse:
        stripped = message.removeprefix("/pilot").strip()
        parts = stripped.split(maxsplit=1)
        command = parts[0].lower() if parts else ""

        if command == "wiki":
            return await self._handle_wiki_direct(parts[1] if len(parts) > 1 else "")
        elif command == "recipe":
            return await self._handle_recipe_direct(parts[1] if len(parts) > 1 else "")
        else:
            return await self._run_agent(message)

    async def handle_pilot_stream(
        self, message: str, history: list[dict[str, str]] | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        stripped = message.removeprefix("/pilot").strip()
        parts = stripped.split(maxsplit=1)
        command = parts[0].lower() if parts else ""

        if command in ("wiki", "recipe"):
            result = await self.handle_pilot(message)
            yield {"type": "done", "answer": result.answer, "state": result.state.value}
            return

        memory = self._memory.detach()
        if history:
            memory.load_history(history)
        token_before = memory.daily_tokens

        event_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

        async def on_event(event_type: str, data: dict[str, Any]) -> None:
            await event_queue.put({"type": event_type, **data})

        client = self._build_client()
        loop = AgentLoop(
            client=client,
            memory=memory,
            tool_executor=self._tool_executor,
            exported_tools=self._get_tools(),
            on_event=on_event,
        )

        async def run_agent() -> None:
            try:
                result = await loop.run(message)
                delta = memory.daily_tokens - token_before
                if delta > 0:
                    self._memory.consume_tokens(delta)
                await event_queue.put({
                    "type": "result",
                    "answer": result.answer,
                    "state": result.state.value,
                    "stop_reason": result.stop_reason,
                    "tokens_used": memory.daily_tokens,
                    "tokens_limit": memory.daily_limit,
                })
            except Exception as exc:
                await event_queue.put({"type": "error", "message": str(exc)})
            finally:
                await event_queue.put(None)

        task = asyncio.create_task(run_agent())

        while True:
            event = await event_queue.get()
            if event is None:
                break
            yield event

        await task

    async def _run_agent(self, user_message: str) -> AgentResponse:
        memory = self._memory.detach()
        token_before = memory.daily_tokens
        client = self._build_client()
        loop = AgentLoop(
            client=client,
            memory=memory,
            tool_executor=self._tool_executor,
            exported_tools=self._get_tools(),
        )
        result = await loop.run(user_message)
        delta = memory.daily_tokens - token_before
        if delta > 0:
            self._memory.consume_tokens(delta)
        return result

    async def _handle_wiki_direct(self, query: str) -> AgentResponse:
        if not self._wiki_service:
            return AgentResponse(state=AgentState.answered, answer="Wiki 服务尚未初始化。")
        result = await self._tool_executor("wiki_search", {"query": query})
        return AgentResponse(state=AgentState.answered, answer=result)

    async def _handle_recipe_direct(self, item_id: str) -> AgentResponse:
        if not self._recipe_service:
            return AgentResponse(state=AgentState.answered, answer="配方服务尚未初始化。")
        result = await self._tool_executor("recipe_query", {"item_id": item_id})
        return AgentResponse(state=AgentState.answered, answer=result)

    def _build_client(self) -> DeepSeekClient:
        return DeepSeekClient(
            base_url=self._deepseek_base_url,
            api_key=self._deepseek_api_key,
            model=self._deepseek_model,
        )

    async def _tool_executor(self, name: str, arguments: dict[str, object]) -> str:
        if name == "wiki_search":
            query = str(arguments.get("query", ""))
            top_k = int(str(arguments.get("top_k", 8)))
            return await self._execute_wiki_search(query, top_k)
        elif name == "recipe_query":
            item_id = str(arguments.get("item_id", ""))
            quantity = int(str(arguments.get("quantity", 1)))
            max_depth_raw = arguments.get("max_depth")
            md = int(str(max_depth_raw)) if max_depth_raw is not None else None
            return await self._execute_recipe_query(item_id, quantity, md)
        elif name == "recipe_direct":
            item_id = str(arguments.get("item_id", ""))
            return await self._execute_recipe_direct(item_id)
        elif name == "get_status":
            return self._handle_status()
        else:
            raise ValueError(f"未知工具: {name}")

    async def _execute_wiki_search(self, query: str, top_k: int) -> str:
        if not self._wiki_service:
            return "Wiki 知识库尚未构建。"
        result = await asyncio.to_thread(
            self._wiki_service.retrieve, query, top_k=min(top_k, 15)
        )
        if result.insufficient_evidence:
            return "知识库未找到足够依据。"
        return str(result.verified_answer)

    async def _execute_recipe_query(
        self, item_id: str, quantity: int, max_depth: int | None
    ) -> str:
        if not self._recipe_service:
            return "配方服务尚未初始化。"
        result = await asyncio.to_thread(
            self._recipe_service.query_tree,
            item_id=item_id,
            quantity=quantity,
            max_depth=max_depth,
        )
        return self._format_recipe_tree(result)

    async def _execute_recipe_direct(self, item_id: str) -> str:
        if not self._recipe_service:
            return "配方服务尚未初始化。"
        result = await asyncio.to_thread(
            self._recipe_service.query_direct, item_id=item_id
        )
        recipes = result.recipes
        if not recipes:
            return f"未找到 {item_id} 的合成配方。"
        parts = [f"{item_id} 的合成配方 ({len(recipes)} 种):"]
        for r in recipes:
            parts.append(f"  - {r.recipe_id} ({r.recipe_type}): {r.result_count}个")
        return "\n".join(parts)

    def _handle_status(self) -> str:
        tokens = self._memory.daily_tokens
        limit = self._memory.daily_limit
        pct = round(tokens / limit * 100, 1) if limit > 0 else 0
        return (
            f"**Minecraft Pilot 运行状态**\n\n"
            f"- 模型: {self._deepseek_model}\n"
            f"- Token 用量: {tokens:,} / {limit:,} ({pct}%)\n"
            f"- 状态: {'已达上限' if self._memory.is_over_budget else '正常运行'}\n"
        )

    def _get_tools(self) -> list[ToolMessage]:
        return [
            WIKI_SEARCH_TOOL,
            RECIPE_QUERY_TOOL,
            RECIPE_DIRECT_TOOL,
            GET_STATUS_TOOL,
        ]

    @property
    def memory(self) -> ConversationMemory:
        return self._memory

    @staticmethod
    def _format_recipe_tree(tree_result: Any) -> str:
        result = tree_result.model_dump()
        leaf_totals = result.get("leaf_totals", {})
        target_name = result.get(
            "target_display_name", result.get("target_item_id", "")
        )
        target_qty = result.get("target_quantity", 1)
        parts: list[str] = [f"目标: {target_name} x {target_qty}"]
        if leaf_totals:
            str_leaf: dict[str, int] = leaf_totals
            parts.append("需要的基础材料:")
            for item_id, count in str_leaf.items():
                parts.append(f"  - {item_id} x {count}")
        if result.get("truncated"):
            parts.append(f"注意: {result.get('truncation_reason', '配方树被截断')}")
        parts.append(f"总计 {result.get('total_nodes', 0)} 个配方节点")
        return "\n".join(parts)
