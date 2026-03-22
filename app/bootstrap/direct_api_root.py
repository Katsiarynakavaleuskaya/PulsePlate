"""Direct ``GET /`` policy when clients reach FastAPI without Caddy/static apex."""

from __future__ import annotations

from app.schemas.direct_api_root import DirectApiRootLinks, DirectApiRootProbe

LEGACY_BMI_WEB_ROUTE: str = "/legacy/bmi-calculator"

_DIRECT_ROOT_MESSAGE: str = (
    "Direct access hits the API process only. With Caddy in front, the browser SPA is "
    "served at site apex; use /health, /docs, or the legacy HTML UI link in `links`."
)


def build_direct_api_root_probe() -> DirectApiRootProbe:
    """Return the stable JSON probe for ``GET /`` (uvicorn / internal scanners)."""
    probe: DirectApiRootProbe = DirectApiRootProbe(
        message=_DIRECT_ROOT_MESSAGE,
        links=DirectApiRootLinks(),
    )
    return probe
