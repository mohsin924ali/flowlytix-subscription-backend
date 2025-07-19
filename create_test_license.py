#!/usr/bin/env python3
"""
Script to create a test license key for development and testing.
"""

import asyncio
import asyncpg
from datetime import datetime, timedelta
import uuid

async def create_test_license():
    """Create a test license key in the database."""
    
    # Database connection
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        database="flowlytix_subscriptions",
        user="flowlytix",
        password="flowlytix_password"
    )
    
    try:
        # Create test customer if not exists
        customer_id = str(uuid.uuid4())
        existing_customer = await conn.fetchrow("SELECT id FROM customers WHERE email = $1", "test@example.com")
        
        if existing_customer:
            customer_id = str(existing_customer['id'])
            print(f"Using existing customer: {customer_id}")
        else:
            await conn.execute("""
                INSERT INTO customers (id, name, email, company, phone, address, metadata_json, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, customer_id, "Test Customer", "test@example.com", "Test Company", "+1234567890", 
                "123 Test Street", "{}", datetime.now(), datetime.now())
            print(f"Created new customer: {customer_id}")
        
        # Create test subscription
        subscription_id = str(uuid.uuid4())
        starts_at = datetime.now()
        expires_at = starts_at + timedelta(days=365)
        
        await conn.execute("""
            INSERT INTO subscriptions (
                id, customer_id, license_key, tier, status, features, max_devices,
                starts_at, expires_at, grace_period_days, price, currency, auto_renew,
                metadata_json, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
            )
            ON CONFLICT (license_key) DO UPDATE SET
                tier = EXCLUDED.tier,
                status = EXCLUDED.status,
                expires_at = EXCLUDED.expires_at,
                updated_at = EXCLUDED.updated_at
        """, subscription_id, customer_id, "TEST-1234-5678-9012", "basic", "active", 
            '{"analytics": true, "reports": true}', 1, starts_at, expires_at, 7, 0.0, 
            "USD", False, '{"test": true}', datetime.now(), datetime.now())
        
        print("✅ Test license key created successfully!")
        print(f"   License Key: TEST-1234-5678-9012")
        print(f"   Customer ID: {customer_id}")
        print(f"   Subscription ID: {subscription_id}")
        print(f"   Tier: basic")
        print(f"   Status: active")
        print(f"   Expires: {expires_at}")
        
    except Exception as e:
        print(f"❌ Error creating test license: {e}")
    
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_test_license()) 