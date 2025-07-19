"""
Debug Migration Script
Test database connection and migration process
"""
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

async def test_database_connection():
    """Test the database connection directly."""
    database_url = os.getenv("DATABASE_URL")
    print(f"Original DATABASE_URL: {database_url}")
    
    # Convert URL if needed
    if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    print(f"Converted DATABASE_URL: {database_url}")
    
    try:
        print("Creating async engine...")
        engine = create_async_engine(database_url)
        
        print("Testing connection...")
        async with engine.connect() as conn:
            result = await conn.execute("SELECT 1")
            print(f"✅ Database connection successful: {result.scalar()}")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_alembic_config():
    """Test Alembic configuration."""
    try:
        print("Testing Alembic imports...")
        from alembic import command
        from alembic.config import Config
        print("✅ Alembic imports successful")
        
        print("Testing Alembic config...")
        alembic_cfg = Config("alembic.ini")
        
        # Get the database URL that Alembic would use
        from alembic.env import get_database_url
        url = get_database_url()
        print(f"Alembic would use URL: {url}")
        
        return True
    except Exception as e:
        print(f"❌ Alembic config failed: {e}")
        return False

async def main():
    """Main debug function."""
    print("🐞 Database Connection Debug")
    print("=" * 50)
    
    # Test basic connection
    connection_ok = await test_database_connection()
    
    print("\n" + "=" * 50)
    
    # Test Alembic config
    alembic_ok = test_alembic_config()
    
    print("\n" + "=" * 50)
    print(f"Database Connection: {'✅' if connection_ok else '❌'}")
    print(f"Alembic Config: {'✅' if alembic_ok else '❌'}")

if __name__ == "__main__":
    asyncio.run(main()) 