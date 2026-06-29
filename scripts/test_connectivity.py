#!/usr/bin/env python3
"""DeepSeek model connectivity smoke test."""

from __future__ import annotations

import asyncio
import logging

from mc_pilot.agent.service import AgentService
from mc_pilot.config import get_settings

logger = logging.getLogger(__name__)


async def _main() -> None:
    settings = get_settings()
    api_key = (
        settings.deepseek_api_key.get_secret_value()
        if settings.deepseek_api_key
        else ""
    )
    if not api_key:
        logger.error("DEEPSEEK_API_KEY not configured")
        return

    service = AgentService(
        deepseek_base_url=settings.deepseek_base_url,
        deepseek_api_key=api_key,
        deepseek_model=settings.deepseek_model,
    )

    result = await service.connectivity_test()
    if result.success:
        logger.info(
            "Connectivity OK",
            extra={
                "model": result.model,
                "latency_ms": result.latency_ms,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "answer": result.answer,
            },
        )
    else:
        logger.error("Connectivity failed", extra={"error": result.error})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(_main())
