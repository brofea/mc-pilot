"""Server-rendered page routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


def create_page_router(templates: Jinja2Templates) -> APIRouter:
    """Create page routes bound to the configured template loader."""

    router = APIRouter(include_in_schema=False)

    @router.get("/", response_class=HTMLResponse)
    async def home(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"page_title": "Minecraft Pilot"},
        )

    @router.get("/admin", response_class=HTMLResponse)
    async def admin(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="admin.html",
            context={
                "page_title": "Minecraft Pilot · Developer",
                "settings": request.app.state.settings.safe_summary(),
            },
        )

    return router
