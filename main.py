# Minimal FastAPI app entrypoint for legacy tests
import app as app_module
from typing import Any

app: Any = app_module.app  # noqa: F401
