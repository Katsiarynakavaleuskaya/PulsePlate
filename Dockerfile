# Multi-stage Dockerfile for PulsePlate
# Optimized for production with minimal image size and security

# Stage 1: Build stage
FROM python:3.13.6-slim-bookworm AS builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Install system dependencies for building (curl removed - not needed)
RUN apt-get update && apt-get install -y \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_PYTHON_VERSION_WARNING=1

# Copy requirements and install Python dependencies
COPY requirements.txt requirements-dev.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt && \
    # Remove setuptools from runtime image to fix GHSA-58pv-8j8x-9vj2 (jaraco.context vulnerability)
    # setuptools is only needed for build-time (pip install), not runtime
    python -m pip uninstall -y setuptools wheel || true

# Stage 2: Runtime base stage
# NOTE: Keep system package manager tools here so the development stage can install tools via apt.
FROM python:3.13.6-slim-bookworm AS runtime-base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

# Install runtime dependencies only (curl removed - using Python for healthcheck)
# NOTE: libtasn1-6 comes transitively via libgnutls30 (required for TLS/HTTPS).
# CVE-2025-13151 is NOT fixed in Debian bookworm as of 2026-01 (no patched version available).
# Tracking: https://security-tracker.debian.org/tracker/CVE-2025-13151
# Revisit when bookworm publishes a fixed package.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libc6 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

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
COPY --chown=pulseplate:pulseplate bmi_core.py bmi_visualization.py nutrition_core.py signed_links.py bodyfat.py ./
COPY --chown=pulseplate:pulseplate alembic/ ./alembic/
COPY --chown=pulseplate:pulseplate alembic.ini ./

# Create necessary directories with proper permissions
# Include home directory for matplotlib config and ensure cache/data/logs are writable
RUN mkdir -p /home/pulseplate/.config/matplotlib /app/cache/matplotlib /app/cache/food_db /app/data /app/logs && \
    chown -R pulseplate:pulseplate /home/pulseplate /app/cache /app/data /app/logs

# Set environment variables for matplotlib and database
ENV MPLCONFIGDIR=/app/cache/matplotlib \
    DATABASE_URL=sqlite:////app/cache/pulseplate.db

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

# NOTE: On Debian-based images, `apt` depends on `gpgv` and removing either can break the base system.
# We intentionally keep them in the production image and document the Trivy finding via `.trivyignore`.

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

# Switch back to root for development tools
USER root

# Install development dependencies
# Copy both requirements files as requirements-dev.txt includes requirements.txt via -r
COPY requirements.txt requirements-dev.txt ./
RUN python -m pip install --no-cache-dir -r requirements-dev.txt && \
    # Remove setuptools from runtime image to fix GHSA-58pv-8j8x-9vj2 (jaraco.context vulnerability)
    # setuptools is only needed for build-time (pip install), not runtime
    python -m pip uninstall -y setuptools wheel || true

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
