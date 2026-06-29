"""Mojang version manifest client and verified JAR downloader."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from mc_pilot.recipes.models import VersionDetail, VersionMetadata

logger = logging.getLogger(__name__)

DEFAULT_VERSION_MANIFEST_URL = (
    "https://launchermeta.mojang.com/mc/game/version_manifest.json"
)
DEFAULT_MIRROR_URLS: tuple[str, ...] = ()


@dataclass(frozen=True)
class DownloadResult:
    version_detail: VersionDetail
    file_path: Path
    actual_source: str
    sha1_match: bool
    downloaded_at: datetime
    retries: int = 0


@dataclass
class DownloaderConfig:
    cache_dir: Path = Path("data/recipes/cache")
    timeout_seconds: int = 120
    max_retries: int = 3
    mirror_urls: tuple[str, ...] = DEFAULT_MIRROR_URLS


def _sha1_hex(path: Path, chunk_size: int = 65536) -> str:
    sha = hashlib.sha1()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha.update(chunk)
    return sha.hexdigest()


async def fetch_version_manifest(
    client: httpx.AsyncClient,
    manifest_url: str = DEFAULT_VERSION_MANIFEST_URL,
) -> list[VersionMetadata]:
    """Download the Mojang version manifest and return all release-type entries."""
    logger.info("Fetching version manifest", extra={"url": manifest_url})
    response = await client.get(manifest_url)
    response.raise_for_status()
    data = response.json()

    versions: list[VersionMetadata] = []
    for entry in data.get("versions", []):
        versions.append(
            VersionMetadata(
                version_id=entry["id"],
                release_type=entry["type"],
                manifest_url=entry["url"],
            )
        )
    logger.debug("Fetched version manifest", extra={"count": len(versions)})
    return versions


async def fetch_version_detail(
    client: httpx.AsyncClient,
    version: VersionMetadata,
) -> VersionDetail:
    """Fetch the per-version JSON to retrieve download URL and hash."""
    logger.debug(
        "Fetching version detail",
        extra={"version": version.version_id, "url": version.manifest_url},
    )
    response = await client.get(version.manifest_url)
    response.raise_for_status()
    data = response.json()

    client_info = data["downloads"]["client"]
    return VersionDetail(
        version_id=version.version_id,
        client_url=client_info["url"],
        client_sha1=client_info["sha1"],
        client_size=client_info["size"],
    )


async def download_jar(
    detail: VersionDetail,
    config: DownloaderConfig | None = None,
) -> DownloadResult:
    """Download the client JAR using CDN first, then mirrors. Verify SHA-1."""
    cfg = config or DownloaderConfig()
    cfg.cache_dir.mkdir(parents=True, exist_ok=True)

    urls = [detail.client_url, *cfg.mirror_urls]

    # Check cache first
    cached_path = cfg.cache_dir / f"{detail.version_id}.jar"
    if cached_path.exists():
        actual_hash = _sha1_hex(cached_path)
        if actual_hash == detail.client_sha1:
            logger.info("Using cached JAR", extra={"version": detail.version_id})
            return DownloadResult(
                version_detail=detail,
                file_path=cached_path,
                actual_source="cache",
                sha1_match=True,
                downloaded_at=datetime.now(UTC),
            )
        else:
            logger.warning(
                "Cached JAR hash mismatch, re-downloading",
                extra={
                    "version": detail.version_id,
                    "expected": detail.client_sha1,
                    "actual": actual_hash,
                },
            )
            cached_path.unlink()

    for attempt, url in enumerate(urls, start=1):
        logger.info(
            "Downloading client JAR",
            extra={"version": detail.version_id, "url": url, "attempt": attempt},
        )
        try:
            async with httpx.AsyncClient(
                timeout=cfg.timeout_seconds, follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                content = response.read()
        except httpx.HTTPError as exc:
            logger.warning(
                "Download attempt failed",
                extra={
                    "version": detail.version_id,
                    "url": url,
                    "attempt": attempt,
                    "error": str(exc),
                },
            )
            if attempt <= cfg.max_retries:
                continue
            raise RuntimeError(
                f"Failed to download {detail.version_id} from all sources"
            ) from exc

        actual_hash = hashlib.sha1(content).hexdigest()
        if actual_hash != detail.client_sha1:
            logger.error(
                "SHA-1 mismatch - rejecting download",
                extra={
                    "version": detail.version_id,
                    "source": url,
                    "expected": detail.client_sha1,
                    "actual": actual_hash,
                },
            )
            if attempt <= cfg.max_retries:
                continue
            raise ValueError(
                f"SHA-1 mismatch for {detail.version_id}: "
                f"expected {detail.client_sha1}, got {actual_hash}"
            )

        cached_path.write_bytes(content)
        logger.info(
            "JAR downloaded and verified",
            extra={"version": detail.version_id, "source": url, "attempt": attempt},
        )
        return DownloadResult(
            version_detail=detail,
            file_path=cached_path,
            actual_source=url,
            sha1_match=True,
            downloaded_at=datetime.now(UTC),
            retries=attempt - 1,
        )

    raise RuntimeError(f"Failed to download {detail.version_id} from all sources")


def find_release_version(
    versions: list[VersionMetadata],
    target_version: str,
) -> VersionMetadata | None:
    """Find a specific release version from the manifest."""
    for v in versions:
        if v.version_id == target_version and v.release_type == "release":
            return v
    return None
