# Use official Python runtime as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements/base.txt requirements/prod.txt ./
RUN pip install --no-cache-dir -r prod.txt

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r flowlytix && useradd -r -g flowlytix flowlytix

# Create necessary directories
RUN mkdir -p keys logs && \
    chown -R flowlytix:flowlytix /app

# Switch to non-root user
USER flowlytix

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application (temporarily skip migrations to test CORS)
CMD ["python", "skip_migration_main.py"] 