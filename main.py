"""
Railway Entry Point
Simple entry point for Railway deployment
"""
import os
import subprocess
import sys


def run_migrations():
    """Run database migrations before starting the server."""
    print("🔄 Running database migrations...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Migrations completed successfully")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("❌ Migration failed:")
        print(e.stderr)
        sys.exit(1)


def start_server():
    """Start the FastAPI server."""
    port = os.environ.get("PORT", "8000")
    print(f"🚀 Starting server on port {port}...")
    
    cmd = [
        "uvicorn", 
        "main_fixed:app", 
        "--host", "0.0.0.0", 
        "--port", port,
        "--log-level", "info"
    ]
    
    subprocess.run(cmd)


if __name__ == "__main__":
    print("🚀 Starting Flowlytix Subscription Server")
    print(f"Environment: {os.environ.get('ENVIRONMENT', 'development')}")
    print(f"Port: {os.environ.get('PORT', '8000')}")
    
    # Run migrations first
    run_migrations()
    
    # Start server
    start_server() 