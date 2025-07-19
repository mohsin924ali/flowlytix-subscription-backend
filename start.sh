#!/bin/bash

set -e  # Exit on any error

echo "🚀 Starting Flowlytix Subscription Server"

# Debug environment
echo "Environment variables:"
echo "PORT: ${PORT:-8000}"
echo "DATABASE_URL: ${DATABASE_URL:0:20}..."
echo "ENVIRONMENT: ${ENVIRONMENT:-development}"

# Run database migrations
echo "Running database migrations..."
python -m alembic upgrade head
echo "✅ Migrations completed successfully"

# Start the server
echo "Starting server on port ${PORT:-8000}..."
exec uvicorn main_fixed:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info 