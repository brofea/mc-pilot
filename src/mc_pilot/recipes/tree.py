"""Deterministic recipe material tree algorithms."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from mc_pilot.recipes.models import Ingredient, MaterialNode, RecipeInfo

logger = logging.getLogger(__name__)

DEFAULT_MAX_NODES = 5000
DEFAULT_MAX_DEPTH = 50


@dataclass
class TreeBuildResult:
    root: MaterialNode
    leaf_totals: dict[str, int]
    total_nodes: int = 0
    truncated: bool = False
    truncation_reason: str | None = None


class RecipeTreeEngine:
    """Builds deterministic recipe decomposition trees."""

    _recipes: dict[str, list[RecipeInfo]]
    _item_names: dict[str, str]
    _tags: dict[str, list[str]]
    _version_id: str

    def __init__(
        self,
        recipes: dict[str, list[RecipeInfo]],
        item_names: dict[str, str] | None = None,
        tags: dict[str, list[str]] | None = None,
        version_id: str = "",
    ) -> None:
        self._recipes = recipes
        self._item_names = item_names or {}
        self._tags = tags or {}
        self._version_id = version_id

    def direct_recipes(self, item_id: str) -> list[RecipeInfo]:
        return list(self._recipes.get(item_id, []))

    def build_tree(
        self,
        target_item_id: str,
        target_quantity: int = 1,
        max_depth: int | None = None,
        max_nodes: int = DEFAULT_MAX_NODES,
        recipe_selections: dict[str, str] | None = None,
    ) -> TreeBuildResult:
        selections = dict(recipe_selections) if recipe_selections else {}

        depth_limit = max_depth if max_depth is not None else DEFAULT_MAX_DEPTH
        node_count = 0
        truncated = False
        truncation_reason: str | None = None
        leaf_totals: dict[str, int] = {}

        def _build(
            item_id: str,
            quantity: int,
            depth: int,
            ancestor_items: frozenset[str],
        ) -> MaterialNode:
            nonlocal node_count, truncated, truncation_reason

            node_count += 1
            if node_count > max_nodes:
                truncated = True
                truncation_reason = f"Exceeded max nodes ({max_nodes})"
                return MaterialNode(
                    item_id=item_id,
                    display_name=self._item_name(item_id),
                    quantity=quantity,
                    depth=depth,
                    is_leaf=True,
                )

            recipes = self._recipes.get(item_id, [])
            if not recipes or depth >= depth_limit:
                _accumulate_leaf(leaf_totals, item_id, quantity)
                return MaterialNode(
                    item_id=item_id,
                    display_name=self._item_name(item_id),
                    quantity=quantity,
                    depth=depth,
                    is_leaf=True,
                )

            # Deterministic recipe selection
            selected_idx = 0
            if item_id in selections:
                for i, r in enumerate(recipes):
                    if r.recipe_id == selections[item_id]:
                        selected_idx = i
                        break
            else:
                selected_idx, _ = _choose_default_recipe(recipes)

            recipe = recipes[selected_idx]
            alternative_ids = tuple(
                r.recipe_id for i, r in enumerate(recipes) if i != selected_idx
            )

            # Check cycle: any ingredient that refers back to an ancestor
            child_ids: set[str] = set()
            for ing in recipe.ingredients:
                resolved = self._resolve_ingredient(ing)
                child_ids.update(resolved)

            if child_ids & ancestor_items:
                truncated = True
                truncation_reason = f"Cycle detected for {item_id}"
                _accumulate_leaf(leaf_totals, item_id, quantity)
                return MaterialNode(
                    item_id=item_id,
                    display_name=self._item_name(item_id),
                    quantity=quantity,
                    depth=depth,
                    is_leaf=True,
                )

            new_ancestors = ancestor_items | {item_id}

            batches = int(quantity * recipe.result_count)
            children: list[MaterialNode] = []
            for ing in recipe.ingredients:
                resolved = self._resolve_ingredient(ing)
                if len(resolved) == 1:
                    child_id = next(iter(resolved))
                    child_node = _build(child_id, batches, depth + 1, new_ancestors)
                    children.append(child_node)
                else:
                    # Tag material — represent as a collection node
                    tag_node = MaterialNode(
                        item_id=ing.tag or "unknown_tag",
                        display_name=f"#{ing.tag}" if ing.tag else "any",
                        quantity=batches,
                        depth=depth + 1,
                        is_leaf=False,
                        children=tuple(
                            _build(cid, batches, depth + 2, new_ancestors)
                            for cid in sorted(resolved)
                        ),
                    )
                    children.append(tag_node)

            is_leaf = len(children) == 0
            if is_leaf:
                _accumulate_leaf(leaf_totals, item_id, quantity)

            return MaterialNode(
                item_id=item_id,
                display_name=self._item_name(item_id),
                quantity=quantity,
                depth=depth,
                recipe_id=recipe.recipe_id,
                is_leaf=is_leaf,
                children=tuple(children),
                alternative_recipes=alternative_ids,
            )

        root = _build(
            target_item_id,
            target_quantity,
            depth=0,
            ancestor_items=frozenset(),
        )

        return TreeBuildResult(
            root=root,
            leaf_totals=dict(leaf_totals),
            total_nodes=node_count,
            truncated=truncated,
            truncation_reason=truncation_reason,
        )

    def _resolve_ingredient(self, ing: Ingredient) -> set[str]:
        if ing.ingredient_kind == "item" and ing.item_id:
            return {ing.item_id}
        if ing.ingredient_kind == "tag" and ing.tag:
            return set(self._tags.get(ing.tag, []))
        return set()

    def _item_name(self, item_id: str) -> str:
        return self._item_names.get(item_id, item_id)


def _choose_default_recipe(
    recipes: list[RecipeInfo],
) -> tuple[int, int]:
    """Select the default recipe branch deterministically.

    Priority: shapeless > shaped with fewer ingredients > built-in category > lexicographic.
    Returns (index, score) where lower score = higher priority.
    """
    scored: list[tuple[int, tuple[int, int, int], str]] = []
    for idx, r in enumerate(recipes):
        # Prefer shapeless (-1) over shaped (0)
        shape_score = -1 if r.recipe_type == "minecraft:crafting_shapeless" else 0
        ingredient_count = len(r.ingredients)
        category_rank = (
            0
            if r.category in ("misc", "building", "redstone", "equipment")
            else 1
        )
        scored.append((idx, (shape_score, ingredient_count, category_rank), r.recipe_id))

    scored.sort(key=lambda x: x[1])
    return scored[0][0], 0


def _accumulate_leaf(leaf_totals: dict[str, int], item_id: str, quantity: int) -> None:
    leaf_totals[item_id] = leaf_totals.get(item_id, 0) + quantity
