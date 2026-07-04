"""SQLite storage operations for recipes, items, and tags."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from mc_pilot.recipes.models import (
    Ingredient,
    ItemOrm,
    ItemTagOrm,
    RecipeInfo,
    RecipeIngredientOrm,
    RecipeOrm,
)

logger = logging.getLogger(__name__)


def clear_version_data(session: Session, version_id: str) -> int:
    """Remove all recipe, item, and tag rows for a given version."""
    count = 0
    for model_cls in (RecipeIngredientOrm, RecipeOrm, ItemTagOrm, ItemOrm):
        stmt = delete(model_cls).where(model_cls.version_id == version_id)
        count += session.execute(stmt).rowcount
    session.commit()
    logger.info("Cleared version data", extra={"version": version_id, "rows": count})
    return count


def store_recipes(
    session: Session,
    recipes: list[RecipeInfo],
    version_id: str,
) -> int:
    """Persist a batch of RecipeInfo objects into the database."""
    count = 0
    for info in recipes:
        orm = RecipeOrm(
            recipe_id=info.recipe_id,
            recipe_type=info.recipe_type,
            group=info.group,
            result_item_id=info.result_item_id,
            result_count=info.result_count,
            category=info.category,
            version_id=version_id,
            raw_data={},
            indexed_at=datetime.now(UTC),
        )
        session.add(orm)
        session.flush()

        for pos, ing in enumerate(info.ingredients):
            ingredient_orm = RecipeIngredientOrm(
                recipe_fk=orm.id,
                ingredient_kind=ing.ingredient_kind,
                item_id=ing.item_id,
                tag=ing.tag,
                count=ing.count,
                slot_key=ing.slot_key,
                position=pos,
                version_id=version_id,
            )
            session.add(ingredient_orm)
        count += 1

    session.commit()
    logger.info("Stored recipes", extra={"count": count, "version": version_id})
    return count


def store_items(
    session: Session,
    items: dict[str, str],
    version_id: str,
    item_type: str = "item",
) -> int:
    """Persist item/block display names."""
    count = 0
    for resource_id, display_name in items.items():
        orm = ItemOrm(
            resource_id=resource_id,
            display_name=display_name,
            item_type=item_type,
            version_id=version_id,
            raw_data={},
            indexed_at=datetime.now(UTC),
        )
        session.add(orm)
        count += 1
    session.commit()
    logger.info("Stored items", extra={"count": count, "version": version_id})
    return count


def store_tags(
    session: Session,
    tags: dict[str, list[str]],
    version_id: str,
) -> int:
    """Persist item tags."""
    count = 0
    for tag_name, items in tags.items():
        for item_id in items:
            orm = ItemTagOrm(
                tag_name=tag_name,
                item_id=item_id,
                version_id=version_id,
            )
            session.add(orm)
            count += 1
    session.commit()
    logger.info(
        "Stored item tags",
        extra={"tags": len(tags), "entries": count, "version": version_id},
    )
    return count


def load_recipes(session: Session, version_id: str) -> dict[str, list[RecipeInfo]]:
    """Load all recipes for a version as a dict keyed by result_item_id."""
    stmt = select(RecipeOrm).where(RecipeOrm.version_id == version_id)
    orms = session.execute(stmt).scalars().all()

    result: dict[str, list[RecipeInfo]] = {}
    for orm in orms:
        info = RecipeInfo(
            recipe_id=orm.recipe_id,
            recipe_type=orm.recipe_type,
            group=orm.group,
            result_item_id=orm.result_item_id,
            result_count=orm.result_count,
            category=orm.category,
            ingredients=tuple(
                Ingredient(
                    ingredient_kind=ing.ingredient_kind,
                    item_id=ing.item_id,
                    tag=ing.tag,
                    count=ing.count,
                    slot_key=ing.slot_key,
                )
                for ing in orm.ingredients
            ),
            version_id=orm.version_id,
        )
        result.setdefault(orm.result_item_id, []).append(info)

    return result


def load_item_names(session: Session, version_id: str) -> dict[str, str]:
    """Load display names for all items in a version."""
    stmt = select(ItemOrm).where(ItemOrm.version_id == version_id)
    orms = session.execute(stmt).scalars().all()
    return {o.resource_id: o.display_name for o in orms}


def load_tags(session: Session, version_id: str) -> dict[str, list[str]]:
    """Load all item tags as a dict of tag_name -> list of item_id."""
    stmt = select(ItemTagOrm).where(ItemTagOrm.version_id == version_id)
    orms = session.execute(stmt).scalars().all()
    result: dict[str, list[str]] = {}
    for o in orms:
        result.setdefault(o.tag_name, []).append(o.item_id)
    return result


def count_recipes(session: Session, version_id: str) -> dict[str, int]:
    """Return counts for recipes, items, and tags in a version."""
    recipe_count = session.execute(
        select(func.count()).select_from(RecipeOrm).where(RecipeOrm.version_id == version_id)
    ).scalar_one()
    item_count = session.execute(
        select(func.count()).select_from(ItemOrm).where(ItemOrm.version_id == version_id)
    ).scalar_one()
    tag_count = session.execute(
        select(func.count()).select_from(ItemTagOrm).where(ItemTagOrm.version_id == version_id)
    ).scalar_one()
    return {"recipes": recipe_count, "items": item_count, "tags": tag_count}
