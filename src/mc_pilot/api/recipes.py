"""Recipe query HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel


class TreeQuery(BaseModel):
    item_id: str
    quantity: int = 1
    max_depth: int | None = None


def create_recipe_router(recipe_service: Any) -> APIRouter:
    router = APIRouter(prefix="/api/recipes", tags=["recipes"])

    @router.get("/{item_id}")
    async def direct_recipe(item_id: str, request: Request) -> dict[str, object]:
        result = recipe_service.query_direct(item_id)
        dumped: dict[str, object] = result.model_dump(mode="json")
        return dumped

    @router.post("/tree")
    async def recipe_tree(body: TreeQuery, request: Request) -> dict[str, object]:
        result = recipe_service.query_tree(
            item_id=body.item_id,
            quantity=body.quantity,
            max_depth=body.max_depth,
        )
        dumped: dict[str, object] = result.model_dump(mode="json")
        return dumped

    return router
