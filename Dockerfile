# Multi-stage Dockerfile for PulsePlate
# Optimized for production with minimal image size and security
# Security: Updates system packages to fix CVE-2025-62813 (liblz4-1 vulnerability)
# Note: CVE-2025-62813 is a very recent vulnerability (2025) and fix may not be available in Debian repos yet
# We update all packages to get the latest available security patches

# Stage 1: Build stage
FROM python:3.13-slim AS builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Install system dependencies for building and update security packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && apt-get upgrade -y \
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

# Install runtime dependencies and update security packages
RUN apt-get update && apt-get install -y \
    curl \
    && apt-get upgrade -y \
    && apt-get install -y liblz4-1 \
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

# Install additional development tools and update security packages
RUN apt-get update && apt-get install -y \
    git \
    vim \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Switch back to non-root user
USER pulseplate

# Override command for development
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
