"""Game state HTTP and WebSocket endpoints."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from mc_pilot.game.models import DeathAdvice
from mc_pilot.game.service import GameStateService

logger = logging.getLogger(__name__)


def create_game_router(game_service: GameStateService) -> APIRouter:
    router = APIRouter(tags=["game"])

    @router.get("/api/game-state")
    async def game_state(request: Request) -> dict[str, object]:
        state = game_service.state
        return {
            "state": state.state,
            "version_id": state.version_id,
            "player_name": state.player_name,
            "log_path": state.log_path,
            "death_count": state.death_count,
        }

    @router.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        state = game_service.state
        state.web_socket_clients += 1

        async def on_advice(advice: DeathAdvice) -> None:
            with contextlib.suppress(Exception):
                await websocket.send_json({
                    "type": "death_advice",
                    "player_name": advice.event.player_name,
                    "category": advice.event.category,
                    "advice": advice.advice,
                })

        game_service.add_advice_callback(on_advice)

        try:
            while True:
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                except TimeoutError:
                    state = game_service.state
                    await websocket.send_json({
                        "type": "state",
                        "state": state.state,
                        "version_id": state.version_id,
                        "player_name": state.player_name,
                        "death_count": state.death_count,
                    })
                    continue

                if data == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            state.web_socket_clients = max(0, state.web_socket_clients - 1)
        except Exception:
            state.web_socket_clients = max(0, state.web_socket_clients - 1)

    return router
