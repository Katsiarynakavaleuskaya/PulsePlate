# Multi-stage Dockerfile for PulsePlate
# Optimized for production with minimal image size and security

# Stage 1: Build stage
FROM python:3.13-slim AS builder

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
RUN python -m pip install --no-cache-dir --upgrade "pip==24.2" && \
    python -m pip install --no-cache-dir -r requirements.txt

# Stage 2: Production stage
FROM python:3.13-slim AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

# Install runtime dependencies only (curl removed - using Python for healthcheck)
RUN apt-get update && apt-get install -y \
    ca-certificates \
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
COPY --chown=pulseplate:pulseplate app.py main.py settings.py ./
COPY --chown=pulseplate:pulseplate alembic/ ./alembic/
COPY --chown=pulseplate:pulseplate alembic.ini ./

# Create necessary directories with proper permissions
RUN mkdir -p /app/cache/food_db /app/data /app/logs && \
    chown -R pulseplate:pulseplate /app/cache /app/data /app/logs

# Switch to non-root user
USER pulseplate

# Expose port
EXPOSE 8000

# Health check (using Python instead of curl to avoid CVE vulnerabilities)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

# Stage 3: Staging stage
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

# Stage 4: Development stage
FROM production AS development

# Switch back to root for development tools
USER root

# Install development dependencies
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# Install additional development tools
RUN apt-get update && apt-get install -y \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Switch back to non-root user
USER pulseplate

# Override command for development
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
