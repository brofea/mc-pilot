"""Recipe domain models, SQLAlchemy ORM tables, and API contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, PlainSerializer, PlainValidator
from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mc_pilot.storage.sqlite import Base


def _validate_iso_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError(f"Expected ISO-format datetime, got {type(value)}")


def _serialize_iso_datetime(value: datetime) -> str:
    return value.isoformat()


IsoDateTime = Annotated[
    datetime,
    PlainValidator(_validate_iso_datetime),
    PlainSerializer(_serialize_iso_datetime, when_used="json"),
]


# ── SQLAlchemy ORM models ──────────────────────────────────────────────


class GameVersionOrm(Base):
    __tablename__ = "game_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version_id: Mapped[str] = mapped_column(String(64), unique=True)
    release_type: Mapped[str] = mapped_column(String(32))
    client_url: Mapped[str] = mapped_column(String(1024))
    client_sha1: Mapped[str] = mapped_column(String(40))
    client_size: Mapped[int] = mapped_column()
    download_source: Mapped[str] = mapped_column(String(64))
    download_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    build_status: Mapped[str] = mapped_column(String(32), default="pending")


class ItemOrm(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resource_id: Mapped[str] = mapped_column(String(256))
    display_name: Mapped[str] = mapped_column(String(256))
    item_type: Mapped[str] = mapped_column(String(32))
    version_id: Mapped[str] = mapped_column(String(64), index=True)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("resource_id", "version_id", name="uq_item_resource_version"),
        Index("ix_items_version_type", "version_id", "item_type"),
    )


class RecipeOrm(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recipe_id: Mapped[str] = mapped_column(String(256), unique=True)
    recipe_type: Mapped[str] = mapped_column(String(128))
    group: Mapped[str | None] = mapped_column(String(256))
    result_item_id: Mapped[str] = mapped_column(String(256), index=True)
    result_count: Mapped[int] = mapped_column()
    category: Mapped[str | None] = mapped_column(String(64))
    version_id: Mapped[str] = mapped_column(String(64), index=True)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    ingredients: Mapped[list[RecipeIngredientOrm]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_recipes_version_result", "version_id", "result_item_id"),)


class RecipeIngredientOrm(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recipe_fk: Mapped[int] = mapped_column(ForeignKey("recipes.id"), index=True)
    ingredient_kind: Mapped[str] = mapped_column(String(32))
    item_id: Mapped[str | None] = mapped_column(String(256))
    tag: Mapped[str | None] = mapped_column(String(256))
    count: Mapped[int] = mapped_column(default=1)
    slot_key: Mapped[str | None] = mapped_column(String(8))
    position: Mapped[int] = mapped_column(default=0)
    version_id: Mapped[str] = mapped_column(String(64), index=True)

    recipe: Mapped[RecipeOrm] = relationship(back_populates="ingredients")


class ItemTagOrm(Base):
    __tablename__ = "item_tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tag_name: Mapped[str] = mapped_column(String(256), index=True)
    item_id: Mapped[str] = mapped_column(String(256), index=True)
    version_id: Mapped[str] = mapped_column(String(64), index=True)

    __table_args__ = (
        UniqueConstraint("tag_name", "item_id", "version_id", name="uq_tag_item_version"),
        Index("ix_tags_version", "version_id"),
    )


# ── Pydantic domain models ─────────────────────────────────────────────


class Ingredient(BaseModel):
    """A single ingredient slot in a recipe pattern or shapeless list."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ingredient_kind: str  # "item" | "tag"
    item_id: str | None = None
    tag: str | None = None
    count: int = 1
    slot_key: str | None = None


class RecipeInfo(BaseModel):
    """Normalised view of one crafting recipe."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    recipe_id: str
    recipe_type: str
    group: str | None = None
    result_item_id: str
    result_count: int = 1
    category: str | None = None
    ingredients: tuple[Ingredient, ...] = ()
    version_id: str = ""


class MaterialNode(BaseModel):
    """A node in a recipe material tree."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str
    display_name: str = ""
    quantity: int = 1
    depth: int = 0
    recipe_id: str | None = None
    is_leaf: bool = True
    children: tuple[MaterialNode, ...] = ()
    alternative_recipes: tuple[str, ...] = ()


class RecipeTreeResponse(BaseModel):
    """API response for a recipe tree query."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_item_id: str
    target_display_name: str = ""
    target_quantity: int = 1
    max_depth: int | None = None
    tree: MaterialNode
    leaf_totals: dict[str, int] = {}
    truncated: bool = False
    truncation_reason: str | None = None
    total_nodes: int = 0
    version_id: str = ""


class DirectRecipeResponse(BaseModel):
    """API response for a direct recipe lookup."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str
    display_name: str = ""
    recipes: tuple[RecipeInfo, ...] = ()
    total_recipes: int = 0
    version_id: str = ""


class VersionMetadata(BaseModel):
    """Metadata for a single game version from the manifest."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version_id: str
    release_type: str
    manifest_url: str


class VersionDetail(BaseModel):
    """Detailed version info including download URL and SHA-1."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version_id: str
    client_url: str
    client_sha1: str
    client_size: int
