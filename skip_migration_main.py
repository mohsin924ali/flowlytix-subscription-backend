"""
Skip Migration Entry Point
Start app without migrations to test CORS and basic functionality
"""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting app WITHOUT migrations on port {port}")
    print("This is a temporary fix to test CORS functionality")
    print(f"ALLOWED_ORIGINS: {os.environ.get('ALLOWED_ORIGINS', 'Not set')}")
    
    uvicorn.run(
        "main_fixed:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    ) 