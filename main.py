# Minimal FastAPI app entrypoint for legacy tests
import app as app_module
from fastapi import FastAPI
from typing import cast

app: FastAPI = cast(FastAPI, app_module.app)  # noqa: F401
