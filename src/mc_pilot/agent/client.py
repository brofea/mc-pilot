"""DeepSeek OpenAI-compatible chat client with tool-call support."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from mc_pilot.agent.models import ToolMessage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatChoice:
    index: int
    message: dict[str, Any]
    finish_reason: str


@dataclass(frozen=True)
class ChatResponse:
    choices: list[ChatChoice]
    usage: dict[str, int]
    model: str


def _normalize_usage(raw_usage: object) -> dict[str, int]:
    """Keep scalar token counters and discard provider-specific nested details."""
    if not isinstance(raw_usage, dict):
        return {}
    return {
        str(key): value
        for key, value in raw_usage.items()
        if isinstance(value, int) and not isinstance(value, bool)
    }


class DeepSeekClient:
    """Thin wrapper over the DeepSeek chat completions endpoint."""

    _base_url: str
    _api_key: str
    _model: str
    _timeout_seconds: float
    _max_tokens: int

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str = "deepseek-v4-flash",
        timeout_seconds: float = 60.0,
        max_tokens: int = 800,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_tokens = max_tokens

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
    ) -> ChatResponse:
        url = f"{self._base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": 0.0,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data: dict[str, Any] = response.json()

        elapsed = (time.monotonic() - start) * 1000
        logger.debug(
            "DeepSeek chat completed",
            extra={
                "model": self._model,
                "duration_ms": round(elapsed, 1),
                "usage": data.get("usage", {}),
            },
        )

        choices = [
            ChatChoice(
                index=c.get("index", 0),
                message=c.get("message", {}),
                finish_reason=c.get("finish_reason", "stop"),
            )
            for c in data.get("choices", [])
        ]
        return ChatResponse(
            choices=choices,
            usage=_normalize_usage(data.get("usage")),
            model=data.get("model", self._model),
        )

    async def connect_test(self) -> dict[str, Any]:
        """Smoke test: does the model respond with a simple completion?"""
        start = time.monotonic()
        result = await self.chat(
            messages=[{"role": "user", "content": "回应：连接成功。仅回答测试通过。"}],
        )
        elapsed = (time.monotonic() - start) * 1000
        return {
            "model": result.model,
            "latency_ms": round(elapsed, 1),
            "prompt_tokens": result.usage.get("prompt_tokens", 0),
            "completion_tokens": result.usage.get("completion_tokens", 0),
            "answer": (
                result.choices[0].message.get("content", "")
                if result.choices
                else ""
            ),
        }

    @staticmethod
    def build_tool_schema(tools: list[ToolMessage]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]
