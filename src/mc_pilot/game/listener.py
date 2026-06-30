"""Game log listener: tail latest.log, detect player, parse deaths, emit advice."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from mc_pilot.agent.client import DeepSeekClient
from mc_pilot.game.death_parser import parse_death
from mc_pilot.game.detector import (
    extract_player_from_log,
    extract_version_from_log,
)
from mc_pilot.game.models import DeathAdvice, DeathEvent, GameConnectionState, GameState
from mc_pilot.game.tailer import LogTailer

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 1.0
MAX_DEATH_TOKENS = 200
DEATH_SYSTEM_PROMPT = (
    "你是 Minecraft 游戏助手。玩家刚刚死亡，请用 2-5 句简短的话给出建议。"
    "不要长篇大论，不要安慰过度，直接给出有用的生存提示。使用中文回答。"
)


class GameLogListener:
    """Poll-based log listener that tracks game state and emits death advice."""

    _tailer: LogTailer
    _state: GameState
    _known_events: set[str]
    _death_queue: asyncio.Queue[DeathEvent]
    _on_advice: Any
    _deepseek: DeepSeekClient | None
    _running: bool

    def __init__(
        self,
        deepseek_client: DeepSeekClient | None = None,
        on_advice: Any = None,
    ) -> None:
        self._tailer = LogTailer()
        self._state = GameState()
        self._known_events = set()
        self._death_queue = asyncio.Queue()
        self._on_advice = on_advice
        self._deepseek = deepseek_client
        self._running = False

    @property
    def state(self) -> GameState:
        return self._state

    def set_log_path(self, path: str) -> None:
        from pathlib import Path

        log_path = Path(path)
        if not log_path.exists():
            return
        self._tailer.set_path(log_path)
        self._state.log_path = str(log_path)
        self._scan_initial()

    def set_deepseek(self, client: DeepSeekClient) -> None:
        self._deepseek = client

    async def start(self) -> None:
        self._running = True
        while self._running:
            try:
                lines = self._tailer.poll()
                if lines:
                    self._process_lines(lines)
                while not self._death_queue.empty():
                    event = self._death_queue.get_nowait()
                    await self._generate_advice(event)
            except Exception as exc:
                logger.error("Listener loop error", extra={"error": str(exc)})
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    def stop(self) -> None:
        self._running = False

    def _scan_initial(self) -> None:
        recent = self._tailer.read_tail(max_lines=200)
        version = extract_version_from_log(recent)
        player = extract_player_from_log(recent)

        if version:
            self._state.version_id = version
        if player:
            self._state.player_name = player
            self._state.state = GameConnectionState.connected
            self._state.detected_at = datetime.now(UTC)

        logger.info(
            "Initial scan complete",
            extra={
                "version": self._state.version_id,
                "player": self._state.player_name,
                "state": self._state.state,
            },
        )

    def _process_lines(self, lines: list[str]) -> None:
        self._state.last_activity = datetime.now(UTC)
        player = self._state.player_name

        for line in lines:
            if "joined the game" in line.lower() or "joined the world" in line.lower():
                detected = extract_player_from_log([line])
                if detected:
                    self._state.player_name = detected
                    self._state.state = GameConnectionState.connected
                    logger.info("Player detected", extra={"player": detected})

            if not player:
                continue

            event = parse_death(line, player, timestamp=datetime.now(UTC))
            if event is None:
                continue
            if event.event_id in self._known_events:
                continue

            self._known_events.add(event.event_id)
            self._state.death_count += 1
            logger.info(
                "Death event detected",
                extra={
                    "player": event.player_name,
                    "category": event.category,
                    "source": event.source,
                },
            )
            self._death_queue.put_nowait(event)

    async def _generate_advice(self, event: DeathEvent) -> None:
        if not self._deepseek:
            return

        try:
            response = await self._deepseek.chat(
                messages=[
                    {"role": "system", "content": DEATH_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"玩家 {event.player_name} 死亡原因: {event.raw_message}\n"
                            f"死亡类别: {event.category}"
                        ),
                    },
                ],
            )
            content = response.choices[0].message.get("content", "") if response.choices else ""
            advice = DeathAdvice(
                event=event,
                advice=content.strip(),
                generated_at=datetime.now(UTC),
                tokens_used=response.usage.get("total_tokens", 0),
            )
            if self._on_advice:
                if asyncio.iscoroutinefunction(self._on_advice):
                    await self._on_advice(advice)
                else:
                    self._on_advice(advice)
        except Exception as exc:
            logger.error("Failed to generate death advice", extra={"error": str(exc)})
