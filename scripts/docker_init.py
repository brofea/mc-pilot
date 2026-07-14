#!/usr/bin/env python
"""Docker startup: auto-build wiki index on first run, then exec the app."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
import urllib.request

QDRANT_URL = os.environ.get("MC_PILOT_QDRANT_URL", "http://qdrant:6333")
MAX_RETRIES = 60
RETRY_DELAY = 2


def qdrant_ready() -> bool:
    try:
        r = urllib.request.urlopen(f"{QDRANT_URL}/healthz", timeout=2)
        return r.status == 200
    except Exception:
        return False


def wiki_index_exists() -> bool:
    try:
        r = urllib.request.urlopen(
            f"{QDRANT_URL}/collections/mc_wiki_live", timeout=2
        )
        return r.status == 200
    except Exception:
        return False


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[init] %(message)s")

    logging.info("Waiting for Qdrant at %s …", QDRANT_URL)
    for i in range(MAX_RETRIES):
        if qdrant_ready():
            logging.info("Qdrant is ready")
            break
        if i % 5 == 0:
            logging.info("Qdrant not ready yet, retrying…")
        time.sleep(RETRY_DELAY)
    else:
        logging.warning("Qdrant did not become ready — starting app without wiki")

    if wiki_index_exists():
        logging.info("Wiki index already exists, skipping build")
    else:
        logging.info("Wiki index not found — building (first run, may take minutes) …")
        try:
            subprocess.run(
                [sys.executable, "scripts/build_wiki.py"],
                check=True,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
            logging.info("Wiki index built successfully")
        except subprocess.CalledProcessError as exc:
            logging.error("Wiki build failed: %s", exc)
            logging.warning("App will start without Wiki index")

    # Exec the CMD
    cmd = sys.argv[1:] if len(sys.argv) > 1 else sys.argv
    logging.info("Starting app: %s", " ".join(cmd))
    os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    main()
