"""Game state service: manages log listener lifecycle and exposes state."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mc_pilot.agent.client import DeepSeekClient
from mc_pilot.game.detector import find_minecraft_log
from mc_pilot.game.listener import GameLogListener
from mc_pilot.game.models import DeathAdvice, GameState

logger = logging.getLogger(__name__)


class GameStateService:
    """Owns the log listener and provides a unified state interface."""

    _listener: GameLogListener
    _task: asyncio.Task[object] | None
    _advice_callbacks: list[Callable[..., Any]]

    def __init__(
        self,
        listener: GameLogListener | None = None,
        *,
        deepseek_client: DeepSeekClient | None = None,
        configured_log_path: str = "",
    ) -> None:
        self._listener = listener or GameLogListener(
            deepseek_client=deepseek_client,
            on_advice=self._on_death_advice,
        )
        self._task = None
        self._advice_callbacks = []
        self._configured_log_path = configured_log_path

    @property
    def state(self) -> GameState:
        return self._listener.state

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def advice_enabled(self) -> bool:
        return self._listener.advice_enabled

    @property
    def advice_subscriber_count(self) -> int:
        return len(self._advice_callbacks)

    def add_advice_callback(self, callback: Callable[..., Any]) -> None:
        self._advice_callbacks.append(callback)

    def remove_advice_callback(self, callback: Callable[..., Any]) -> None:
        """Stop delivering advice to a disconnected client."""
        with contextlib.suppress(ValueError):
            self._advice_callbacks.remove(callback)

    async def _on_death_advice(self, advice: DeathAdvice) -> None:
        for cb in self._advice_callbacks:
            if asyncio.iscoroutinefunction(cb):
                await cb(advice)
            else:
                cb(advice)

    async def start(self, log_path: str | None = None) -> None:
        selected_path = log_path or self._configured_log_path
        if selected_path and Path(selected_path).is_file():
            self._listener.set_log_path(selected_path)
        elif not self.state.log_path:
            auto_path = find_minecraft_log()
            if auto_path:
                self._listener.set_log_path(str(auto_path))

        if not self.state.log_path:
            logger.info("game_log_listener_inactive", extra={"reason": "log_not_found"})
            return

        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._listener.start())

    async def stop(self) -> None:
        """Stop and join the listener task without leaking cancellation."""
        self._listener.stop()
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._task = None

    def set_manual_path(self, path: str) -> GameState:
        self._listener.set_log_path(path)
        return self.state
