"""
Subscription Creation Debug
Test each step of subscription creation to isolate the issue
"""
import os
import asyncio
from uuid import UUID
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.domain.entities.subscription import SubscriptionTier
from app.domain.services.subscription_service import SubscriptionService
from app.infrastructure.database.repositories.subscription_repository import (
    SubscriptionRepository, CustomerRepository, DeviceRepository
)
from app.core.security import SecurityManager

async def test_subscription_creation():
    """Test subscription creation step by step."""
    print("🔍 Testing subscription creation process...")
    
    # Setup database connection
    database_url = os.getenv("DATABASE_URL")
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine)
    
    try:
        async with session_factory() as session:
            print("✅ Database session created")
            
            # Setup repositories
            subscription_repo = SubscriptionRepository(session)
            customer_repo = CustomerRepository(session)
            device_repo = DeviceRepository(session)
            security_manager = SecurityManager()
            
            print("✅ Repositories created")
            
            # Setup service
            service = SubscriptionService(
                subscription_repo, customer_repo, device_repo, security_manager
            )
            print("✅ Service created")
            
            # Test customer exists
            customer_id = UUID("a921cc62-d3c7-489c-bf0d-962d777d68b5")
            customer = await customer_repo.get_by_id(customer_id)
            if not customer:
                print("❌ Customer not found")
                return
            print(f"✅ Customer found: {customer.name}")
            
            # Test enum creation
            try:
                tier = SubscriptionTier.BASIC
                print(f"✅ Tier enum created: {tier}")
            except Exception as e:
                print(f"❌ Tier enum error: {e}")
                return
            
            # Test subscription creation
            try:
                print("🔄 Creating subscription...")
                subscription = await service.create_subscription(
                    customer_id=customer_id,
                    tier=tier,
                    duration_days=30,
                    max_devices=2,
                    price=29.99,
                    currency="USD"
                )
                print(f"✅ Subscription created: {subscription.id}")
                print(f"📋 License key: {subscription.license_key[:8]}...")
                
                # Commit the transaction
                await session.commit()
                print("✅ Transaction committed")
                
                return subscription
                
            except Exception as e:
                print(f"❌ Subscription creation failed: {e}")
                print(f"Error type: {type(e).__name__}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                return None
                
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return None
    finally:
        await engine.dispose()

if __name__ == "__main__":
    result = asyncio.run(test_subscription_creation())
    if result:
        print("🎉 Test completed successfully!")
    else:
        print("❌ Test failed") 