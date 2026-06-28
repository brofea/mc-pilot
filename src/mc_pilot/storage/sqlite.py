"""SQLite engine ownership and health probing."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative model base for future local tables."""


def ensure_sqlite_parent(sqlite_url: str) -> None:
    """Ensure a relative SQLite database parent directory exists."""

    prefix = "sqlite:///"
    if not sqlite_url.startswith(prefix):
        return
    database = sqlite_url.removeprefix(prefix)
    if database == ":memory:":
        return
    Path(database).expanduser().parent.mkdir(parents=True, exist_ok=True)


def create_sqlite_engine(sqlite_url: str) -> Engine:
    """Create the application-owned SQLAlchemy engine."""

    ensure_sqlite_parent(sqlite_url)
    connect_args = {"check_same_thread": False} if sqlite_url.startswith("sqlite") else {}
    return create_engine(sqlite_url, connect_args=connect_args, pool_pre_ping=True)


def initialize_database(engine: Engine) -> None:
    """Create the currently known local schema."""

    Base.metadata.create_all(engine)


def sqlite_is_ready(engine: Engine) -> bool:
    """Return whether SQLite can execute a trivial query."""

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except (OSError, SQLAlchemyError):
        return False
    return True
