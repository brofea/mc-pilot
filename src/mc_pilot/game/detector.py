"""macOS process detection and log path discovery."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_DIR = Path.home() / "Library" / "Application Support" / "minecraft"
DEFAULT_LOG_RELPATH = Path("logs") / "latest.log"


def find_minecraft_log() -> Path | None:
    """Try to locate the Minecraft latest.log on macOS."""
    candidate = DEFAULT_DIR / DEFAULT_LOG_RELPATH
    if candidate.exists():
        return candidate
    return None


def detect_game_process() -> dict[str, str] | None:
    """Look for a local Minecraft Java process on macOS."""
    try:
        result = subprocess.run(
            ["pgrep", "-fl", "minecraft"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None

    for line in result.stdout.strip().split("\n"):
        if "java" in line.lower() and "minecraft" in line.lower():
            return {
                "pid": line.split()[0],
                "command": " ".join(line.split()[1:]),
            }
    return None


def extract_version_from_log(lines: list[str]) -> str | None:
    """Scan startup log lines for the Minecraft version identifier."""
    for line in lines:
        if "Minecraft " in line:
            parts = line.split("Minecraft ", 1)
            if len(parts) > 1:
                version = parts[1].split()[0].strip()
                if version:
                    return version
    return None


def extract_player_from_log(lines: list[str]) -> str | None:
    """Scan log lines for the local player name."""
    for line in lines:
        marker = "Setting user: "
        if marker in line:
            player = line.split(marker, 1)[1].strip().split()[0]
            if player:
                return player
    for line in lines:
        lowered = line.lower()
        if ("joined the game" in lowered or "joined the world" in lowered) and "]: " in line:
            msg_part = line.split("]: ", 1)[1] if "]: " in line else line
            player = msg_part.split(" ")[0].strip()
            if player and player not in ("<", "[", "Server"):
                return player
    for line in lines:
        lowered = line.lower()
        if "logged in with entity id" in lowered:
            for segment in line.split():
                if "[local:" in segment or "[local:E:" in segment:
                    player = segment.split("[")[0].strip()
                    if player and player.lower() not in {"server", "null", "unknown"}:
                        return player
    return None
