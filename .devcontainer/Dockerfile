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

ARG DEVCONTAINER_NATIVE_SDK_IMAGE=scratch

# Keep the service context when supported and its scoped local image on older Compose.
FROM ${DEVCONTAINER_NATIVE_SDK_IMAGE} AS native_sdk

FROM mcr.microsoft.com/devcontainers/python:1-3.13-bookworm AS tooling

USER root

# Remove Yarn APT source shipped by Microsoft base image — the GPG key
# (62D54FD4003F6525) is periodically expired/rotated upstream and breaks
# apt-get update in CI.  Yarn is not needed for backend development;
# Node.js is provided by the devcontainer Node feature instead.
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && rm -f /usr/share/keyrings/yarn-keyring.gpg \
    && apt-get update \
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

# The full consumer remains the default target and requires the genuine SDK context.
FROM tooling AS devcontainer
USER root

# Native SDK and verified binary wheelhouse from the existing source producer.
# This image build only copies artifacts; the user installs into a venv offline.
COPY --from=native_sdk /usr/local/lib/ /usr/local/lib/
COPY --from=native_sdk /usr/local/include/ /usr/local/include/
COPY --from=native_sdk /usr/local/bin/ /usr/local/bin/
COPY --from=native_sdk /usr/local/share/terminfo/ /usr/local/share/terminfo/
COPY --from=native_sdk /psycopg-sdk/ /opt/psycopg-sdk/
COPY --from=native_sdk /wheelhouse/ /opt/dev-wheelhouse/
# Admit the copied artifacts against the current SDK receipt and compiled dev profile.
RUN --network=none \
    --mount=type=bind,source=scripts/ci/install_locked_python_requirements.py,target=/tmp/pulseplate-sdk-admission/scripts/ci/install_locked_python_requirements.py \
    --mount=type=bind,source=requirements.txt,target=/tmp/pulseplate-sdk-admission/requirements.txt \
    --mount=type=bind,source=requirements-dev.txt,target=/tmp/pulseplate-sdk-admission/requirements-dev.txt \
    python3 -I - /tmp/pulseplate-sdk-admission /opt/psycopg-sdk /opt/dev-wheelhouse / <<'PY'
from pathlib import Path
import sys

inputs, sdk, wheelhouse, native_root = map(Path, sys.argv[1:])
sys.path.insert(0, str(inputs))
from scripts.ci.install_locked_python_requirements import (
    _exact_locked_artifacts,
    _validate_exact_wheelhouse,
    read_psycopg_c_sdk,
)

admitted = read_psycopg_c_sdk(sdk, native_root=native_root)
expected = _exact_locked_artifacts((inputs / "requirements.txt", inputs / "requirements-dev.txt"))
artifacts = _validate_exact_wheelhouse(wheelhouse=wheelhouse, expected=expected)
current = next((wheel for wheel in artifacts if wheel.artifact_key == admitted.artifact_key), None)
if current is None or current.snapshot.digest != admitted.snapshot.digest:
    raise RuntimeError("Consumed Psycopg C differs from the admitted SDK wheel.")
PY
RUN test -f /opt/psycopg-sdk/psycopg-c-sdk.json \
    && test ! -L /opt/psycopg-sdk/psycopg-c-sdk.json \
    && test -f /opt/psycopg-sdk/psycopg_c-3.3.4-cp313-cp313-linux_x86_64.whl \
    && test ! -L /opt/psycopg-sdk/psycopg_c-3.3.4-cp313-cp313-linux_x86_64.whl \
    && chmod 755 /opt/psycopg-sdk \
    && chmod 644 /opt/psycopg-sdk/psycopg-c-sdk.json /opt/psycopg-sdk/psycopg_c-3.3.4-cp313-cp313-linux_x86_64.whl \
    && chmod 755 /opt/dev-wheelhouse \
    && chmod 644 /opt/dev-wheelhouse/*.whl \
    && ldconfig \
    && install -d -o vscode -g vscode /workspaces/PulsePlate/.venv
ENV PULSEPLATE_PSYCOPG_C_SDK=/opt/psycopg-sdk \
    PULSEPLATE_BOOTSTRAP_WHEELHOUSE=/opt/dev-wheelhouse

USER vscode
WORKDIR /workspaces/PulsePlate
