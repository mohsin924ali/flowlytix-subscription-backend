#!/bin/bash

echo "🚀 Starting Flowlytix Subscription Server"

# Run database migrations
echo "Running database migrations..."
python -m alembic upgrade head

# Start the server
echo "Starting server..."
exec uvicorn main_fixed:app --host 0.0.0.0 --port ${PORT:-8000} 