"""
Manual Migration Script
Create database tables step by step to avoid hanging migrations
"""
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def create_database_tables():
    """Create database tables manually."""
    database_url = os.getenv("DATABASE_URL")
    
    # Convert URL format
    if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    print(f"🔄 Connecting to database...")
    
    engine = create_async_engine(database_url, echo=True)
    
    try:
        async with engine.connect() as conn:
            print("✅ Connected to database")
            
            # Create ENUM types first
            print("🔄 Creating ENUM types...")
            
            await conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE subscription_tier AS ENUM ('basic', 'professional', 'enterprise', 'trial');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            await conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE subscription_status AS ENUM ('active', 'expired', 'suspended', 'cancelled', 'pending');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            await conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE payment_method AS ENUM ('cash', 'card', 'bank_transfer', 'paypal', 'stripe', 'manual', 'other');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            await conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE payment_type AS ENUM ('subscription', 'one_time', 'refund', 'adjustment', 'penalty', 'bonus');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            await conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE payment_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            print("✅ ENUM types created")
            
            # Create customers table
            print("🔄 Creating customers table...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS customers (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    company VARCHAR(255),
                    phone VARCHAR(50),
                    address TEXT,
                    metadata_json JSON,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                )
            """))
            
            # Create indexes for customers
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_customers_company ON customers(company)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_customers_created_at ON customers(created_at)"))
            
            print("✅ Customers table created")
            
            # Create subscriptions table
            print("🔄 Creating subscriptions table...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                    license_key VARCHAR(255) NOT NULL UNIQUE,
                    tier subscription_tier NOT NULL,
                    status subscription_status NOT NULL,
                    features JSON NOT NULL,
                    max_devices INTEGER NOT NULL,
                    starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE,
                    grace_period_days INTEGER NOT NULL DEFAULT 0,
                    price FLOAT,
                    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
                    auto_renew BOOLEAN NOT NULL DEFAULT false,
                    renewal_period_days INTEGER,
                    metadata_json JSON,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                )
            """))
            
            # Create indexes for subscriptions
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_subscriptions_customer_id ON subscriptions(customer_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_subscriptions_license_key ON subscriptions(license_key)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_subscriptions_expires_at ON subscriptions(expires_at)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_subscriptions_created_at ON subscriptions(created_at)"))
            
            print("✅ Subscriptions table created")
            
            # Create devices table
            print("🔄 Creating devices table...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS devices (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
                    device_id VARCHAR(255) NOT NULL,
                    device_name VARCHAR(255),
                    device_type VARCHAR(100),
                    platform VARCHAR(100),
                    os_version VARCHAR(100),
                    app_version VARCHAR(100),
                    last_seen_at TIMESTAMP WITH TIME ZONE,
                    is_active BOOLEAN NOT NULL DEFAULT true,
                    fingerprint VARCHAR(255),
                    metadata_json JSON,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    UNIQUE(subscription_id, device_id)
                )
            """))
            
            # Create indexes for devices
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_devices_subscription_id ON devices(subscription_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_devices_device_id ON devices(device_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_devices_last_seen_at ON devices(last_seen_at)"))
            
            print("✅ Devices table created")
            
            # Create payments table
            print("🔄 Creating payments table...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS payments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
                    admin_user_id UUID,
                    amount FLOAT NOT NULL CHECK (amount != 0),
                    currency VARCHAR(3) NOT NULL DEFAULT 'USD' CHECK (currency ~ '^[A-Z]{3}$'),
                    payment_method payment_method NOT NULL,
                    payment_type payment_type NOT NULL,
                    status payment_status NOT NULL DEFAULT 'pending',
                    reference_id VARCHAR(255),
                    description TEXT,
                    notes TEXT,
                    metadata_json JSON,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    processed_at TIMESTAMP WITH TIME ZONE,
                    CHECK (processed_at IS NULL OR processed_at >= created_at),
                    CHECK (updated_at >= created_at)
                )
            """))
            
            # Create indexes for payments
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_payments_subscription_id ON payments(subscription_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at)"))
            
            print("✅ Payments table created")
            
            # Create alembic version table to mark migrations as complete
            print("🔄 Creating alembic version table...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL PRIMARY KEY
                )
            """))
            
            # Mark both migrations as complete
            await conn.execute(text("DELETE FROM alembic_version"))
            await conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('12aeace128ec')"))
            
            print("✅ Alembic version table updated")
            
            # Commit the transaction
            await conn.commit()
            
            print("\n🎉 ALL TABLES CREATED SUCCESSFULLY!")
            print("✅ Database is now ready for use")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_database_tables()) 