"""Agent domain models: state machine, tool contracts, trace entries, memory."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentState(StrEnum):
    received = "received"
    deciding = "deciding"
    tool_running = "tool_running"
    observing = "observing"
    answered = "answered"
    stopped = "stopped"
    failed = "failed"


class ToolMessage(BaseModel):
    """MCP-style tool definition passed to the model."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for the tool's arguments


class ToolCall(BaseModel):
    """A tool invocation from the model."""

    model_config = ConfigDict(frozen=True)

    id: str = ""
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result returned from executing a tool."""

    model_config = ConfigDict(frozen=True)

    tool_call_id: str
    name: str
    success: bool
    content: str = ""
    error: str | None = None


class AgentTurn(BaseModel):
    """One round of user–assistant exchange in conversation memory."""

    model_config = ConfigDict(frozen=True)

    role: Literal["user", "assistant", "tool"]
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None


class TraceEntry(BaseModel):
    """A single point-in-time agent event for structured tracing."""

    model_config = ConfigDict(frozen=True)

    step: int
    state: AgentState
    event: str  # e.g. "tool_selected", "answer_generated", "budget_exceeded"
    tool_name: str | None = None
    tool_args_summary: str | None = None
    duration_ms: float | None = None
    token_usage: dict[str, int] = Field(default_factory=dict)
    error_type: str | None = None


class AgentResponse(BaseModel):
    """Final agent reply to the user."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    state: AgentState
    answer: str = ""
    tool_results: tuple[ToolResult, ...] = ()
    trace: tuple[TraceEntry, ...] = ()
    stop_reason: str | None = None


class ConnectivityResult(BaseModel):
    """DeepSeek model connectivity smoke test result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    model: str
    base_url: str
    success: bool
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    answer: str = ""
    error: str | None = None


class SessionMemory(BaseModel):
    """In-memory short-term conversation buffer."""

    model_config = ConfigDict(validate_assignment=True)

    turns: list[AgentTurn] = Field(default_factory=list, max_length=6)
    daily_tokens: int = 0
    daily_limit: int = 500_000
