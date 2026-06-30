"""Chat and /pilot command HTTP routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from mc_pilot.agent.service import AgentService

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


def create_chat_router(agent_service: AgentService) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["chat"])

    @router.post("/chat")
    async def chat(body: ChatRequest, request: Request) -> dict[str, object]:
        if not body.message.strip():
            raise HTTPException(status_code=400, detail="消息不能为空")
        try:
            result = await agent_service.handle_pilot(body.message)
        except Exception as exc:
            logger.error("Chat failed", extra={"error": str(exc)})
            raise HTTPException(status_code=500, detail="内部错误") from exc
        return {
            "state": result.state,
            "answer": result.answer,
            "stop_reason": result.stop_reason,
        }

    @router.get("/api/agent-status")
    async def agent_status(request: Request) -> dict[str, object]:
        return {"configured": agent_service.is_configured()}

    return router
