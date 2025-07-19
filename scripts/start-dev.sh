#!/bin/bash
# Development startup script for Flowlytix Subscription Server

set -e

echo "🚀 Starting Flowlytix Subscription Server Development Environment"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_warning "Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_status "Installing dependencies..."
pip install -r requirements/dev.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Please create one based on .env.example"
    print_warning "For now, using default development configuration"
fi

# Check if database is running
print_status "Checking database connection..."
if ! pg_isready -h localhost -p 5432 -U flowlytix 2>/dev/null; then
    print_warning "PostgreSQL not running. Starting with Docker Compose..."
    docker-compose up -d db redis
    
    # Wait for database to be ready
    print_status "Waiting for database to be ready..."
    sleep 10
    
    # Run migrations
    print_status "Running database migrations..."
    alembic upgrade head
fi

# Run tests
print_status "Running tests..."
python -m pytest app/tests/ -v --tb=short

# Start the development server
print_status "Starting development server..."
print_status "Server will be available at: http://localhost:8000"
print_status "API documentation at: http://localhost:8000/docs"
print_status "Health check at: http://localhost:8000/health"

# Set development environment variables
export ENVIRONMENT=development
export DEBUG=true
export RELOAD=true

# Start the server
python main.py 