"""Game state, death event, and listener models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class GameConnectionState(StrEnum):
    disconnected = "disconnected"
    connected = "connected"
    degraded = "degraded"


class DeathCategory(StrEnum):
    fall = "fall"
    mob = "mob"
    fire = "fire"
    lava = "lava"
    drowning = "drowning"
    suffocation = "suffocation"
    explosion = "explosion"
    magic = "magic"
    projectile = "projectile"
    void = "void"
    starvation = "starvation"
    cactus = "cactus"
    lightning = "lightning"
    freeze = "freeze"
    stalagmite = "stalagmite"
    generic = "generic"
    unknown = "unknown"


class DeathEvent(BaseModel):
    """Normalised death event from a log line."""

    model_config = ConfigDict(frozen=True)

    player_name: str
    category: DeathCategory
    raw_message: str
    timestamp: datetime | None = None
    source: str = ""  # zh_cn / en_us
    confidence: float = 1.0
    event_id: str = Field(default="")  # stable dedup key

    @classmethod
    def build_event_id(cls, player_name: str, raw: str, timestamp: datetime | None = None) -> str:
        import hashlib

        key = f"{player_name}|{raw}|{timestamp.isoformat() if timestamp else ''}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]


class GameState(BaseModel):
    """Current game connection snapshot."""

    model_config = ConfigDict(validate_assignment=True)

    state: GameConnectionState = GameConnectionState.disconnected
    log_path: str = ""
    version_id: str = ""
    player_name: str = ""
    detected_at: datetime | None = None
    last_activity: datetime | None = None
    file_offset: int = 0
    rotation_count: int = 0
    truncation_count: int = 0
    death_count: int = 0
    web_socket_clients: int = 0


class DeathAdvice(BaseModel):
    """A single death advice payload for WebSocket / frontend."""

    model_config = ConfigDict(frozen=True)

    event: DeathEvent
    advice: str  # 2-5 sentence suggestion
    generated_at: datetime | None = None
    tokens_used: int = 0
