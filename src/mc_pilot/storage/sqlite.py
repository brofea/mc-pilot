"""SQLite engine ownership, health probing, and conversation persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    Column,
    DateTime,
    Engine,
    ForeignKey,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, relationship


class Base(DeclarativeBase):
    """Declarative model base for local tables."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ConversationModel(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False, default="新对话")
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    messages = relationship(
        "MessageModel",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="MessageModel.created_at",
    )


class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    conversation = relationship("ConversationModel", back_populates="messages")


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


class ConversationStore:
    """CRUD operations for conversations and messages."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def _session(self) -> Session:
        return Session(self._engine)

    def list_conversations(self) -> list[dict[str, object]]:
        with self._session() as sess:
            rows = (
                sess.query(ConversationModel)
                .order_by(ConversationModel.updated_at.desc())
                .all()
            )
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "created_at": r.created_at.isoformat(),
                    "updated_at": r.updated_at.isoformat(),
                }
                for r in rows
            ]

    def create_conversation(self, title: str = "新对话") -> dict[str, object]:
        conv = ConversationModel(title=title)
        with self._session() as sess:
            sess.add(conv)
            sess.commit()
            return {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
            }

    def get_conversation(self, conv_id: str) -> dict[str, object] | None:
        with self._session() as sess:
            conv = sess.get(ConversationModel, conv_id)
            if conv is None:
                return None
            return {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "messages": [
                    {
                        "id": m.id,
                        "role": m.role,
                        "content": m.content,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in conv.messages
                ],
            }

    def update_title(self, conv_id: str, title: str) -> bool:
        with self._session() as sess:
            conv = sess.get(ConversationModel, conv_id)
            if conv is None:
                return False
            conv.title = title  # type: ignore[assignment]
            conv.updated_at = _utcnow()  # type: ignore[assignment]
            sess.commit()
            return True

    def delete_conversation(self, conv_id: str) -> bool:
        with self._session() as sess:
            conv = sess.get(ConversationModel, conv_id)
            if conv is None:
                return False
            sess.delete(conv)
            sess.commit()
            return True

    def add_message(
        self, conv_id: str, role: str, content: str
    ) -> dict[str, object] | None:
        with self._session() as sess:
            conv = sess.get(ConversationModel, conv_id)
            if conv is None:
                return None
            msg = MessageModel(conversation_id=conv_id, role=role, content=content)
            conv.updated_at = _utcnow()  # type: ignore[assignment]
            sess.add(msg)
            sess.commit()
            return {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }

    def get_messages(self, conv_id: str) -> list[dict[str, object]]:
        with self._session() as sess:
            rows = (
                sess.query(MessageModel)
                .filter(MessageModel.conversation_id == conv_id)
                .order_by(MessageModel.created_at)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "role": r.role,
                    "content": r.content,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]
