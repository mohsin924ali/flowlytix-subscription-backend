"""
Migration Debug Tool
Test database connection and migration steps individually
"""
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import text
import subprocess
import sys

async def test_basic_connection():
    """Test basic database connectivity."""
    print("🔍 Testing basic database connection...")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found")
        return False
        
    # Convert URL format
    if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    print(f"📍 Connecting to: {database_url[:50]}...")
    
    try:
        engine = create_async_engine(
            database_url,
            echo=False,
            pool_timeout=30,  # 30 second timeout
            pool_recycle=3600,
            connect_args={
                "server_settings": {
                    "application_name": "flowlytix_migration_debug",
                }
            }
        )
        
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Database connected successfully")
            print(f"📋 PostgreSQL version: {version}")
            
            # Test basic queries
            result = await conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"📋 Database name: {db_name}")
            
            # Check permissions
            result = await conn.execute(text("SELECT current_user"))
            user = result.scalar()
            print(f"📋 Connected as user: {user}")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def test_enum_creation():
    """Test if we can create ENUM types."""
    print("\n🔍 Testing ENUM creation...")
    
    database_url = os.getenv("DATABASE_URL")
    if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    try:
        engine = create_async_engine(database_url, echo=False)
        
        async with engine.connect() as conn:
            # Test creating a simple enum
            await conn.execute(text("DROP TYPE IF EXISTS test_enum CASCADE"))
            await conn.execute(text("CREATE TYPE test_enum AS ENUM ('test1', 'test2')"))
            await conn.execute(text("DROP TYPE test_enum CASCADE"))
            print("✅ ENUM creation works")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ ENUM creation failed: {e}")
        return False

async def test_table_creation():
    """Test if we can create a simple table."""
    print("\n🔍 Testing table creation...")
    
    database_url = os.getenv("DATABASE_URL")
    if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    try:
        engine = create_async_engine(database_url, echo=False)
        
        async with engine.connect() as conn:
            # Test creating a simple table
            await conn.execute(text("DROP TABLE IF EXISTS test_table CASCADE"))
            await conn.execute(text("""
                CREATE TABLE test_table (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            await conn.execute(text("DROP TABLE test_table CASCADE"))
            print("✅ Table creation works")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        return False

def test_alembic_env():
    """Test Alembic environment setup."""
    print("\n🔍 Testing Alembic environment...")
    
    try:
        from alembic.config import Config
        from alembic import command
        from alembic.env import get_database_url
        
        print("✅ Alembic imports successful")
        
        # Test config loading
        config = Config("alembic.ini")
        print("✅ Alembic config loaded")
        
        # Test URL retrieval
        url = get_database_url()
        print(f"✅ Alembic URL: {url[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Alembic environment failed: {e}")
        return False

async def test_migration_connection():
    """Test the specific connection method used by migrations."""
    print("\n🔍 Testing migration-style connection...")
    
    try:
        from alembic.env import get_database_url
        from sqlalchemy.ext.asyncio import async_engine_from_config
        from sqlalchemy import pool
        
        database_url = get_database_url()
        print(f"📍 Migration URL: {database_url[:50]}...")
        
        configuration = {
            "sqlalchemy.url": database_url,
            "sqlalchemy.echo": "false"
        }
        
        connectable = async_engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        
        async with connectable.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            print(f"✅ Migration-style connection successful: {result.scalar()}")
        
        await connectable.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Migration-style connection failed: {e}")
        return False

def run_single_migration():
    """Try to run just the first migration with timeout."""
    print("\n🔍 Testing single migration with timeout...")
    
    try:
        # Run with timeout
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "d165d8168f01"],
            timeout=60,  # 60 second timeout
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ First migration completed successfully")
            print(f"Output: {result.stdout}")
            return True
        else:
            print(f"❌ Migration failed with return code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Migration timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"❌ Migration test failed: {e}")
        return False

async def main():
    """Run all diagnostic tests."""
    print("🚀 Starting Migration Diagnostic Tool")
    print("=" * 60)
    
    tests = [
        ("Basic Connection", test_basic_connection()),
        ("ENUM Creation", test_enum_creation()),
        ("Table Creation", test_table_creation()),
        ("Migration Connection", test_migration_connection()),
    ]
    
    results = {}
    
    for test_name, test_coro in tests:
        try:
            result = await test_coro
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Synchronous tests
    results["Alembic Environment"] = test_alembic_env()
    results["Single Migration"] = run_single_migration()
    
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC RESULTS:")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
    
    # Recommendations
    print("\n" + "=" * 60)
    print("💡 RECOMMENDATIONS:")
    print("=" * 60)
    
    if not results["Basic Connection"]:
        print("❌ Fix database connection first")
    elif not results["ENUM Creation"]:
        print("❌ PostgreSQL ENUM permissions issue")
    elif not results["Migration Connection"]:
        print("❌ Alembic connection configuration issue")
    elif not results["Single Migration"]:
        print("❌ Migration script or timeout issue")
    else:
        print("✅ All tests passed - migration should work!")

if __name__ == "__main__":
    asyncio.run(main()) 