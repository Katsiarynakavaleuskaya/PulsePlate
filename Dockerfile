# Multi-stage Dockerfile for PulsePlate
# Optimized for production with minimal image size and security
# Security: Uses pinned base image python:3.13-slim-bookworm@sha256:... for CVE-2025-62813 mitigation
# Note: LZ4 is used by Python packages for compression; service runs in isolated containers with network restrictions
# CI/CD: Container vulnerability scanning (Trivy) is configured to detect vulnerable libraries

# Stage 1: Build stage
# Using bookworm variant for better security posture and package availability
FROM python:3.13-slim-bookworm@sha256:4c9fe962f6ce46ecf3633a7e9d0a9fb7f5622121ee00d628eff206da024147c9 AS builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt requirements-dev.txt ./

# Create virtual environment
RUN python -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_PYTHON_VERSION_WARNING=1

# Install Python dependencies
RUN python -m pip install --no-cache-dir --upgrade "pip==24.2" && \
    python -m pip install --no-cache-dir -r requirements.txt

# Stage 2: Production stage
# Using same pinned bookworm variant for consistency and security
FROM python:3.13-slim-bookworm@sha256:4c9fe962f6ce46ecf3633a7e9d0a9fb7f5622121ee00d628eff206da024147c9 AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd -r pulseplate && useradd -r -g pulseplate pulseplate

# Create app directory
WORKDIR /app

# Copy application code
COPY --chown=pulseplate:pulseplate . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/cache /app/data /app/logs && \
    chown -R pulseplate:pulseplate /app/cache /app/data /app/logs

# Switch to non-root user
USER pulseplate

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

# Stage 3: Development stage
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
