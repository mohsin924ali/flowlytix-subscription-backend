"""
Diagnostic + Server Entry Point
Run migration diagnostics and then start server
"""
import os
import asyncio
import uvicorn
import subprocess
import sys
from migration_debug import main as run_diagnostics

async def run_diagnostics_and_start():
    """Run diagnostics and then start server."""
    print("🔍 Running migration diagnostics first...")
    
    try:
        # Run diagnostics
        await run_diagnostics()
        
        print("\n" + "="*60)
        print("🚀 Diagnostics complete. Starting server...")
        print("="*60)
        
        # Start server without migrations for now
        port = int(os.environ.get("PORT", 8000))
        uvicorn.run(
            "main_fixed:app",
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
        
    except Exception as e:
        print(f"❌ Diagnostic startup failed: {e}")
        # Still try to start server so Railway doesn't fail
        port = int(os.environ.get("PORT", 8000))
        uvicorn.run(
            "main_fixed:app",
            host="0.0.0.0",
            port=port,
            log_level="info"
        )

if __name__ == "__main__":
    asyncio.run(run_diagnostics_and_start()) 