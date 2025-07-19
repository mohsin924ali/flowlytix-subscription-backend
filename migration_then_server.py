"""
Migration Then Server
Run manual migration first, then start the server
"""
import os
import asyncio
import uvicorn
from manual_migration import create_database_tables

async def run_migration_then_server():
    """Run manual migration and then start server."""
    print("🔄 Running manual database migration...")
    
    try:
        # Run manual migration
        await create_database_tables()
        print("✅ Manual migration completed successfully!")
        
    except Exception as e:
        print(f"⚠️ Migration failed, but starting server anyway: {e}")
        # Continue to start server even if migration fails
    
    print("\n🚀 Starting server...")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main_fixed:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    asyncio.run(run_migration_then_server()) 