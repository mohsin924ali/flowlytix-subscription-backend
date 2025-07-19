"""
No Migration Entry Point
Start FastAPI app without any database migrations
"""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting FastAPI without migrations on port {port}")
    print(f"DATABASE_URL: {os.environ.get('DATABASE_URL', 'Not set')[:50]}...")
    print(f"ALLOWED_ORIGINS: {os.environ.get('ALLOWED_ORIGINS', 'Not set')}")
    
    try:
        uvicorn.run(
            "main_fixed:app",
            host="0.0.0.0",
            port=port,
            log_level="info",
            reload=False
        )
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        exit(1) 