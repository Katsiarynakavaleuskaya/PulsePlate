"""Public discovery surfaces served directly from FastAPI.

RU: Здесь живут простые публичные discovery endpoints вроде `/sitemap.xml`,
которые должны работать даже при прямом обращении к FastAPI.
EN: This module owns small public discovery endpoints such as `/sitemap.xml`
that must stay available even when traffic bypasses the static edge shell.
"""

from __future__ import annotations

from html import escape
from typing import Iterable
from urllib.parse import urljoin

from fastapi import Request
from fastapi.responses import Response

from app.bootstrap.direct_api_root import LEGACY_BMI_WEB_ROUTE

SITEMAP_ROUTE_PATH: str = "/sitemap.xml"
PUBLIC_SITEMAP_PATHS: tuple[str, ...] = (
    "/",
    "/privacy",
    "/terms",
    LEGACY_BMI_WEB_ROUTE,
)


def _build_public_url(base_url: str, path: str) -> str:
    """Return a deterministic absolute URL for sitemap entries.

    RU: Нормализуем базовый URL и путь, чтобы sitemap всегда был стабильным.
    EN: Normalize base URL and path so the sitemap stays deterministic.
    """
    normalized_base = base_url if base_url.endswith("/") else f"{base_url}/"
    normalized_path = path if path.startswith("/") else f"/{path}"
    return urljoin(normalized_base, normalized_path.lstrip("/"))


def build_public_sitemap_xml(
    base_url: str,
    paths: Iterable[str] = PUBLIC_SITEMAP_PATHS,
) -> str:
    """Build the public sitemap XML payload.

    RU: Генерируем минимальный sitemap только для канонических публичных путей.
    EN: Generate a minimal sitemap for canonical public paths only.
    """
    xml_entries = []
    for path in paths:
        public_url = _build_public_url(base_url=base_url, path=path)
        escaped_public_url = escape(public_url, quote=True)
        xml_entries.append(f"<url><loc>{escaped_public_url}</loc></url>")

    xml_body = "".join(xml_entries)
    xml_body = (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' f"{xml_body}" "</urlset>"
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>{xml_body}'


async def serve_public_sitemap(request: Request) -> Response:
    """Serve `/sitemap.xml` from the application surface.

    RU: Endpoint остаётся доступным даже если edge/static shell временно дрейфует.
    EN: Keep the endpoint available even when the edge/static shell drifts.
    """
    sitemap_xml = build_public_sitemap_xml(base_url=str(request.base_url))
    return Response(content=sitemap_xml, media_type="application/xml")
