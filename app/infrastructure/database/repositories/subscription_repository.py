"""
Subscription Repository Implementation

SQLAlchemy-based repository implementations for subscription management.
Follows Instructions file standards for repository pattern and data access.
"""

import structlog
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities.subscription import (
    Subscription,
    Customer,
    Device,
    SubscriptionStatus,
    SubscriptionTier,
)
from app.domain.repositories.subscription_repository import (
    ISubscriptionRepository,
    ICustomerRepository,
    IDeviceRepository,
)
from app.infrastructure.database.models.subscription import (
    Subscription as SubscriptionModel,
    Customer as CustomerModel,
    Device as DeviceModel,
)
from app.core.exceptions import DatabaseException

logger = structlog.get_logger(__name__)


class SubscriptionRepository(ISubscriptionRepository):
    """
    SQLAlchemy implementation of subscription repository.
    
    Follows Instructions file standards for repository pattern and error handling.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _model_to_entity(self, model: SubscriptionModel) -> Subscription:
        """Convert SQLAlchemy model to domain entity."""
        devices = []
        
        # Safely handle devices relationship to avoid async issues
        # Default to empty list during creation to avoid lazy loading
        devices = []
        
        subscription = Subscription(
            id=model.id,
            customer_id=model.customer_id,
            license_key=model.license_key,
            tier=SubscriptionTier(model.tier),
            status=SubscriptionStatus(model.status),
            features=model.features,
            max_devices=model.max_devices,
            starts_at=model.starts_at,
            expires_at=model.expires_at,
            grace_period_days=model.grace_period_days,
            price=model.price,
            currency=model.currency,
            auto_renew=model.auto_renew,
            renewal_period_days=model.renewal_period_days,
            metadata=model.metadata_json,
            created_at=model.created_at,
            updated_at=model.updated_at,
            devices=devices,
        )
        
        # Note: Avoiding customer model access here to prevent lazy loading
        # Customer will be loaded separately when needed
        
        return subscription
    
    def _entity_to_model(self, entity: Subscription) -> SubscriptionModel:
        """Convert domain entity to SQLAlchemy model."""
        # Safely extract features
        features = {}
        if hasattr(entity, 'features') and entity.features:
            features = entity.features
        elif hasattr(entity, 'feature_set') and entity.feature_set:
            features = entity.feature_set.features
        
        # Safe enum conversion to avoid async issues
        tier_value = entity.tier
        if hasattr(tier_value, 'value'):
            tier_value = tier_value.value
        elif isinstance(tier_value, str):
            tier_value = tier_value
        else:
            tier_value = str(tier_value)
            
        status_value = entity.status  
        if hasattr(status_value, 'value'):
            status_value = status_value.value
        elif isinstance(status_value, str):
            status_value = status_value
        else:
            status_value = str(status_value)
        
        return SubscriptionModel(
            id=entity.id,
            customer_id=entity.customer_id,
            license_key=entity.license_key,
            tier=tier_value,
            status=status_value,
            features=features,
            max_devices=entity.max_devices,
            starts_at=entity.starts_at,
            expires_at=entity.expires_at,
            grace_period_days=entity.grace_period_days,
            price=entity.price,
            currency=entity.currency,
            auto_renew=entity.auto_renew,
            renewal_period_days=entity.renewal_period_days,
            metadata_json=entity.metadata,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
    
    def _device_model_to_entity(self, model: DeviceModel) -> Device:
        """Convert device model to entity."""
        return Device(
            id=model.id,
            subscription_id=model.subscription_id,
            device_id=model.device_id,
            device_name=model.device_name,
            device_type=model.device_type,
            fingerprint=model.fingerprint,
            os_name=model.os_name,
            os_version=model.os_version,
            app_version=model.app_version,
            is_active=model.is_active,
            last_seen_at=model.last_seen_at,
            metadata=model.metadata_json,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    async def create(self, subscription: Subscription) -> Subscription:
        """Create a new subscription."""
        try:
            logger.info("Starting subscription creation", 
                       subscription_id=str(subscription.id),
                       tier=str(subscription.tier),
                       tier_type=type(subscription.tier).__name__)
            
            logger.info("Converting entity to model...")
            model = self._entity_to_model(subscription)
            logger.info("Entity converted to model successfully")
            
            logger.info("Adding model to session...")
            self.session.add(model)
            logger.info("Model added to session")
            
            logger.info("Flushing session...")
            await self.session.flush()
            logger.info("Session flushed")
            
            logger.info("Refreshing model...")
            await self.session.refresh(model)
            logger.info("Model refreshed")
            
            logger.info(
                "Subscription created successfully",
                subscription_id=str(model.id),
                license_key=model.license_key[:8] + "***",
                tier=model.tier,
            )
            
            logger.info("Converting model back to entity...")
            result = self._model_to_entity(model)
            logger.info("Model converted to entity successfully")
            
            return result
            
        except Exception as e:
            logger.error("Failed to create subscription", 
                        error=str(e),
                        error_type=type(e).__name__)
            import traceback
            logger.error("Traceback", traceback=traceback.format_exc())
            raise DatabaseException(f"Failed to create subscription: {e}", "create")
    
    async def get_by_id(self, subscription_id: UUID) -> Optional[Subscription]:
        """Get subscription by ID."""
        try:
            stmt = (
                select(SubscriptionModel)
                .options(
                    selectinload(SubscriptionModel.devices),
                    selectinload(SubscriptionModel.customer)
                )
                .where(SubscriptionModel.id == subscription_id)
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            
            if model:
                return self._model_to_entity(model)
            return None
            
        except Exception as e:
            logger.error("Failed to get subscription by ID", subscription_id=str(subscription_id), error=str(e))
            raise DatabaseException(f"Failed to get subscription: {e}", "get_by_id")
    
    async def get_by_license_key(self, license_key: str) -> Optional[Subscription]:
        """Get subscription by license key."""
        try:
            stmt = (
                select(SubscriptionModel)
                .options(
                    selectinload(SubscriptionModel.devices),
                    selectinload(SubscriptionModel.customer)
                )
                .where(SubscriptionModel.license_key == license_key)
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            
            if model:
                logger.info(
                    "Subscription found by license key",
                    subscription_id=str(model.id),
                    license_key=license_key[:8] + "***",
                )
                return self._model_to_entity(model)
            
            logger.warning("Subscription not found", license_key=license_key[:8] + "***")
            return None
            
        except Exception as e:
            logger.error("Failed to get subscription by license key", license_key=license_key[:8] + "***", error=str(e))
            raise DatabaseException(f"Failed to get subscription: {e}", "get_by_license_key")
    
    async def get_by_customer_id(self, customer_id: UUID) -> List[Subscription]:
        """Get all subscriptions for a customer."""
        try:
            stmt = (
                select(SubscriptionModel)
                .options(selectinload(SubscriptionModel.devices))
                .where(SubscriptionModel.customer_id == customer_id)
                .order_by(SubscriptionModel.created_at.desc())
            )
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            
            return [self._model_to_entity(model) for model in models]
            
        except Exception as e:
            logger.error("Failed to get subscriptions by customer ID", customer_id=str(customer_id), error=str(e))
            raise DatabaseException(f"Failed to get subscriptions: {e}", "get_by_customer_id")
    
    async def update(self, subscription: Subscription) -> Subscription:
        """Update an existing subscription."""
        try:
            subscription.updated_at = datetime.now(timezone.utc)
            
            # Safe enum conversion
            tier_value = subscription.tier
            if hasattr(tier_value, 'value'):
                tier_value = tier_value.value
            elif isinstance(tier_value, str):
                tier_value = tier_value
            else:
                tier_value = str(tier_value)
                
            status_value = subscription.status
            if hasattr(status_value, 'value'):
                status_value = status_value.value
            elif isinstance(status_value, str):
                status_value = status_value
            else:
                status_value = str(status_value)
            
            # Safe features extraction
            features = {}
            if hasattr(subscription, 'features') and subscription.features:
                features = subscription.features
            elif hasattr(subscription, 'feature_set') and subscription.feature_set:
                features = subscription.feature_set.features
            
            stmt = (
                update(SubscriptionModel)
                .where(SubscriptionModel.id == subscription.id)
                .values(
                    tier=tier_value,
                    status=status_value,
                    features=features,
                    max_devices=subscription.max_devices,
                    starts_at=subscription.starts_at,
                    expires_at=subscription.expires_at,
                    grace_period_days=subscription.grace_period_days,
                    price=subscription.price,
                    currency=subscription.currency,
                    auto_renew=subscription.auto_renew,
                    renewal_period_days=subscription.renewal_period_days,
                    metadata_json=subscription.metadata,
                    updated_at=subscription.updated_at,
                )
            )
            await self.session.execute(stmt)
            
            # Get updated model
            updated_subscription = await self.get_by_id(subscription.id)
            if not updated_subscription:
                raise DatabaseException("Subscription not found after update", "update")
            
            logger.info(
                "Subscription updated",
                subscription_id=str(subscription.id),
                status=status_value,
            )
            
            return updated_subscription
            
        except Exception as e:
            logger.error("Failed to update subscription", subscription_id=str(subscription.id), error=str(e))
            raise DatabaseException(f"Failed to update subscription: {e}", "update")
    
    async def delete(self, subscription_id: UUID) -> bool:
        """Delete a subscription."""
        try:
            stmt = delete(SubscriptionModel).where(SubscriptionModel.id == subscription_id)
            result = await self.session.execute(stmt)
            
            deleted = result.rowcount > 0
            if deleted:
                logger.info("Subscription deleted", subscription_id=str(subscription_id))
            else:
                logger.warning("Subscription not found for deletion", subscription_id=str(subscription_id))
            
            return deleted
            
        except Exception as e:
            logger.error("Failed to delete subscription", subscription_id=str(subscription_id), error=str(e))
            raise DatabaseException(f"Failed to delete subscription: {e}", "delete")
    
    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Subscription]:
        """List subscriptions with pagination and filtering."""
        try:
            stmt = select(SubscriptionModel).options(
                selectinload(SubscriptionModel.devices),
                selectinload(SubscriptionModel.customer)
            )
            
            # Apply filters
            if filters:
                if "status" in filters:
                    stmt = stmt.where(SubscriptionModel.status == filters["status"])
                if "tier" in filters:
                    stmt = stmt.where(SubscriptionModel.tier == filters["tier"])
                if "customer_id" in filters:
                    stmt = stmt.where(SubscriptionModel.customer_id == filters["customer_id"])
                if "expires_before" in filters:
                    stmt = stmt.where(SubscriptionModel.expires_at <= filters["expires_before"])
                if "expires_after" in filters:
                    stmt = stmt.where(SubscriptionModel.expires_at >= filters["expires_after"])
            
            stmt = stmt.order_by(SubscriptionModel.created_at.desc()).limit(limit).offset(offset)
            
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            
            return [self._model_to_entity(model) for model in models]
            
        except Exception as e:
            logger.error("Failed to list subscriptions", error=str(e))
            raise DatabaseException(f"Failed to list subscriptions: {e}", "list_all")
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count subscriptions with optional filtering."""
        try:
            stmt = select(func.count(SubscriptionModel.id))
            
            # Apply filters
            if filters:
                if "status" in filters:
                    stmt = stmt.where(SubscriptionModel.status == filters["status"])
                if "tier" in filters:
                    stmt = stmt.where(SubscriptionModel.tier == filters["tier"])
                if "customer_id" in filters:
                    stmt = stmt.where(SubscriptionModel.customer_id == filters["customer_id"])
                if "expires_before" in filters:
                    stmt = stmt.where(SubscriptionModel.expires_at <= filters["expires_before"])
                if "expires_after" in filters:
                    stmt = stmt.where(SubscriptionModel.expires_at >= filters["expires_after"])
            
            result = await self.session.execute(stmt)
            return result.scalar() or 0
            
        except Exception as e:
            logger.error("Failed to count subscriptions", error=str(e))
            raise DatabaseException(f"Failed to count subscriptions: {e}", "count")
    
    async def get_expiring_soon(self, days: int = 7) -> List[Subscription]:
        """Get subscriptions expiring within specified days."""
        try:
            cutoff_date = datetime.now(timezone.utc) + timedelta(days=days)
            
            stmt = (
                select(SubscriptionModel)
                .options(selectinload(SubscriptionModel.devices))
                .where(
                    and_(
                        SubscriptionModel.expires_at <= cutoff_date,
                        SubscriptionModel.expires_at >= datetime.now(timezone.utc),
                        SubscriptionModel.status == SubscriptionStatus.ACTIVE,
                    )
                )
                .order_by(SubscriptionModel.expires_at.asc())
            )
            
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            
            return [self._model_to_entity(model) for model in models]
            
        except Exception as e:
            logger.error("Failed to get expiring subscriptions", error=str(e))
            raise DatabaseException(f"Failed to get expiring subscriptions: {e}", "get_expiring_soon")


class CustomerRepository(ICustomerRepository):
    """
    SQLAlchemy implementation of customer repository.
    
    Follows Instructions file standards for repository pattern.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _model_to_entity(self, model: CustomerModel) -> Customer:
        """Convert SQLAlchemy model to domain entity."""
        return Customer(
            id=model.id,
            name=model.name,
            email=model.email,
            company=model.company,
            phone=model.phone,
            address=model.address,
            metadata=model.metadata_json,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    def _entity_to_model(self, entity: Customer) -> CustomerModel:
        """Convert domain entity to SQLAlchemy model."""
        return CustomerModel(
            id=entity.id,
            name=entity.name,
            email=entity.email,
            company=entity.company,
            phone=entity.phone,
            address=entity.address,
            metadata_json=entity.metadata,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
    
    async def create(self, customer: Customer) -> Customer:
        """Create a new customer."""
        try:
            model = self._entity_to_model(customer)
            self.session.add(model)
            await self.session.flush()
            await self.session.refresh(model)
            
            logger.info("Customer created", customer_id=str(model.id), email=model.email)
            
            return self._model_to_entity(model)
            
        except Exception as e:
            logger.error("Failed to create customer", error=str(e))
            raise DatabaseException(f"Failed to create customer: {e}", "create")
    
    async def get_by_id(self, customer_id: UUID) -> Optional[Customer]:
        """Get customer by ID."""
        try:
            stmt = select(CustomerModel).where(CustomerModel.id == customer_id)
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            
            if model:
                return self._model_to_entity(model)
            return None
            
        except Exception as e:
            logger.error("Failed to get customer by ID", customer_id=str(customer_id), error=str(e))
            raise DatabaseException(f"Failed to get customer: {e}", "get_by_id")
    
    async def get_by_email(self, email: str) -> Optional[Customer]:
        """Get customer by email address."""
        try:
            stmt = select(CustomerModel).where(CustomerModel.email == email)
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            
            if model:
                return self._model_to_entity(model)
            return None
            
        except Exception as e:
            logger.error("Failed to get customer by email", email=email, error=str(e))
            raise DatabaseException(f"Failed to get customer: {e}", "get_by_email")
    
    async def update(self, customer: Customer) -> Customer:
        """Update an existing customer."""
        try:
            customer.updated_at = datetime.now(timezone.utc)
            
            stmt = (
                update(CustomerModel)
                .where(CustomerModel.id == customer.id)
                .values(
                    name=customer.name,
                    email=customer.email,
                    company=customer.company,
                    phone=customer.phone,
                    address=customer.address,
                    metadata_json=customer.metadata,
                    updated_at=customer.updated_at,
                )
            )
            await self.session.execute(stmt)
            
            # Get updated model
            updated_customer = await self.get_by_id(customer.id)
            if not updated_customer:
                raise DatabaseException("Customer not found after update", "update")
            
            logger.info("Customer updated", customer_id=str(customer.id))
            
            return updated_customer
            
        except Exception as e:
            logger.error("Failed to update customer", customer_id=str(customer.id), error=str(e))
            raise DatabaseException(f"Failed to update customer: {e}", "update")
    
    async def delete(self, customer_id: UUID) -> bool:
        """Delete a customer."""
        try:
            stmt = delete(CustomerModel).where(CustomerModel.id == customer_id)
            result = await self.session.execute(stmt)
            
            deleted = result.rowcount > 0
            if deleted:
                logger.info("Customer deleted", customer_id=str(customer_id))
            else:
                logger.warning("Customer not found for deletion", customer_id=str(customer_id))
            
            return deleted
            
        except Exception as e:
            logger.error("Failed to delete customer", customer_id=str(customer_id), error=str(e))
            raise DatabaseException(f"Failed to delete customer: {e}", "delete")
    
    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        search: Optional[str] = None
    ) -> List[Customer]:
        """List customers with pagination and search."""
        try:
            stmt = select(CustomerModel)
            
            # Apply search
            if search:
                search_pattern = f"%{search}%"
                stmt = stmt.where(
                    or_(
                        CustomerModel.name.ilike(search_pattern),
                        CustomerModel.email.ilike(search_pattern),
                        CustomerModel.company.ilike(search_pattern),
                    )
                )
            
            stmt = stmt.order_by(CustomerModel.created_at.desc()).limit(limit).offset(offset)
            
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            
            return [self._model_to_entity(model) for model in models]
            
        except Exception as e:
            logger.error("Failed to list customers", error=str(e))
            raise DatabaseException(f"Failed to list customers: {e}", "list_all")
    
    async def count(self, search: Optional[str] = None) -> int:
        """Count customers with optional search."""
        try:
            stmt = select(func.count(CustomerModel.id))
            
            # Apply search
            if search:
                search_pattern = f"%{search}%"
                stmt = stmt.where(
                    or_(
                        CustomerModel.name.ilike(search_pattern),
                        CustomerModel.email.ilike(search_pattern),
                        CustomerModel.company.ilike(search_pattern),
                    )
                )
            
            result = await self.session.execute(stmt)
            return result.scalar() or 0
            
        except Exception as e:
            logger.error("Failed to count customers", error=str(e))
            raise DatabaseException(f"Failed to count customers: {e}", "count")


class DeviceRepository(IDeviceRepository):
    """
    SQLAlchemy implementation of device repository.
    
    Follows Instructions file standards for repository pattern.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _model_to_entity(self, model: DeviceModel) -> Device:
        """Convert SQLAlchemy model to domain entity."""
        return Device(
            id=model.id,
            subscription_id=model.subscription_id,
            device_id=model.device_id,
            device_name=model.device_name,
            device_type=model.device_type,
            fingerprint=model.fingerprint,
            os_name=model.os_name,
            os_version=model.os_version,
            app_version=model.app_version,
            is_active=model.is_active,
            last_seen_at=model.last_seen_at,
            metadata=model.metadata_json,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    def _entity_to_model(self, entity: Device) -> DeviceModel:
        """Convert domain entity to SQLAlchemy model."""
        return DeviceModel(
            id=entity.id,
            subscription_id=entity.subscription_id,
            device_id=entity.device_id,
            device_name=entity.device_name,
            device_type=entity.device_type,
            fingerprint=entity.fingerprint,
            os_name=entity.os_name,
            os_version=entity.os_version,
            app_version=entity.app_version,
            is_active=entity.is_active,
            last_seen_at=entity.last_seen_at,
            metadata_json=entity.metadata,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
    
    async def create(self, device: Device) -> Device:
        """Create a new device."""
        try:
            model = self._entity_to_model(device)
            self.session.add(model)
            await self.session.flush()
            await self.session.refresh(model)
            
            logger.info(
                "Device created",
                device_id=model.device_id,
                subscription_id=str(model.subscription_id),
            )
            
            return self._model_to_entity(model)
            
        except Exception as e:
            logger.error("Failed to create device", error=str(e))
            raise DatabaseException(f"Failed to create device: {e}", "create")
    
    async def get_by_id(self, device_id: UUID) -> Optional[Device]:
        """Get device by ID."""
        try:
            stmt = select(DeviceModel).where(DeviceModel.id == device_id)
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            
            if model:
                return self._model_to_entity(model)
            return None
            
        except Exception as e:
            logger.error("Failed to get device by ID", device_id=str(device_id), error=str(e))
            raise DatabaseException(f"Failed to get device: {e}", "get_by_id")
    
    async def get_by_device_id(self, device_id: str, subscription_id: UUID) -> Optional[Device]:
        """Get device by device ID and subscription."""
        try:
            stmt = select(DeviceModel).where(
                and_(
                    DeviceModel.device_id == device_id,
                    DeviceModel.subscription_id == subscription_id,
                )
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            
            if model:
                return self._model_to_entity(model)
            return None
            
        except Exception as e:
            logger.error("Failed to get device by device ID", device_id=device_id, error=str(e))
            raise DatabaseException(f"Failed to get device: {e}", "get_by_device_id")
    
    async def get_by_subscription_id(self, subscription_id: UUID) -> List[Device]:
        """Get all devices for a subscription."""
        try:
            stmt = (
                select(DeviceModel)
                .where(DeviceModel.subscription_id == subscription_id)
                .order_by(DeviceModel.created_at.desc())
            )
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            
            return [self._model_to_entity(model) for model in models]
            
        except Exception as e:
            logger.error("Failed to get devices by subscription ID", subscription_id=str(subscription_id), error=str(e))
            raise DatabaseException(f"Failed to get devices: {e}", "get_by_subscription_id")
    
    async def update(self, device: Device) -> Device:
        """Update an existing device."""
        try:
            device.updated_at = datetime.now(timezone.utc)
            
            stmt = (
                update(DeviceModel)
                .where(DeviceModel.id == device.id)
                .values(
                    device_name=device.device_name,
                    device_type=device.device_type,
                    fingerprint=device.fingerprint,
                    os_name=device.os_name,
                    os_version=device.os_version,
                    app_version=device.app_version,
                    is_active=device.is_active,
                    last_seen_at=device.last_seen_at,
                    metadata_json=device.metadata,
                    updated_at=device.updated_at,
                )
            )
            await self.session.execute(stmt)
            
            # Get updated model
            updated_device = await self.get_by_id(device.id)
            if not updated_device:
                raise DatabaseException("Device not found after update", "update")
            
            logger.info("Device updated", device_id=device.device_id)
            
            return updated_device
            
        except Exception as e:
            logger.error("Failed to update device", device_id=device.device_id, error=str(e))
            raise DatabaseException(f"Failed to update device: {e}", "update")
    
    async def delete(self, device_id: UUID) -> bool:
        """Delete a device."""
        try:
            stmt = delete(DeviceModel).where(DeviceModel.id == device_id)
            result = await self.session.execute(stmt)
            
            deleted = result.rowcount > 0
            if deleted:
                logger.info("Device deleted", device_id=str(device_id))
            else:
                logger.warning("Device not found for deletion", device_id=str(device_id))
            
            return deleted
            
        except Exception as e:
            logger.error("Failed to delete device", device_id=str(device_id), error=str(e))
            raise DatabaseException(f"Failed to delete device: {e}", "delete")
    
    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Device]:
        """List devices with pagination and filtering."""
        try:
            stmt = select(DeviceModel)
            
            # Apply filters
            if filters:
                if "is_active" in filters:
                    stmt = stmt.where(DeviceModel.is_active == filters["is_active"])
                if "subscription_id" in filters:
                    stmt = stmt.where(DeviceModel.subscription_id == filters["subscription_id"])
                if "device_type" in filters:
                    stmt = stmt.where(DeviceModel.device_type == filters["device_type"])
            
            stmt = stmt.order_by(DeviceModel.created_at.desc()).limit(limit).offset(offset)
            
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            
            return [self._model_to_entity(model) for model in models]
            
        except Exception as e:
            logger.error("Failed to list devices", error=str(e))
            raise DatabaseException(f"Failed to list devices: {e}", "list_all")
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count devices with optional filtering."""
        try:
            stmt = select(func.count(DeviceModel.id))
            
            # Apply filters
            if filters:
                if "is_active" in filters:
                    stmt = stmt.where(DeviceModel.is_active == filters["is_active"])
                if "subscription_id" in filters:
                    stmt = stmt.where(DeviceModel.subscription_id == filters["subscription_id"])
                if "device_type" in filters:
                    stmt = stmt.where(DeviceModel.device_type == filters["device_type"])
            
            result = await self.session.execute(stmt)
            return result.scalar() or 0
            
        except Exception as e:
            logger.error("Failed to count devices", error=str(e))
            raise DatabaseException(f"Failed to count devices: {e}", "count")
    
    async def get_inactive_devices(self, days: int = 30) -> List[Device]:
        """Get devices that haven't been seen for specified days."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            stmt = (
                select(DeviceModel)
                .where(
                    and_(
                        DeviceModel.is_active == True,
                        or_(
                            DeviceModel.last_seen_at < cutoff_date,
                            DeviceModel.last_seen_at.is_(None),
                        ),
                    )
                )
                .order_by(DeviceModel.last_seen_at.asc())
            )
            
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            
            return [self._model_to_entity(model) for model in models]
            
        except Exception as e:
            logger.error("Failed to get inactive devices", error=str(e))
            raise DatabaseException(f"Failed to get inactive devices: {e}", "get_inactive_devices") 