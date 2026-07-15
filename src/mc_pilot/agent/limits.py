"""Bounded resource limits for conversational Agent requests."""

from __future__ import annotations

DAILY_TOKEN_LIMIT = 750_000
MAX_USER_MESSAGE_CHARS = 12_000
USER_MESSAGE_TOO_LONG_RESPONSE = (
    f"单条消息最多 {MAX_USER_MESSAGE_CHARS:,} 个字符，请分段发送后继续。"
)
