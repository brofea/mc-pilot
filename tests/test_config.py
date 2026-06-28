"""Configuration redaction tests."""

from __future__ import annotations

from mc_pilot.config import Settings


def test_safe_summary_never_returns_secret() -> None:
    settings = Settings(_env_file=None, DEEPSEEK_API_KEY="secret-value")

    summary = settings.safe_summary()

    assert summary["deepseek_configured"] is True
    assert "secret-value" not in repr(summary)
