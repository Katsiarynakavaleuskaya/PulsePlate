"""Canonical construction and ownership of the PulsePlate FastAPI instance."""

from __future__ import annotations

import logging
import os

import dotenv
from fastapi import FastAPI
from settings import get_runtime_env_name

from app.application_metadata import ApplicationMetadata, build_application_metadata
from app.bootstrap.lifespan import application_lifespan

RUNTIME_ENV = get_runtime_env_name()

if (
    "PATH" in os.environ
    and RUNTIME_ENV in {"local", "dev", "development"}
    and os.getenv("PYTEST_CURRENT_TEST") is None
):
    dotenv.load_dotenv()

logging.basicConfig(
    level=logging.DEBUG if RUNTIME_ENV in {"test", "testing"} else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

APPLICATION_METADATA = build_application_metadata(runtime_env=RUNTIME_ENV)


def _create_fastapi_application(metadata: ApplicationMetadata) -> FastAPI:
    """Construct an independent FastAPI object from immutable metadata."""

    return FastAPI(**metadata.to_fastapi_kwargs(), lifespan=application_lifespan)


app = _create_fastapi_application(APPLICATION_METADATA)
