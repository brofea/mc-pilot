"""Bilingual (zh_cn / en_us) Minecraft death message parser."""

from __future__ import annotations

import logging
import re
from datetime import datetime

from mc_pilot.game.models import DeathCategory, DeathEvent

logger = logging.getLogger(__name__)

# ── English death patterns ─────────────────────────────────────────────

_EN_PATTERNS: list[tuple[DeathCategory, str]] = [
    (DeathCategory.fall, r"^(\S+) fell from a high place"),
    (DeathCategory.fall, r"^(\S+) hit the ground too hard"),
    (DeathCategory.fall, r"^(\S+) fell off a ladder"),
    (DeathCategory.fall, r"^(\S+) fell off some vines"),
    (DeathCategory.fall, r"^(\S+) fell off some weeping vines"),
    (DeathCategory.fall, r"^(\S+) fell off some twisting vines"),
    (DeathCategory.fall, r"^(\S+) fell off scaffolding"),
    (DeathCategory.fall, r"^(\S+) fell while climbing"),
    (DeathCategory.fall, r"^(\S+) was doomed to fall"),
    (DeathCategory.fall, r"^(\S+) was shot by a skull"),
    (DeathCategory.fire, r"^(\S+) went up in flames"),
    (DeathCategory.fire, r"^(\S+) burned to death"),
    (DeathCategory.fire, r"^(\S+) was burnt to a crisp"),
    (DeathCategory.lava, r"^(\S+) tried to swim in lava"),
    (DeathCategory.drowning, r"^(\S+) drowned"),
    (DeathCategory.suffocation, r"^(\S+) suffocated in a wall"),
    (DeathCategory.explosion, r"^(\S+) blew up"),
    (DeathCategory.explosion, r"^(\S+) was blown up by"),
    (DeathCategory.magic, r"^(\S+) was killed by magic"),
    (DeathCategory.magic, r"^(\S+) was killed by .+ using magic"),
    (DeathCategory.projectile, r"^(\S+) was shot by"),
    (DeathCategory.projectile, r"^(\S+) was fireballed by"),
    (DeathCategory.void, r"^(\S+) fell out of the world"),
    (DeathCategory.void, r"^(\S+) didn't want to live in the same world as"),
    (DeathCategory.starvation, r"^(\S+) starved to death"),
    (DeathCategory.cactus, r"^(\S+) was pricked to death"),
    (DeathCategory.cactus, r"^(\S+) walked into a cactus"),
    (DeathCategory.lightning, r"^(\S+) was struck by lightning"),
    (DeathCategory.freeze, r"^(\S+) froze to death"),
    (DeathCategory.stalagmite, r"^(\S+) was skewered by a falling stalactite"),
    (DeathCategory.stalagmite, r"^(\S+) was impaled on a stalagmite"),
    (DeathCategory.fire, r"^(\S+) was roasted in dragon's breath"),
    (DeathCategory.fall, r"^(\S+) experienced kinetic energy"),
    (DeathCategory.mob, r"^(\S+) was slain by"),
    (DeathCategory.mob, r"^(\S+) was killed by"),
    (DeathCategory.mob, r"^(\S+) was squished too much"),
]

# ── Chinese death patterns ─────────────────────────────────────────────

_ZH_PATTERNS: list[tuple[DeathCategory, str]] = [
    (DeathCategory.fall, r"^(\S+)从高处摔了下来"),
    (DeathCategory.fall, r"^(\S+)落地过猛"),
    (DeathCategory.fall, r"^(\S+)从梯子上摔了下来"),
    (DeathCategory.fall, r"^(\S+)从藤蔓上摔了下来"),
    (DeathCategory.fall, r"^(\S+)从垂泪藤上摔了下来"),
    (DeathCategory.fall, r"^(\S+)从缠怨藤上摔了下来"),
    (DeathCategory.fall, r"^(\S+)从脚手架摔了下来"),
    (DeathCategory.fall, r"^(\S+)在攀爬时摔了下来"),
    (DeathCategory.fire, r"^(\S+)在火焰中冉冉升起"),
    (DeathCategory.fire, r"^(\S+)烧死了"),
    (DeathCategory.fire, r"^(\S+)被烧成了灰烬"),
    (DeathCategory.lava, r"^(\S+)试图在熔岩里游泳"),
    (DeathCategory.drowning, r"^(\S+)淹死了"),
    (DeathCategory.suffocation, r"^(\S+)在墙里窒息了"),
    (DeathCategory.explosion, r"^(\S+)爆炸了"),
    (DeathCategory.explosion, r"^(\S+)被炸死了"),
    (DeathCategory.magic, r"^(\S+)被魔法杀死了"),
    (DeathCategory.projectile, r"^(\S+)被射杀了"),
    (DeathCategory.projectile, r"^(\S+)被火球烧死了"),
    (DeathCategory.void, r"^(\S+)掉出了这个世界"),
    (DeathCategory.void, r"^(\S+)不想和\S+活在同一世界"),
    (DeathCategory.starvation, r"^(\S+)饿死了"),
    (DeathCategory.cactus, r"^(\S+)被仙人掌戳死了"),
    (DeathCategory.cactus, r"^(\S+)在试图逃离\S+时被仙人掌戳死了"),
    (DeathCategory.lightning, r"^(\S+)被闪电击中了"),
    (DeathCategory.freeze, r"^(\S+)冻死了"),
    (DeathCategory.stalagmite, r"^(\S+)被坠落的钟乳石刺穿了"),
    (DeathCategory.stalagmite, r"^(\S+)被石笋刺穿了"),
    (DeathCategory.fire, r"^(\S+)被龙息烤熟了"),
    (DeathCategory.mob, r"^(\S+)被\S+杀死了"),
    (DeathCategory.fall, r"^(\S+)感受到了动能"),
]


def _extract_message(line: str) -> str | None:
    """Extract death message portion from a log line."""
    markers = [
        "[Server thread/INFO]: ",
        "[Server thread/INFO] [",
        "[Render thread/INFO]: ",
        ": [Server thread/INFO]: ",
    ]
    for marker in markers:
        if marker in line:
            return line.split(marker, 1)[1].strip()
    if "]: " in line:
        return line.split("]: ", 1)[1].strip()
    return line.strip()


def parse_death(
    line: str, player_name: str, timestamp: datetime | None = None
) -> DeathEvent | None:
    """Try to parse a death message from a log line."""
    msg = _extract_message(line)
    if not msg:
        return None

    for category, pattern in _EN_PATTERNS:
        m = re.match(pattern, msg)
        if m:
            dead_player = m.group(1)
            if dead_player != player_name:
                continue
            return DeathEvent(
                player_name=player_name,
                category=category,
                raw_message=msg,
                timestamp=timestamp,
                source="en_us",
                confidence=0.95,
                event_id=DeathEvent.build_event_id(player_name, line),
            )

    for category, pattern in _ZH_PATTERNS:
        m = re.match(pattern, msg)
        if m:
            dead_player = m.group(1)
            if dead_player != player_name:
                continue
            return DeathEvent(
                player_name=player_name,
                category=category,
                raw_message=msg,
                timestamp=timestamp,
                source="zh_cn",
                confidence=0.95,
                event_id=DeathEvent.build_event_id(player_name, line),
            )

    if player_name in msg and any(
        kw in msg.lower()
        for kw in ("died", "killed", "slain", "fell", "burn", "drown", "froze", "starved", "died")
    ):
        return DeathEvent(
            player_name=player_name,
            category=DeathCategory.unknown,
            raw_message=msg,
            timestamp=timestamp,
            source="unknown",
            confidence=0.3,
            event_id=DeathEvent.build_event_id(player_name, line),
        )

    return None
