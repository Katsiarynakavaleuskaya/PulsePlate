from __future__ import annotations

import logging
from typing import Any, cast

from app.bootstrap.application import app as _canonical_app

# Preserve the declared lexical legacy surface while re-exporting the exact canonical object.
app = cast(Any, _canonical_app)

# Canonical application bootstrap owns environment resolution, dotenv loading,
# root logging configuration, metadata construction, and the FastAPI instance.
logger = logging.getLogger(__name__)
bmi_logger = logging.getLogger("app.bmi")


# (moved to top with other imports)


# PRO/VIP route registration is owned by app.main canonical bootstrap.
# Shopping-list route registration is owned by app.main canonical bootstrap.

# Premium week router registration is now handled in
# app.routers.pro_registration.register_pro_routes() for centralized registration.

# Legacy event handlers - replaced with lifespan
# @app.on_event("startup")
# @app.on_event("shutdown")


# ---------- Core logic ----------


# Bodyfat, BMI, and BMI Pro route registration is owned by app.main canonical bootstrap.
