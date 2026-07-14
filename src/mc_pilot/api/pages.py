"""Server-rendered page routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates


def create_page_router(templates: Jinja2Templates, app_dir: Path) -> APIRouter:
    """Create page routes bound to the configured template loader."""

    router = APIRouter(include_in_schema=False)

    spa_index = app_dir / "index.html"

    def spa_or_template(request: Request, title: str) -> Response:
        if spa_index.is_file():
            return FileResponse(spa_index)
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"page_title": title},
        )

    @router.get("/", response_class=HTMLResponse)
    async def home(request: Request) -> Response:
        return spa_or_template(request, "Minecraft Pilot")

    @router.get("/admin", response_class=HTMLResponse)
    async def admin(request: Request) -> Response:
        return spa_or_template(request, "Minecraft Pilot · 开发者后台")

    @router.get("/{path:path}", response_class=HTMLResponse)
    async def spa(request: Request, path: str) -> Response:
        return spa_or_template(request, "Minecraft Pilot")

    return router
