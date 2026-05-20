# =============================================================================
# Menu Extraction System - Multi-Stage Dockerfile
# =============================================================================
# Stage 1: Builder - Install all dependencies and prepare the app
# Stage 2: Runtime - Lightweight production image
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Build-time labels
LABEL stage="builder"
LABEL maintainer="menu-extraction-system"

# Set environment variables for build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment for clean dependency isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --upgrade pip setuptools wheel

# Copy only requirements first for layer caching
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies with pip cache mount for faster repeated builds
# --mount=type=cache,target=/root/.cache/pip is a BuildKit feature
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /tmp/requirements.txt

# Install gunicorn for production WSGI serving
RUN pip install "gunicorn==21.2.0" "uvicorn[standard]==0.24.0"

# -----------------------------------------------------------------------------
# Stage 2: Runtime (Production)
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Runtime labels
LABEL org.opencontainers.image.title="Menu Extraction System"
LABEL org.opencontainers.image.description="AI-powered menu extraction with FastAPI + Streamlit"
LABEL org.opencontainers.image.version="2.0.0"

# Set runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app" \
    PATH="/opt/venv/bin:$PATH" \
    # Application defaults (can be overridden at runtime)
    APP_ENV="production" \
    LOG_LEVEL="info" \
    BACKEND_HOST="0.0.0.0" \
    BACKEND_PORT="8000" \
    FRONTEND_PORT="8501" \
    # Workers: 2*CPU+1 is the recommended formula for gunicorn
    WEB_CONCURRENCY="2" \
    MAX_WORKERS="4"

# Install runtime system dependencies
# poppler-utils: required for pdf2image (PDF → image conversion)
# libmagic1: required for python-magic (file type detection)
# tesseract-ocr: optional OCR backup engine
# libgl1: required for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    libmagic1 \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Create a non-root user for security
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Create application directories with proper permissions
RUN mkdir -p /app /app/outputs /app/logs /tmp/menu_extraction && \
    chown -R appuser:appgroup /app /tmp/menu_extraction

# Set working directory
WORKDIR /app

# Copy application code
# Copy in layers for better cache utilization
COPY --chown=appuser:appgroup backend/ ./backend/
COPY --chown=appuser:appgroup frontend/ ./frontend/
COPY --chown=appuser:appgroup docker/entrypoint.sh ./entrypoint.sh

# Make entrypoint executable
RUN chmod +x ./entrypoint.sh

# Switch to non-root user
USER appuser

# Expose application ports
# 8000: FastAPI backend
# 8501: Streamlit frontend
EXPOSE 8000 8501

# Health check - pings the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${BACKEND_PORT}/health || exit 1

# Use the entrypoint script for graceful startup/shutdown
ENTRYPOINT ["./entrypoint.sh"]

# Default command (can be overridden in docker-compose)
CMD ["backend"]

# -----------------------------------------------------------------------------
# Stage 3: Development (extends Runtime with dev tools)
# -----------------------------------------------------------------------------
FROM runtime AS development

# Switch back to root to install dev tools
USER root

# Install development utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    git \
    httpie \
    && rm -rf /var/lib/apt/lists/*

# Install dev Python packages
RUN pip install \
    pytest \
    pytest-asyncio \
    httpx \
    black \
    isort \
    flake8 \
    ipython

# Override for development
ENV APP_ENV="development" \
    LOG_LEVEL="debug"

# Switch back to appuser
USER appuser

# In development, override the CMD to use reload
CMD ["backend-dev"]
