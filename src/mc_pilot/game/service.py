"""Game state service: manages log listener lifecycle and exposes state."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from mc_pilot.game.detector import find_minecraft_log
from mc_pilot.game.listener import GameLogListener
from mc_pilot.game.models import DeathAdvice, GameState

logger = logging.getLogger(__name__)


class GameStateService:
    """Owns the log listener and provides a unified state interface."""

    _listener: GameLogListener
    _task: asyncio.Task[object] | None
    _advice_callbacks: list[Callable[..., Any]]

    def __init__(self, listener: GameLogListener | None = None) -> None:
        self._listener = listener or GameLogListener(on_advice=self._on_death_advice)
        self._task = None
        self._advice_callbacks = []

    @property
    def state(self) -> GameState:
        return self._listener.state

    def add_advice_callback(self, callback: Callable[..., Any]) -> None:
        self._advice_callbacks.append(callback)

    async def _on_death_advice(self, advice: DeathAdvice) -> None:
        for cb in self._advice_callbacks:
            if asyncio.iscoroutinefunction(cb):
                await cb(advice)
            else:
                cb(advice)

    async def start(self, log_path: str | None = None) -> None:
        if log_path:
            self._listener.set_log_path(log_path)
        elif not self.state.log_path:
            auto_path = find_minecraft_log()
            if auto_path:
                self._listener.set_log_path(str(auto_path))

        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._listener.start())

    def stop(self) -> None:
        self._listener.stop()
        if self._task and not self._task.done():
            self._task.cancel()

    def set_manual_path(self, path: str) -> GameState:
        self._listener.set_log_path(path)
        return self.state
