# ---------------------------------------------------------------------------
# PulsePlate Dev Container — tooling-only image
# ---------------------------------------------------------------------------
# This image provides the system tooling needed to develop PulsePlate.
# Application dependencies are installed at runtime via `make devcontainer-bootstrap`
# so that the package proxy secret is never baked into image layers.
#
# SECURITY: Do NOT add ARG/ENV for PULSEPLATE_PYTHON_INDEX_URL here.
#           Do NOT run pip install for project requirements during build.
# ---------------------------------------------------------------------------

FROM mcr.microsoft.com/devcontainers/python:1-3.13-bookworm

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        make \
        jq \
        postgresql-client \
        sqlite3 \
        git \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_PYTHON_VERSION_WARNING=1 \
    PYTHONDONTWRITEBYTECODE=1

USER vscode
WORKDIR /workspaces/PulsePlate
