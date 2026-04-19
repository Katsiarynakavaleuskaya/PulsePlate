"""Direct ``GET /`` policy when clients reach FastAPI without Caddy/static apex."""

from __future__ import annotations

from fastapi.responses import HTMLResponse
from starlette.requests import Request

from app.bootstrap.legacy_bmi_web_html import render_legacy_bmi_calculator_page
from app.schemas.direct_api_root import DirectApiRootLinks, DirectApiRootProbe

LEGACY_BMI_WEB_ROUTE: str = "/legacy/bmi-calculator"

DIRECT_API_ROOT_PROBE_MESSAGE: str = (
    "Direct access hits the API process only. With Caddy in front, the browser SPA is "
    "served at site apex; use /health, /docs, or the legacy HTML UI link in `links`."
)


def build_direct_api_root_probe() -> DirectApiRootProbe:
    """Return the stable JSON probe for ``GET /`` (uvicorn / internal scanners)."""
    probe: DirectApiRootProbe = DirectApiRootProbe(
        message=DIRECT_API_ROOT_PROBE_MESSAGE,
        links=DirectApiRootLinks(),
    )
    return probe


async def serve_direct_api_root_probe() -> DirectApiRootProbe:
    """ASGI handler for ``GET /`` JSON probe (registered from ``app.main`` bootstrap)."""
    return build_direct_api_root_probe()


async def serve_legacy_bmi_calculator_web(request: Request) -> HTMLResponse:
    """ASGI handler for embedded legacy BMI HTML (registered from ``app.main`` bootstrap)."""
    return render_legacy_bmi_calculator_page(request)
