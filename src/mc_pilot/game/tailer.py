"""Log file tailer with rotation and truncation recovery."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LogTailer:
    """Follows a log file; returns new lines; recovers from rotation/truncation."""

    _path: Path | None
    _offset: int
    _inode: int | None
    _rotation_count: int
    _truncation_count: int

    def __init__(self, path: Path | None = None) -> None:
        self._path = path
        self._offset = 0
        self._inode = None
        self._rotation_count = 0
        self._truncation_count = 0
        self._sync_state()

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def offset(self) -> int:
        return self._offset

    @property
    def rotation_count(self) -> int:
        return self._rotation_count

    @property
    def truncation_count(self) -> int:
        return self._truncation_count

    def set_path(self, path: Path) -> None:
        self._path = path
        self._offset = 0
        self._inode = None
        self._rotation_count = 0
        self._truncation_count = 0
        self._sync_state()

    def poll(self) -> list[str]:
        """Return new lines since last poll; handles rotation/truncation."""
        if not self._path or not self._path.exists():
            return []

        try:
            stat = self._path.stat()
        except OSError:
            return []

        current_inode = stat.st_ino
        current_size = stat.st_size

        if self._inode is not None and current_inode != self._inode:
            logger.info(
                "Log rotation detected",
                extra={
                    "path": str(self._path),
                    "old_inode": self._inode,
                    "new_inode": current_inode,
                },
            )
            self._offset = 0
            self._rotation_count += 1
        elif current_size < self._offset:
            logger.info(
                "Log truncation detected",
                extra={
                    "path": str(self._path),
                    "old_offset": self._offset,
                    "new_size": current_size,
                },
            )
            self._offset = 0
            self._truncation_count += 1

        self._inode = current_inode

        if self._offset >= current_size:
            return []

        new_lines: list[str] = []
        try:
            with open(self._path, encoding="utf-8", errors="replace") as f:
                f.seek(self._offset)
                for raw_line in f:
                    line = raw_line.rstrip("\n\r")
                    if line:
                        new_lines.append(line)
                self._offset = f.tell()
        except OSError as exc:
            logger.warning("Failed to read log file", extra={"error": str(exc)})
            return []

        return new_lines

    def read_tail(self, max_lines: int = 500) -> list[str]:
        """Read the tail of the current log for initial scanning."""
        if not self._path or not self._path.exists():
            return []

        try:
            with open(self._path, encoding="utf-8", errors="replace") as f:
                all_lines = [line.rstrip("\n\r") for line in f if line.strip()]
        except OSError:
            return []

        return all_lines[-max_lines:]

    def _sync_state(self) -> None:
        if not self._path or not self._path.exists():
            self._inode = None
            self._offset = 0
            return
        try:
            stat = self._path.stat()
            self._inode = stat.st_ino
            self._offset = stat.st_size
        except OSError:
            self._inode = None
            self._offset = 0
