"""Bounded agent state machine with tool-call loop and streaming events."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from mc_pilot.agent.client import DeepSeekClient
from mc_pilot.agent.memory import ConversationMemory
from mc_pilot.agent.models import (
    AgentResponse,
    AgentState,
    AgentTurn,
    ToolCall,
    ToolMessage,
    ToolResult,
    TraceEntry,
)
from mc_pilot.agent.tools import TOOL_WHITELIST

logger = logging.getLogger(__name__)

MAX_TOOL_TURNS = 12

type ToolExecutor = Callable[[str, dict[str, Any]], Awaitable[str]]
type EventEmitter = Callable[[str, dict[str, Any]], Awaitable[None]] | None


class AgentLoop:
    """Drives the agent state machine: received → deciding → tool_running → ..."""

    _client: DeepSeekClient
    _memory: ConversationMemory
    _tool_executor: ToolExecutor
    _exported_tools: list[ToolMessage]
    _traces: list[TraceEntry]
    _step: int
    _state: AgentState
    _stop_reason: str | None
    _wiki_search_count: int
    _on_event: EventEmitter

    def __init__(
        self,
        client: DeepSeekClient,
        memory: ConversationMemory,
        tool_executor: ToolExecutor,
        exported_tools: list[ToolMessage],
        on_event: EventEmitter = None,
    ) -> None:
        self._client = client
        self._memory = memory
        self._tool_executor = tool_executor
        self._exported_tools = exported_tools
        self._traces = []
        self._step = 0
        self._state = AgentState.received
        self._stop_reason = None
        self._wiki_search_count = 0
        self._on_event = on_event

    async def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        if self._on_event:
            await self._on_event(event_type, data)

    async def run(self, user_message: str) -> AgentResponse:
        self._memory.strip_tool_context()
        self._memory.add_user(user_message)
        self._add_trace(AgentState.received, "user_message_received")
        self._state = AgentState.received

        if self._memory.is_over_budget:
            self._stop_reason = "每日 token 预算已用尽"
            self._add_trace(AgentState.stopped, "budget_exceeded")
            logger.info("Agent stopped (budget exceeded)")
            return self._respond(
                "每日 token 配额已用尽。明天会自动重置。",
                AgentState.stopped,
            )

        logger.info("Agent loop started")
        await self._emit("status", {"text": "正在分析问题…"})
        try:
            return await self._decide()
        except Exception as exc:
            logger.error("Agent loop failed", extra={"error": str(exc)})
            self._add_trace(AgentState.failed, "unhandled_error", error_type=type(exc).__name__)
            await self._emit("error", {"message": str(exc)})
            return self._respond("内部错误，请重试。", AgentState.failed)

    async def _decide(self) -> AgentResponse:
        self._state = AgentState.deciding
        self._add_trace(AgentState.deciding, "model_inference_started")

        await self._emit("thinking", {"text": "思考中…"})
        schemas = DeepSeekClient.build_tool_schema(self._exported_tools)
        tool_schemas: list[dict[str, Any]] | None = schemas
        if self._wiki_search_count >= 2:
            tool_schemas = None
        chat_start = time.monotonic()

        response = await self._client.chat(
            messages=self._memory.as_messages(),
            tools=tool_schemas,
        )
        elapsed = (time.monotonic() - chat_start) * 1000
        self._memory.consume_tokens(response.usage.get("total_tokens", 0))

        choice = response.choices[0]
        msg = choice.message

        if choice.finish_reason == "tool_calls" and msg.get("tool_calls"):
            tool_calls = self._parse_tool_calls(msg["tool_calls"])
            self._add_trace(
                AgentState.deciding,
                "tool_selected",
                tool_name=",".join(tc.name for tc in tool_calls),
                duration_ms=elapsed,
                token_usage=response.usage,
            )

            # Save assistant message with tool calls to memory
            self._memory._turns.append(
                AgentTurn(
                    role="assistant",
                    content=msg.get("content") or "",
                    tool_calls=tuple(tool_calls),
                )
            )

            results: list[ToolResult] = []
            for tc in tool_calls:
                result = await self._execute_tool(tc)
                results.append(result)

            self._state = AgentState.observing
            return await self._handle_observation(results)

        # Model produced a text answer
        answer = msg.get("content", "")
        self._add_trace(
            AgentState.answered,
            "answer_generated",
            duration_ms=elapsed,
            token_usage=response.usage,
        )
        self._memory.add_assistant(answer)
        await self._emit("done", {"answer": answer})
        return self._respond(answer, AgentState.answered)

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        self._state = AgentState.tool_running
        self._add_trace(
            AgentState.tool_running,
            "tool_invoked",
            tool_name=tool_call.name,
            tool_args_summary=json.dumps(tool_call.arguments, ensure_ascii=False)[:200],
        )

        tool_label = {
            "wiki_search": "搜索 Wiki 知识库",
            "recipe_query": "查询合成配方",
            "recipe_direct": "查询直接配方",
        }.get(tool_call.name, tool_call.name)

        await self._emit("tool_start", {
            "name": tool_call.name,
            "label": tool_label,
            "arguments": tool_call.arguments,
        })

        if tool_call.name not in TOOL_WHITELIST:
            logger.warning("Tool blocked by whitelist", extra={"tool": tool_call.name})
            await self._emit("tool_end", {
                "name": tool_call.name,
                "success": False,
                "summary": f"未知工具: {tool_call.name}",
            })
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=False,
                error=f"未知工具: {tool_call.name}",
            )

        logger.info(
            "Tool executing",
            extra={
                "tool": tool_call.name,
                "tool_args": json.dumps(tool_call.arguments, ensure_ascii=False)[:120],
            },
        )
        try:
            content = await self._tool_executor(tool_call.name, tool_call.arguments)
            logger.info("Tool completed", extra={"tool": tool_call.name})
            if tool_call.name == "wiki_search":
                self._wiki_search_count += 1
                if self._wiki_search_count >= 2:
                    hint = (
                        "[系统提示] 已进行多次 Wiki 搜索，信息充足，"
                        "请立即基于已有结果给出回答。不要再搜索了。"
                    )
                    content += "\n\n" + hint
            await self._emit("tool_end", {
                "name": tool_call.name,
                "success": True,
                "summary": content[:200] + ("…" if len(content) > 200 else ""),
            })
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=True,
                content=content,
            )
        except Exception as exc:
            logger.error("Tool failed", extra={"tool": tool_call.name, "error": str(exc)})
            await self._emit("tool_end", {
                "name": tool_call.name,
                "success": False,
                "summary": str(exc),
            })
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=False,
                error=str(exc),
            )

    async def _handle_observation(self, results: list[ToolResult]) -> AgentResponse:
        self._step += 1

        for result in results:
            self._memory.add_tool_result(result)

        if self._step >= MAX_TOOL_TURNS:
            self._stop_reason = f"达到最大工具轮数 ({MAX_TOOL_TURNS})"
            self._add_trace(AgentState.stopped, "max_turns_reached")
            logger.warning("Agent stopped (max turns)")
            return await self._force_answer()

        self._add_trace(AgentState.observing, "tool_result_observed")
        logger.info("Agent observing tool results", extra={"turn": self._step})
        return await self._decide()

    async def _force_answer(self) -> AgentResponse:
        """Ask the model for a final answer based on all tool results collected so far,
        without offering any more tools."""
        tool_schemas: list[dict[str, Any]] | None = None
        chat_start = time.monotonic()

        response = await self._client.chat(
            messages=self._memory.as_messages(),
            tools=tool_schemas,
        )
        elapsed = (time.monotonic() - chat_start) * 1000
        self._memory.consume_tokens(response.usage.get("total_tokens", 0))

        choice = response.choices[0]
        msg = choice.message
        answer = msg.get("content", "")
        self._add_trace(
            AgentState.answered,
            "answer_generated",
            duration_ms=elapsed,
            token_usage=response.usage,
        )
        self._memory.add_assistant(answer)
        await self._emit("done", {"answer": answer})
        return self._respond(answer, AgentState.answered)

    def _parse_tool_calls(self, raw: list[dict[str, Any]]) -> list[ToolCall]:
        result: list[ToolCall] = []
        for tc in raw:
            func = tc.get("function", {})
            args_str = func.get("arguments", "{}")
            try:
                arguments: dict[str, Any] = json.loads(args_str)
            except json.JSONDecodeError:
                arguments = {}
            result.append(
                ToolCall(
                    id=tc.get("id", ""),
                    name=func.get("name", ""),
                    arguments=arguments,
                )
            )
        return result

    def _respond(self, answer: str, state: AgentState) -> AgentResponse:
        logger.info(
            "Agent response ready",
            extra={"state": state.value, "answer_len": len(answer), "turns": self._step},
        )
        return AgentResponse(
            state=state,
            answer=answer,
            tool_results=(),
            trace=tuple(self._traces),
            stop_reason=self._stop_reason,
        )

    def _add_trace(
        self,
        state: AgentState,
        event: str,
        *,
        tool_name: str | None = None,
        tool_args_summary: str | None = None,
        duration_ms: float | None = None,
        token_usage: dict[str, int] | None = None,
        error_type: str | None = None,
    ) -> None:
        self._traces.append(
            TraceEntry(
                step=self._step,
                state=state,
                event=event,
                tool_name=tool_name,
                tool_args_summary=tool_args_summary,
                duration_ms=duration_ms,
                token_usage=token_usage or {},
                error_type=error_type,
            )
        )
