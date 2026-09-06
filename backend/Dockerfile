# ThermalWatch Backend Dockerfile
# Production-ready Python FastAPI container with XGBoost support

FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required for OpenMP (XGBoost) and healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and group
RUN groupadd -r thermalwatch && useradd -r -g thermalwatch -d /app thermalwatch

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source and production model
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

# Ensure correct file permissions for non-root user
RUN chown -R thermalwatch:thermalwatch /app

USER thermalwatch

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
