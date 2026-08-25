# syntax=docker/dockerfile:1
# Multi-stage Dockerfile for PulsePlate
# Optimized for production with minimal image size and security

# Centralize pip upgrade range (SoT) to avoid drift across stages.
ARG PIP_VERSION_RANGE="pip>=26.0,<27.0"
# SQLite source pins are intentionally mirrored in scripts/ci/docker_source_artifacts.json.
# Docker COPY source paths are literal, so a SQLite bump must update the manifest,
# the COPY filename below, and these SHA3 parts together.
ARG SQLITE_AUTOCONF_VERSION="3530200"
ARG SQLITE_AUTOCONF_SHA3_256_PART_1="025328da"
ARG SQLITE_AUTOCONF_SHA3_256_PART_2="165109f4"
ARG SQLITE_AUTOCONF_SHA3_256_PART_3="8abccc6e"
ARG SQLITE_AUTOCONF_SHA3_256_PART_4="74785080"
ARG SQLITE_AUTOCONF_SHA3_256_PART_5="60804412"
ARG SQLITE_AUTOCONF_SHA3_256_PART_6="bed2bd81"
ARG SQLITE_AUTOCONF_SHA3_256_PART_7="d47e98ba"
ARG SQLITE_AUTOCONF_SHA3_256_PART_8="1b72983b"

# Stage 1: Build stage
FROM python:3.13.14-slim-bookworm@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64 AS builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PULSEPLATE_PYTHON_INDEX_URL
ARG PULSEPLATE_PYTHON_TRUSTED_HOST=""
ARG PULSEPLATE_REQUIREMENTS_FILE="requirements-docker-runtime.txt"

# Install system dependencies for building (curl removed - not needed)
RUN apt-get update && apt-get install -y \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_PYTHON_VERSION_WARNING=1 \
    PULSEPLATE_DOCKER_SINGLE_PASS_LOCKED_INSTALL=1 \
    PULSEPLATE_DOCKER_PIP_LAYER_CACHE=1

# Centralize pip version range (SoT) for CVE fixes.
ARG PIP_VERSION_RANGE
COPY scripts/ci/install_locked_python_requirements.py scripts/ci/emergency_python_wheels.json /tmp/pulseplate-ci/

# SECURITY (CVE-2026-1703):
# Ensure pip is upgraded in the venv before installing dependencies.
# We must upgrade pip inside the image (system + venv) because scanners flag installed pip dist-info.
# requirements.in cannot affect pip shipped in the base image.
# Policy: do not pin exact pip in Dockerfile; use a safe version range instead.
# Mirror-lag fallback is governed by install_locked_python_requirements.py and the sha256 manifest.
# BuildKit cache mount speeds rebuilds; omit --no-cache-dir so pip can use the mounted HTTP cache.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=secret,id=pp_py_index,required=false \
    --mount=type=secret,id=pp_py_host,required=false \
    --mount=type=secret,id=pp_netrc,required=false \
    PULSEPLATE_PYTHON_INDEX_URL="$(cat /run/secrets/pp_py_index 2>/dev/null || printf '%s' "${PULSEPLATE_PYTHON_INDEX_URL:-}")"; \
    PULSEPLATE_PYTHON_TRUSTED_HOST="$(cat /run/secrets/pp_py_host 2>/dev/null || printf '%s' "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}")"; \
    if [ -f /run/secrets/pp_netrc ]; then \
      if [ -e /root/.netrc ]; then \
        echo "Refusing to overwrite an existing /root/.netrc." >&2; \
        exit 1; \
      fi; \
      cp /run/secrets/pp_netrc /root/.netrc; \
      chmod 600 /root/.netrc; \
    fi; \
    trap 'rm -f /root/.netrc' EXIT; \
    if [ -z "${PULSEPLATE_PYTHON_INDEX_URL:-}" ]; then \
      echo "PULSEPLATE_PYTHON_INDEX_URL is required for Docker builds." >&2; \
      exit 1; \
    fi; \
    if [ -n "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}" ]; then \
      /opt/venv/bin/python /tmp/pulseplate-ci/install_locked_python_requirements.py \
        --python-executable /opt/venv/bin/python \
        --upgrade-pip-only \
        --upgrade-pip-spec "${PIP_VERSION_RANGE}" \
        --emergency-wheel-manifest /tmp/pulseplate-ci/emergency_python_wheels.json \
        --index-url "${PULSEPLATE_PYTHON_INDEX_URL}" \
        --trusted-host "${PULSEPLATE_PYTHON_TRUSTED_HOST}"; \
    else \
      /opt/venv/bin/python /tmp/pulseplate-ci/install_locked_python_requirements.py \
        --python-executable /opt/venv/bin/python \
        --upgrade-pip-only \
        --upgrade-pip-spec "${PIP_VERSION_RANGE}" \
        --emergency-wheel-manifest /tmp/pulseplate-ci/emergency_python_wheels.json \
        --index-url "${PULSEPLATE_PYTHON_INDEX_URL}"; \
    fi && \
    rm -rf /tmp/pulseplate-ci

# Copy requirements and install Python dependencies
COPY requirements.txt requirements-ci-lite.txt requirements-docker-runtime.txt constraints.txt ./
COPY scripts/ci/check_python_startup_hooks.py scripts/ci/install_locked_python_requirements.py scripts/ci/emergency_python_wheels.json /tmp/pulseplate-ci/
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=secret,id=pp_py_index,required=false \
    --mount=type=secret,id=pp_py_host,required=false \
    --mount=type=secret,id=pp_netrc,required=false \
    PULSEPLATE_PYTHON_INDEX_URL="$(cat /run/secrets/pp_py_index 2>/dev/null || printf '%s' "${PULSEPLATE_PYTHON_INDEX_URL:-}")"; \
    PULSEPLATE_PYTHON_TRUSTED_HOST="$(cat /run/secrets/pp_py_host 2>/dev/null || printf '%s' "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}")"; \
    if [ -f /run/secrets/pp_netrc ]; then \
      if [ -e /root/.netrc ]; then \
        echo "Refusing to overwrite an existing /root/.netrc." >&2; \
        exit 1; \
      fi; \
      cp /run/secrets/pp_netrc /root/.netrc; \
      chmod 600 /root/.netrc; \
    fi; \
    trap 'rm -f /root/.netrc' EXIT; \
    if [ -z "${PULSEPLATE_PYTHON_INDEX_URL:-}" ]; then \
      echo "PULSEPLATE_PYTHON_INDEX_URL is required for Docker builds." >&2; \
      exit 1; \
    fi; \
    case "${PULSEPLATE_REQUIREMENTS_FILE}" in \
      requirements.txt|requirements-ci-lite.txt|requirements-docker-runtime.txt) ;; \
      *) \
        echo "Unsupported Docker requirements profile: ${PULSEPLATE_REQUIREMENTS_FILE}" >&2; \
        exit 1; \
        ;; \
    esac; \
    if [ -n "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}" ]; then \
      /opt/venv/bin/python /tmp/pulseplate-ci/install_locked_python_requirements.py \
        --python-executable /opt/venv/bin/python \
        --requirements-file "${PULSEPLATE_REQUIREMENTS_FILE}" \
        --guard-script /tmp/pulseplate-ci/check_python_startup_hooks.py \
        --constraints-file constraints.txt \
        --install-mode direct-proxy \
        --emergency-wheel-manifest /tmp/pulseplate-ci/emergency_python_wheels.json \
        --index-url "${PULSEPLATE_PYTHON_INDEX_URL}" \
        --trusted-host "${PULSEPLATE_PYTHON_TRUSTED_HOST}"; \
    else \
      /opt/venv/bin/python /tmp/pulseplate-ci/install_locked_python_requirements.py \
        --python-executable /opt/venv/bin/python \
        --requirements-file "${PULSEPLATE_REQUIREMENTS_FILE}" \
        --guard-script /tmp/pulseplate-ci/check_python_startup_hooks.py \
        --constraints-file constraints.txt \
        --install-mode direct-proxy \
        --emergency-wheel-manifest /tmp/pulseplate-ci/emergency_python_wheels.json \
        --index-url "${PULSEPLATE_PYTHON_INDEX_URL}"; \
    fi && \
    # Remove setuptools from runtime image to fix GHSA-58pv-8j8x-9vj2 (jaraco.context vulnerability)
    # setuptools is only needed for build-time (pip install), not runtime
    /opt/venv/bin/pip uninstall -y setuptools wheel && \
    /opt/venv/bin/python - <<'PY'
import importlib.util, sys
if importlib.util.find_spec("setuptools") is not None:
    sys.stderr.write("setuptools leaked into runtime venv\n")
    sys.exit(1)
PY

# Stage 1b: SQLite runtime library stage
# SECURITY (CVE-2026-11822, CVE-2026-11824):
# Debian bookworm libsqlite3-0 is currently flagged by Trivy with no fixed
# package metadata. Build SQLite 3.53.2 from a pre-fetched official autoconf
# source tarball with SHA3 verification, then copy only the shared runtime
# library into runtime-base. The tarball is prepared outside Docker by
# scripts/ci/fetch_docker_source_artifacts.py so Docker builds do not perform
# hidden live upstream downloads.
FROM python:3.13.14-slim-bookworm@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64 AS sqlite-builder

ARG SQLITE_AUTOCONF_VERSION
ARG SQLITE_AUTOCONF_SHA3_256_PART_1
ARG SQLITE_AUTOCONF_SHA3_256_PART_2
ARG SQLITE_AUTOCONF_SHA3_256_PART_3
ARG SQLITE_AUTOCONF_SHA3_256_PART_4
ARG SQLITE_AUTOCONF_SHA3_256_PART_5
ARG SQLITE_AUTOCONF_SHA3_256_PART_6
ARG SQLITE_AUTOCONF_SHA3_256_PART_7
ARG SQLITE_AUTOCONF_SHA3_256_PART_8

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY build/docker-sources/sqlite-autoconf-3530200.tar.gz /tmp/sqlite-autoconf.tar.gz

RUN python - <<'PY'
from hashlib import sha3_256
from pathlib import Path
import os
import sys

expected = "".join(
    os.environ[f"SQLITE_AUTOCONF_SHA3_256_PART_{index}"] for index in range(1, 9)
)
payload = Path("/tmp/sqlite-autoconf.tar.gz").read_bytes()
actual = sha3_256(payload).hexdigest()
if actual != expected:
    sys.stderr.write(f"SQLite source SHA3 mismatch: expected {expected}, got {actual}\n")
    sys.exit(1)
PY

RUN tar -xzf /tmp/sqlite-autoconf.tar.gz -C /tmp \
    && cd "/tmp/sqlite-autoconf-${SQLITE_AUTOCONF_VERSION}" \
    && ./configure --prefix=/usr/local --disable-static --enable-shared \
    && make -j"$(nproc)" \
    && make install \
    && /usr/local/bin/sqlite3 -version | grep '^3\.53\.2 ' \
    && rm -rf "/tmp/sqlite-autoconf-${SQLITE_AUTOCONF_VERSION}" /tmp/sqlite-autoconf.tar.gz

# Stage 2: Runtime base stage
# NOTE: Keep system package manager tools here so the development stage can install tools via apt.
FROM python:3.13.14-slim-bookworm@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64 AS runtime-base

# Re-declare build arg in this stage.
ARG PIP_VERSION_RANGE
ARG PULSEPLATE_PYTHON_INDEX_URL
ARG PULSEPLATE_PYTHON_TRUSTED_HOST=""

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

# SECURITY (CVE-2026-1703):
# The base image may ship with an affected pip (e.g., 25.2) in system site-packages.
# Upgrade it so scanners do not detect pip 25.2 at /usr/local/lib/... in the runtime image.
# We must upgrade pip inside the image (system + venv) because scanners flag installed pip dist-info.
# requirements.in cannot affect pip shipped in the base image.
# Policy: do not pin exact pip in Dockerfile; use a safe version range instead.
COPY scripts/ci/install_locked_python_requirements.py scripts/ci/emergency_python_wheels.json /tmp/pulseplate-ci/
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=secret,id=pp_py_index,required=false \
    --mount=type=secret,id=pp_py_host,required=false \
    --mount=type=secret,id=pp_netrc,required=false \
    PULSEPLATE_PYTHON_INDEX_URL="$(cat /run/secrets/pp_py_index 2>/dev/null || printf '%s' "${PULSEPLATE_PYTHON_INDEX_URL:-}")"; \
    PULSEPLATE_PYTHON_TRUSTED_HOST="$(cat /run/secrets/pp_py_host 2>/dev/null || printf '%s' "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}")"; \
    if [ -f /run/secrets/pp_netrc ]; then \
      if [ -e /root/.netrc ]; then \
        echo "Refusing to overwrite an existing /root/.netrc." >&2; \
        exit 1; \
      fi; \
      cp /run/secrets/pp_netrc /root/.netrc; \
      chmod 600 /root/.netrc; \
    fi; \
    trap 'rm -f /root/.netrc' EXIT; \
    if [ -z "${PULSEPLATE_PYTHON_INDEX_URL:-}" ]; then \
      echo "PULSEPLATE_PYTHON_INDEX_URL is required for Docker builds." >&2; \
      exit 1; \
    fi; \
    if [ -n "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}" ]; then \
      python /tmp/pulseplate-ci/install_locked_python_requirements.py \
        --python-executable python \
        --upgrade-pip-only \
        --upgrade-pip-spec "${PIP_VERSION_RANGE}" \
        --emergency-wheel-manifest /tmp/pulseplate-ci/emergency_python_wheels.json \
        --index-url "${PULSEPLATE_PYTHON_INDEX_URL}" \
        --trusted-host "${PULSEPLATE_PYTHON_TRUSTED_HOST}"; \
    else \
      python /tmp/pulseplate-ci/install_locked_python_requirements.py \
        --python-executable python \
        --upgrade-pip-only \
        --upgrade-pip-spec "${PIP_VERSION_RANGE}" \
        --emergency-wheel-manifest /tmp/pulseplate-ci/emergency_python_wheels.json \
        --index-url "${PULSEPLATE_PYTHON_INDEX_URL}"; \
    fi && \
    rm -rf /tmp/pulseplate-ci

# Install runtime dependencies only (curl removed - using Python for healthcheck)
# NOTE: libtasn1-6 comes transitively via libgnutls30 (required for TLS/HTTPS).
# CVE-2025-13151 is NOT fixed in Debian bookworm as of 2026-01 (no patched version available).
# Tracking: https://security-tracker.debian.org/tracker/CVE-2025-13151
# Revisit when bookworm publishes a fixed package.
#
# Security hardening:
# Explicitly install libc6/libc-bin from the current bookworm repositories and
# fail the build unless the image reaches Debian's fixed line for CVE-2025-8058.
# Explicitly install libgnutls30, alongside the existing OpenSSL packages, so
# runtime-base/development layers take Debian's latest available bookworm-security
# package instead of a stale base-layer copy. The final production target then
# prunes apt/gpgv/libgnutls30 and the CI runtime surface guard fails closed if
# that package-manager/GnuTLS surface returns.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libc-bin \
        libc6 \
        libgnutls30 \
        libssl3 \
        openssl \
    && for package in libc6 libc-bin; do \
        version="$(dpkg-query -W -f='${Version}' "${package}")"; \
        if ! dpkg --compare-versions "${version}" ge "2.36-9+deb12u13"; then \
            echo "${package} ${version} is below fixed glibc line 2.36-9+deb12u13" >&2; \
            exit 1; \
        fi; \
    done \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY --from=sqlite-builder /usr/local/lib/libsqlite3.so* /usr/local/lib/
RUN printf '%s\n' '/usr/local/lib' > /etc/ld.so.conf.d/00-pulseplate-local-sqlite.conf \
    && ldconfig \
    && python - <<'PY'
import sqlite3
import sys

version = tuple(int(part) for part in sqlite3.sqlite_version.split("."))
if version < (3, 53, 2):
    sys.stderr.write(
        f"Python sqlite3 loaded SQLite {sqlite3.sqlite_version}, expected >= 3.53.2\n"
    )
    sys.exit(1)
PY

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd -r pulseplate && useradd -r -g pulseplate pulseplate

# Create app directory
WORKDIR /app

# Copy only necessary application files (exclude frontend, tests, docs)
COPY --chown=pulseplate:pulseplate app/ ./app/
COPY --chown=pulseplate:pulseplate core/ ./core/
COPY --chown=pulseplate:pulseplate legacy_app.py main.py settings.py ./
# Copy root-level modules that app.py imports
# Note: bmi_core.py is a legacy compatibility shim (no BMI math, delegates to core/bmi/*)
COPY --chown=pulseplate:pulseplate bmi_core.py bmi_visualization.py nutrition_core.py signed_links.py bodyfat.py ./
COPY --chown=pulseplate:pulseplate alembic/ ./alembic/
COPY --chown=pulseplate:pulseplate alembic.ini ./

# Create necessary directories with proper permissions
# Include home directory for matplotlib config and ensure cache/data/logs are writable
RUN mkdir -p /home/pulseplate/.config/matplotlib /app/cache/matplotlib /app/cache/food_db /app/data /app/logs && \
    chown -R pulseplate:pulseplate /home/pulseplate /app/cache /app/data /app/logs

# Set environment variables for matplotlib only.
# Production/staging must supply DATABASE_URL explicitly at runtime.
ENV MPLCONFIGDIR=/app/cache/matplotlib

# Switch to non-root user
USER pulseplate

# Expose port
EXPOSE 8000

# Health check (using Python instead of curl to avoid CVE vulnerabilities)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

# Default command (serve ASGI via app.main:app; legacy_app.py is no longer the entrypoint;
# ensure scripts/CI pass DATABASE_URL/API_KEY envs as needed)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Stage 3: Production stage (hardened)
FROM runtime-base AS production

# RU: Временный возврат к root нужен только для production-only slimming/hardening.
# EN: Temporarily switch back to root only for production-only slimming/hardening.
USER root

# RU: Убираем pip из production-stage, но не трогаем runtime-base/development.
# EN: Remove pip from the production stage only so shared runtime/dev topology stays intact.
RUN /opt/venv/bin/python -m pip uninstall -y pip \
    && /usr/local/bin/python -m pip uninstall -y pip \
    && /opt/venv/bin/python - <<'PY'
import importlib.util
import sys

if importlib.util.find_spec("pip") is not None:
    sys.stderr.write("pip leaked into production venv\n")
    sys.exit(1)
PY
RUN /usr/local/bin/python - <<'PY'
import importlib.util
import sys

if importlib.util.find_spec("pip") is not None:
    sys.stderr.write("pip leaked into production system site-packages\n")
    sys.exit(1)
PY

# RU: Убираем package-manager TLS, ACL/attr, Debian SQLite, gzip и Perl runtime surface только из production;
# RU: runtime-base/development остаются с apt для dev/staging workflows. apt/gpgv/perl-base
# RU: essential для Debian, поэтому удаление намеренно ограничено final production stage
# RU: и проверяется fail-closed.
# EN: Remove the package-manager TLS, ACL/attr, Debian SQLite, gzip, and Perl runtime
# EN: surface only from production; runtime-base/development keep apt for dev/staging workflows.
# EN: apt/gpgv/perl-base are Debian-essential, so this removal is intentionally limited
# EN: to the final production stage and checked fail-closed.
# SECURITY: production-package-pruning-start
RUN perl_module_packages="$(dpkg-query -W -f='${Package}\n' 'perl-modules-*' 2>/dev/null || true)" \
    && dpkg --purge --force-depends --force-remove-essential \
        apt \
        gzip \
        gpgv \
        libacl1 \
        libattr1 \
        libgnutls30 \
        libsqlite3-0 \
        perl-base \
        ${perl_module_packages} \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/* \
    && for package in apt gzip gpgv libacl1 libattr1 libgnutls30 libsqlite3-0 perl-base ${perl_module_packages}; do \
        status="$(dpkg-query -W -f='${db:Status-Abbrev}' "${package}" 2>/dev/null || true)"; \
        if [ "${status#ii}" != "${status}" ]; then \
            echo "${package} remains installed after production package pruning" >&2; \
            exit 1; \
        fi; \
    done \
    && for binary in gzip gunzip zcat; do \
        if command -v "${binary}" >/dev/null 2>&1; then \
            echo "${binary} binary remains after production package pruning" >&2; \
            exit 1; \
        fi; \
    done \
    && /usr/local/bin/python - <<'PY'
import gzip
import io
import ssl
import sqlite3
import sys

if not ssl.OPENSSL_VERSION:
    sys.stderr.write("Python ssl module is unavailable after production package pruning\n")
    sys.exit(1)
version = tuple(int(part) for part in sqlite3.sqlite_version.split("."))
if version < (3, 53, 2):
    sys.stderr.write(
        f"Python sqlite3 loaded SQLite {sqlite3.sqlite_version}, expected >= 3.53.2\n"
    )
    sys.exit(1)
payload = b"pulseplate gzip stdlib smoke"
compressed = gzip.compress(payload, mtime=0)
if gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb").read() != payload:
    sys.stderr.write("Python gzip stdlib smoke failed after production package pruning\n")
    sys.exit(1)
PY
# SECURITY: production-package-pruning-end

# RU: Финальный runtime остаётся non-root как и в runtime-base.
# EN: Final runtime stays non-root, matching the runtime-base contract.
USER pulseplate

# ALEMBIC-IMPORT-OWNERSHIP-GUARD-START
RUN /opt/venv/bin/python - <<'PY'
import importlib
import importlib.metadata
import importlib.util
from pathlib import Path
import sys
import sysconfig

from alembic.config import Config
from alembic.script import ScriptDirectory

literal_app_root = Path("/app")
literal_migration_root = Path("/app/alembic")
for path in (literal_app_root, literal_migration_root):
    if path.is_symlink() or not path.is_dir():
        sys.stderr.write(f"Required repository directory is not a real directory: {path}\n")
        raise SystemExit(1)
app_root = literal_app_root.resolve()
migration_root = literal_migration_root.resolve()
if app_root != literal_app_root:
    sys.stderr.write(f"Repository root must resolve exactly to /app, got {app_root}\n")
    raise SystemExit(1)
if migration_root != literal_migration_root or not migration_root.is_relative_to(app_root):
    sys.stderr.write(
        f"Migration root must resolve exactly to /app/alembic under /app, got {migration_root}\n"
    )
    raise SystemExit(1)
symlink_paths = [path for path in migration_root.rglob("*") if path.is_symlink()]
if symlink_paths:
    rendered = ", ".join(str(path) for path in symlink_paths[:5])
    sys.stderr.write(f"Repository migration tree contains symlink carriers: {rendered}\n")
    raise SystemExit(1)
forbidden_paths = []
package_carrier = migration_root / "__init__.py"
if package_carrier.exists() or package_carrier.is_symlink():
    forbidden_paths.append(package_carrier)
forbidden_paths.extend(migration_root.rglob("__pycache__"))
forbidden_paths.extend(migration_root.rglob("*.pyc"))
forbidden_paths.extend(migration_root.rglob("*.pyo"))
if forbidden_paths:
    rendered = ", ".join(str(path) for path in forbidden_paths[:5])
    sys.stderr.write(f"Repository Alembic package/bytecode carrier detected: {rendered}\n")
    raise SystemExit(1)

venv_root = Path(sys.prefix).resolve()
if venv_root != Path("/opt/venv"):
    sys.stderr.write(f"Production interpreter prefix mismatch: {venv_root}\n")
    raise SystemExit(1)
purelib_root = Path(sysconfig.get_path("purelib")).resolve()
if not purelib_root.is_relative_to(venv_root):
    sys.stderr.write(f"Production purelib is outside /opt/venv: {purelib_root}\n")
    raise SystemExit(1)
distribution = importlib.metadata.distribution("alembic")
distribution_root = Path(distribution.locate_file("")).resolve()
installed_alembic_root = Path(distribution.locate_file("alembic")).resolve()
if distribution_root != purelib_root or not installed_alembic_root.is_relative_to(purelib_root):
    sys.stderr.write("Installed Alembic distribution is outside the production venv purelib\n")
    raise SystemExit(1)
print(f"Alembic distribution root: {distribution_root}")

for module_name in ("alembic", "alembic.config", "alembic.context", "alembic.op"):
    module = importlib.import_module(module_name)
    origin_path = Path(module.__file__ or "")
    if not origin_path.is_file() or origin_path.is_symlink():
        sys.stderr.write(f"{module_name} is not a regular installed module: {origin_path}\n")
        raise SystemExit(1)
    origin = origin_path.resolve()
    if not origin.is_relative_to(installed_alembic_root):
        sys.stderr.write(f"{module_name} resolved outside installed Alembic: {origin}\n")
        raise SystemExit(1)
    if origin.is_relative_to(migration_root):
        sys.stderr.write(f"{module_name} resolved from repository migration data: {origin}\n")
        raise SystemExit(1)

expected_repo_origins = {
    "app": app_root / "app" / "__init__.py",
    "core": app_root / "core" / "__init__.py",
    "settings": app_root / "settings.py",
}
for module_name, expected_origin in expected_repo_origins.items():
    if not expected_origin.is_file() or expected_origin.is_symlink():
        sys.stderr.write(f"{module_name} repository carrier is not a regular file: {expected_origin}\n")
        raise SystemExit(1)
    if not expected_origin.resolve().is_relative_to(app_root):
        sys.stderr.write(f"{module_name} repository carrier escaped /app: {expected_origin}\n")
        raise SystemExit(1)
    spec = importlib.util.find_spec(module_name)
    origin_path = Path(spec.origin or "") if spec is not None else None
    origin = origin_path.resolve() if origin_path is not None else None
    if origin_path != expected_origin or origin != expected_origin.resolve():
        sys.stderr.write(
            f"{module_name} repository ownership mismatch: expected {expected_origin}, got {origin}\n"
        )
        raise SystemExit(1)

config = Config("/app/alembic.ini")
scripts = ScriptDirectory.from_config(config)
if Path(scripts.dir).resolve() != migration_root:
    sys.stderr.write(f"Alembic script directory mismatch: {scripts.dir}\n")
    raise SystemExit(1)
heads = scripts.get_heads()
if len(heads) != 1 or not heads[0].strip():
    sys.stderr.write(f"Alembic migration graph must have one non-empty head, got {heads!r}\n")
    raise SystemExit(1)
PY
RUN /opt/venv/bin/alembic -c /app/alembic.ini heads
# ALEMBIC-IMPORT-OWNERSHIP-GUARD-END

# Stage 4: Staging stage
# Extends production with staging-specific configurations
# Can be customized for staging needs (e.g., debug logging, extended health checks)
#
# HOW TO BUILD FOR STAGING:
#   docker build --target=staging -t myapp:staging .
#   docker build --target=staging --build-arg LOG_LEVEL=INFO -t myapp:staging .
#
# HOW TO RUN STAGING CONTAINER:
#   docker run -e LOG_LEVEL=INFO -e DATABASE_URL=staging_db_url myapp:staging
#
FROM production AS staging

# COMMON STAGING ENV VARS (uncomment/modify as needed):
#
# Logging and debugging:
# ENV LOG_LEVEL=INFO                    # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
# ENV ENABLE_DEBUG_FEATURES=true        # Enable debug endpoints/features
# ENV ENABLE_PROFILING=true             # Enable performance profiling
# ENV SENTRY_ENVIRONMENT=staging        # Sentry error tracking environment
#
# API and feature flags:
# ENV API_RATE_LIMIT=1000               # Higher rate limits for testing
# ENV ENABLE_BETA_FEATURES=true         # Enable beta/experimental features
# ENV MOCK_EXTERNAL_APIS=false          # Use real APIs but with test credentials
#
# Database and caching:
# ENV DATABASE_POOL_SIZE=10             # Smaller pool for staging resources
# ENV REDIS_CACHE_TTL=300               # Shorter cache TTL for testing
#
# Security and monitoring:
# ENV CORS_ALLOWED_ORIGINS="*"          # More permissive CORS for testing
# ENV ENABLE_METRICS_EXPORT=true        # Export metrics to monitoring service
#
# HOW TO SET ENV VARS:
# 1. Build-time (baked into image): Use ENV directive above or --build-arg
# 2. Run-time (flexible): Use -e flag with docker run or docker-compose.yaml
# 3. From file: Use --env-file staging.env with docker run
#
# CI/CD USAGE:
# - In GitHub Actions: Set target in docker/build-push-action@v2 with 'target: staging'
# - In GitLab CI: Add --target=staging to docker build command in .gitlab-ci.yml
# - With docker-compose: Set 'target: staging' in docker-compose.staging.yaml
#
# For detailed staging setup and deployment instructions, see:
# - STAGING_SETUP.md - Complete staging environment configuration
# - DEPLOYMENT_FULL_GUIDE.md - Production and staging deployment workflows
# - .github/workflows/ - CI/CD pipeline examples with staging targets

# Stage 5: Development stage
FROM runtime-base AS development

ARG PULSEPLATE_PYTHON_INDEX_URL
ARG PULSEPLATE_PYTHON_TRUSTED_HOST=""

# Switch back to root for development tools
USER root

# Install development dependencies
# Copy both requirements files as requirements-dev.txt includes requirements.txt via -r
COPY requirements.txt requirements-dev.txt constraints.txt ./
COPY scripts/ci/check_python_startup_hooks.py scripts/ci/install_locked_python_requirements.py scripts/ci/emergency_python_wheels.json /tmp/pulseplate-ci/
# SECURITY NOTE: Do NOT uninstall setuptools/wheel in development stage.
# They are required runtime dependencies of pip-tools for lockfile generation (pip-compile).
# Security mitigation (GHSA-58pv-8j8x-9vj2) applies to runtime/production images only.
RUN --mount=type=secret,id=pp_py_index,required=false \
    --mount=type=secret,id=pp_py_host,required=false \
    --mount=type=secret,id=pp_netrc,required=false \
    PULSEPLATE_PYTHON_INDEX_URL="$(cat /run/secrets/pp_py_index 2>/dev/null || printf '%s' "${PULSEPLATE_PYTHON_INDEX_URL:-}")"; \
    PULSEPLATE_PYTHON_TRUSTED_HOST="$(cat /run/secrets/pp_py_host 2>/dev/null || printf '%s' "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}")"; \
    if [ -f /run/secrets/pp_netrc ]; then \
      if [ -e /root/.netrc ]; then \
        echo "Refusing to overwrite an existing /root/.netrc." >&2; \
        exit 1; \
      fi; \
      cp /run/secrets/pp_netrc /root/.netrc; \
      chmod 600 /root/.netrc; \
    fi; \
    trap 'rm -f /root/.netrc' EXIT; \
    if [ -z "${PULSEPLATE_PYTHON_INDEX_URL:-}" ]; then \
      echo "PULSEPLATE_PYTHON_INDEX_URL is required for Docker builds." >&2; \
      exit 1; \
    fi; \
    if [ -n "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}" ]; then \
      python /tmp/pulseplate-ci/install_locked_python_requirements.py \
        --python-executable python \
        --requirements-file requirements.txt \
        --dev-requirements-file requirements-dev.txt \
        --guard-script /tmp/pulseplate-ci/check_python_startup_hooks.py \
        --constraints-file constraints.txt \
        --install-dev \
        --emergency-wheel-manifest /tmp/pulseplate-ci/emergency_python_wheels.json \
        --index-url "${PULSEPLATE_PYTHON_INDEX_URL}" \
        --trusted-host "${PULSEPLATE_PYTHON_TRUSTED_HOST}"; \
    else \
      python /tmp/pulseplate-ci/install_locked_python_requirements.py \
        --python-executable python \
        --requirements-file requirements.txt \
        --dev-requirements-file requirements-dev.txt \
        --guard-script /tmp/pulseplate-ci/check_python_startup_hooks.py \
        --constraints-file constraints.txt \
        --install-dev \
        --emergency-wheel-manifest /tmp/pulseplate-ci/emergency_python_wheels.json \
        --index-url "${PULSEPLATE_PYTHON_INDEX_URL}"; \
    fi

# Install additional development tools
RUN apt-get update && apt-get install -y \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Switch back to non-root user
USER pulseplate

# Override command for development (serve ASGI via app.main:app; legacy_app.py is no longer
# the entrypoint; ensure scripts/CI pass DATABASE_URL/API_KEY envs as needed)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
