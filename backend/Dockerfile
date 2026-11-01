# ==============================================================================
# EVIDENTIA-AI PRODUCTION BACKEND DOCKERFILE
# Multi-stage lightweight secure container image for FastAPI ASGI production service
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered terminal logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    ENVIRONMENT=production

WORKDIR /app

# Install system dependencies (curl for container orchestrator health checks, libpq-dev for PostgreSQL, ffmpeg for audio, tesseract-ocr for OCR)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    ffmpeg \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create directory for uploads and ensure proper access permissions
RUN mkdir -p uploads && \
    chmod 755 uploads && \
    chmod +x start.sh

# Create non-privileged user for secure container execution
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose production listening port
EXPOSE 8000

# Container Host Health Check (used by Docker, Kubernetes, AWS ECS, GCP Cloud Run)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production entrypoint starting background worker and ASGI server
CMD ["./start.sh"]

