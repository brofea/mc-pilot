"""Bounded agent state machine with tool-call loop."""

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

MAX_TOOL_TURNS = 4


type ToolExecutor = Callable[[str, dict[str, Any]], Awaitable[str]]


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

    def __init__(
        self,
        client: DeepSeekClient,
        memory: ConversationMemory,
        tool_executor: ToolExecutor,
        exported_tools: list[ToolMessage],
    ) -> None:
        self._client = client
        self._memory = memory
        self._tool_executor = tool_executor
        self._exported_tools = exported_tools
        self._traces = []
        self._step = 0
        self._state = AgentState.received
        self._stop_reason = None

    async def run(self, user_message: str) -> AgentResponse:
        self._memory.add_user(user_message)
        self._add_trace(AgentState.received, "user_message_received")
        self._state = AgentState.received

        if self._memory.is_over_budget:
            self._stop_reason = "每日 token 预算已用尽"
            self._add_trace(AgentState.stopped, "budget_exceeded")
            return self._respond(
                "每日 token 配额已用尽。明天会自动重置。",
                AgentState.stopped,
            )

        try:
            return await self._decide()
        except Exception as exc:
            logger.error("Agent loop failed", extra={"error": str(exc)})
            self._add_trace(AgentState.failed, "unhandled_error", error_type=type(exc).__name__)
            return self._respond("内部错误，请重试。", AgentState.failed)

    async def _decide(self) -> AgentResponse:
        self._state = AgentState.deciding
        self._add_trace(AgentState.deciding, "model_inference_started")

        tool_schemas = DeepSeekClient.build_tool_schema(self._exported_tools)
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
        return self._respond(answer, AgentState.answered)

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        self._state = AgentState.tool_running
        self._add_trace(
            AgentState.tool_running,
            "tool_invoked",
            tool_name=tool_call.name,
            tool_args_summary=json.dumps(tool_call.arguments, ensure_ascii=False)[:200],
        )

        if tool_call.name not in TOOL_WHITELIST:
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=False,
                error=f"未知工具: {tool_call.name}",
            )

        try:
            content = await self._tool_executor(tool_call.name, tool_call.arguments)
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=True,
                content=content,
            )
        except Exception as exc:
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                success=False,
                error=str(exc),
            )

    async def _handle_observation(self, results: list[ToolResult]) -> AgentResponse:
        self._step += 1

        # Add tool results to memory
        for result in results:
            self._memory.add_tool_result(result)

        # Cap at max tool turns
        if self._step >= MAX_TOOL_TURNS:
            self._stop_reason = f"达到最大工具轮数 ({MAX_TOOL_TURNS})"
            self._add_trace(AgentState.stopped, "max_turns_reached")
            return self._respond(
                "已达到最大工具调用次数。基于已有信息给出回答。",
                AgentState.stopped,
            )

        self._add_trace(AgentState.observing, "tool_result_observed")
        return await self._decide()

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
