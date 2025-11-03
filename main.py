# Minimal FastAPI app entrypoint for legacy tests
import app as app_module

app = app_module.app  # noqa: F401
