# =============================================================================
# Multi-stage Dockerfile for Reverie Generative Agents
# =============================================================================
# This Dockerfile creates a containerized deployment of both the Django
# frontend server and the Reverie backend server.
#
# Build: docker build -t reverie:latest .
# Run: docker-compose up
# =============================================================================

FROM python:3.9-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Dependencies Stage
# =============================================================================
FROM base as dependencies

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn daphne channels channels-redis

# =============================================================================
# Frontend Server Stage
# =============================================================================
FROM dependencies as frontend

# Copy application code
COPY environment/frontend_server /app/frontend_server/
COPY reverie /app/reverie/

WORKDIR /app/frontend_server

# Create necessary directories
RUN mkdir -p storage temp_storage compressed_storage logs

# Collect static files
RUN python manage.py collectstatic --noinput --settings=frontend_server.settings.production || true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", \
     "--worker-class", "gthread", "--timeout", "120", \
     "frontend_server.wsgi:application"]

# =============================================================================
# Backend Server Stage
# =============================================================================
FROM dependencies as backend

# Copy application code
COPY reverie /app/reverie/
COPY environment/frontend_server/static_dirs /app/environment/frontend_server/static_dirs/
COPY environment/frontend_server/storage /app/environment/frontend_server/storage/
COPY environment/frontend_server/temp_storage /app/environment/frontend_server/temp_storage/

WORKDIR /app/reverie/backend_server

# Create directories
RUN mkdir -p ../../environment/frontend_server/storage \
    ../../environment/frontend_server/temp_storage \
    ../../environment/frontend_server/compressed_storage

# The backend server runs interactively, so we use a wrapper script
COPY docker/backend-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port for potential API
EXPOSE 8001

ENTRYPOINT ["/entrypoint.sh"]

# =============================================================================
# Development Stage (includes both servers)
# =============================================================================
FROM dependencies as development

# Copy all application code
COPY . /app/

WORKDIR /app

# Install development dependencies
RUN pip install ipython pytest pytest-django

# Create directories
RUN mkdir -p environment/frontend_server/storage \
    environment/frontend_server/temp_storage \
    environment/frontend_server/compressed_storage

EXPOSE 8000 8001

CMD ["bash"]
