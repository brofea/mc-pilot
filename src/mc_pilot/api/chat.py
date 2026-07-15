"""Chat and /pilot command HTTP routes with SSE streaming."""

from __future__ import annotations

import json
import logging
import math
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from mc_pilot.agent.limits import MAX_USER_MESSAGE_CHARS, USER_MESSAGE_TOO_LONG_RESPONSE
from mc_pilot.agent.service import AgentService
from mc_pilot.storage.sqlite import ConversationStore

logger = logging.getLogger(__name__)
CHAT_REQUESTS_PER_MINUTE = 20
CHAT_RATE_WINDOW_SECONDS = 60.0


class ChatRequest(BaseModel):
    message: str
    conversation_id: str = ""


class ChatRateLimiter:
    """Small in-memory sliding-window limiter for local chat endpoints."""

    def __init__(
        self,
        *,
        maximum_requests: int = CHAT_REQUESTS_PER_MINUTE,
        window_seconds: float = CHAT_RATE_WINDOW_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._maximum_requests = maximum_requests
        self._window_seconds = window_seconds
        self._clock = clock
        self._requests: dict[str, deque[float]] = {}

    def retry_after_seconds(self, client_key: str) -> int | None:
        """Record one request and return a retry delay when its window is full."""

        now = self._clock()
        self._discard_expired(now)
        timestamps = self._requests.setdefault(client_key, deque())
        if len(timestamps) >= self._maximum_requests:
            return max(1, math.ceil(self._window_seconds - (now - timestamps[0])))
        timestamps.append(now)
        return None

    def _discard_expired(self, now: float) -> None:
        expired_keys: list[str] = []
        for key, timestamps in self._requests.items():
            while timestamps and now - timestamps[0] >= self._window_seconds:
                timestamps.popleft()
            if not timestamps:
                expired_keys.append(key)
        for key in expired_keys:
            del self._requests[key]


def create_chat_router(
    agent_service: AgentService,
    store: ConversationStore | None = None,
    recipe_service: Any = None,
    wiki_service: Any = None,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["chat"])
    rate_limiter = ChatRateLimiter()

    def validate_chat_request(body: ChatRequest, request: Request) -> None:
        """Reject oversized or bursty requests before they consume model budget."""

        if not body.message.strip():
            raise HTTPException(status_code=400, detail="消息不能为空")
        if len(body.message) > MAX_USER_MESSAGE_CHARS:
            raise HTTPException(status_code=413, detail=USER_MESSAGE_TOO_LONG_RESPONSE)
        client_key = request.client.host if request.client else "unknown"
        retry_after = rate_limiter.retry_after_seconds(client_key)
        if retry_after is not None:
            raise HTTPException(
                status_code=429,
                detail="请求过于频繁，请稍后再试。",
                headers={"Retry-After": str(retry_after)},
            )

    @router.post("/chat")
    async def chat(body: ChatRequest, request: Request) -> dict[str, object]:
        validate_chat_request(body, request)
        try:
            result = await agent_service.handle_pilot(body.message)
        except Exception as exc:
            logger.error("Chat failed", extra={"error": str(exc)})
            raise HTTPException(status_code=500, detail="内部错误") from exc

        if store and body.conversation_id:
            store.add_message(body.conversation_id, "user", body.message)
            store.add_message(body.conversation_id, "assistant", result.answer)
            conv = store.get_conversation(body.conversation_id)
            if conv and str(conv.get("title")) == "新对话" and body.message:
                title = body.message[:50]
                store.update_title(body.conversation_id, title)

        return {
            "state": result.state,
            "answer": result.answer,
            "stop_reason": result.stop_reason,
            "tokens_used": agent_service.memory.daily_tokens,
            "tokens_limit": agent_service.memory.daily_limit,
            "turns_used": len(agent_service.memory._turns),
        }

    @router.post("/chat/stream")
    async def chat_stream(body: ChatRequest, request: Request) -> StreamingResponse:
        validate_chat_request(body, request)

        user_message = body.message

        # Load conversation history from DB if a conversation_id is provided
        history: list[dict[str, str]] | None = None
        if store and body.conversation_id:
            msgs = store.get_messages(body.conversation_id)
            history = [
                {"role": str(m["role"]), "content": str(m["content"])}
                for m in msgs
            ]

        async def generate():  # type: ignore[no-untyped-def]
            full_answer = ""
            try:
                async for event in agent_service.handle_pilot_stream(
                    user_message, history
                ):
                    full_answer = event.get("answer", full_answer)
                    yield (
                        "data: "
                        + json.dumps(event, ensure_ascii=False)
                        + "\n\n"
                    )

                if store and body.conversation_id:
                    store.add_message(body.conversation_id, "user", user_message)
                    if full_answer:
                        store.add_message(body.conversation_id, "assistant", full_answer)
                    conv = store.get_conversation(body.conversation_id)
                    if conv and str(conv.get("title")) == "新对话" and user_message:
                        title = user_message[:50]
                        store.update_title(body.conversation_id, title)

                yield "data: [DONE]\n\n"
            except Exception as exc:
                logger.error("Chat stream failed", extra={"error": str(exc)})
                err_payload = json.dumps(
                    {"type": "error", "message": str(exc)},
                    ensure_ascii=False,
                )
                yield f"data: {err_payload}\n\n"

        return StreamingResponse(
            generate(),  # type: ignore[no-untyped-call]
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @router.get("/agent-status")
    async def agent_status(request: Request) -> dict[str, object]:
        return {"configured": agent_service.is_configured()}

    if store:
        @router.get("/conversations")
        async def list_conversations(request: Request) -> list[dict[str, object]]:
            return store.list_conversations()

        @router.post("/conversations")
        async def create_conversation(request: Request) -> dict[str, object]:
            return store.create_conversation()

        @router.get("/conversations/{conv_id}")
        async def get_conversation(conv_id: str, request: Request) -> dict[str, object]:
            conv = store.get_conversation(conv_id)
            if conv is None:
                raise HTTPException(status_code=404, detail="对话不存在")
            return conv

        @router.delete("/conversations/{conv_id}")
        async def delete_conversation(conv_id: str, request: Request) -> dict[str, object]:
            ok = store.delete_conversation(conv_id)
            if not ok:
                raise HTTPException(status_code=404, detail="对话不存在")
            return {"deleted": True}

        @router.patch("/conversations/{conv_id}")
        async def update_conversation_title(
            conv_id: str, body: dict[str, object], request: Request
        ) -> dict[str, object]:
            title = str(body.get("title", ""))
            if not title:
                raise HTTPException(status_code=400, detail="标题不能为空")
            ok = store.update_title(conv_id, title)
            if not ok:
                raise HTTPException(status_code=404, detail="对话不存在")
            return {"updated": True, "title": title}

    @router.get("/recipes-health")
    async def recipes_health(request: Request) -> dict[str, object]:
        if recipe_service and hasattr(recipe_service, "get_stats"):
            stats = recipe_service.get_stats()
            return {
                "available": bool(stats.get("available")),
                "count": stats.get("recipe_count", 0),
            }
        return {"available": False, "count": 0}

    @router.get("/rag-health")
    async def rag_health(request: Request) -> dict[str, object]:
        if wiki_service and hasattr(wiki_service, "index_stats"):
            stats = wiki_service.index_stats()
            exists = bool(stats.get("index_exists"))
            return {"available": exists, "count": stats.get("chunk_count", 0)}
        return {"available": False, "count": 0}

    return router
