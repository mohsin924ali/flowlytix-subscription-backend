"""
Subscription Service Layer

Business logic for subscription management, license activation, and validation.
Follows Instructions file standards for service layer and business logic separation.
"""

import structlog
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

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
from app.core.exceptions import (
    SubscriptionExpiredException,
    DeviceLimitExceededException,
    LicenseKeyInvalidException,
    SubscriptionNotFoundException,
    CustomerNotFoundException,
    DeviceNotFoundException,
)
from app.core.security import SecurityManager

logger = structlog.get_logger(__name__)


class SubscriptionService:
    """
    Subscription business logic service.
    
    Handles subscription management, validation, and business rules.
    Follows Instructions file standards for service layer design.
    """
    
    def __init__(
        self,
        subscription_repo: ISubscriptionRepository,
        customer_repo: ICustomerRepository,
        device_repo: IDeviceRepository,
        security_manager: SecurityManager,
    ):
        self.subscription_repo = subscription_repo
        self.customer_repo = customer_repo
        self.device_repo = device_repo
        self.security_manager = security_manager
    
    async def create_subscription(
        self,
        customer_id: UUID,
        tier: SubscriptionTier,
        duration_days: int,
        max_devices: int = 1,
        custom_features: Optional[Dict[str, Any]] = None,
        price: Optional[float] = None,
        currency: str = "USD",
    ) -> Subscription:
        """
        Create a new subscription for a customer.
        
        Args:
            customer_id: Customer identifier
            tier: Subscription tier
            duration_days: Subscription duration in days
            max_devices: Maximum number of devices allowed
            custom_features: Optional custom feature overrides
            price: Optional subscription price
            currency: Currency code
            
        Returns:
            Created subscription entity
            
        Raises:
            CustomerNotFoundException: If customer doesn't exist
        """
        # Verify customer exists
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise CustomerNotFoundException(customer_id=str(customer_id))
        
        # Generate unique license key
        license_key = self.security_manager.generate_license_key()
        
        # Calculate subscription dates
        starts_at = datetime.now(timezone.utc)
        expires_at = starts_at + timedelta(days=duration_days)
        
        # Create subscription entity
        subscription = Subscription(
            id=uuid4(),
            customer_id=customer_id,
            license_key=license_key,
            tier=tier,
            status=SubscriptionStatus.ACTIVE,
            features=custom_features,
            max_devices=max_devices,
            starts_at=starts_at,
            expires_at=expires_at,
            price=price,
            currency=currency,
        )
        
        # Save to repository
        created_subscription = await self.subscription_repo.create(subscription)
        
        logger.info(
            "Subscription created",
            subscription_id=str(created_subscription.id),
            customer_id=str(customer_id),
            tier=tier.value,
            license_key=license_key[:8] + "***",
        )
        
        return created_subscription
    
    async def activate_license(
        self,
        license_key: str,
        device_id: str,
        device_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Activate a license on a device.
        
        Args:
            license_key: License key to activate
            device_id: Unique device identifier
            device_info: Optional device information
            
        Returns:
            Dictionary containing activation result and JWT token
            
        Raises:
            LicenseKeyInvalidException: If license key is invalid
            SubscriptionExpiredException: If subscription is expired
            DeviceLimitExceededException: If device limit is exceeded
        """
        # Get subscription by license key
        subscription = await self.subscription_repo.get_by_license_key(license_key)
        if not subscription:
            logger.warning("Invalid license key", license_key=license_key[:8] + "***")
            raise LicenseKeyInvalidException(reason="License key not found")
        
        # Validate subscription for activation
        validation_result = subscription.validate_for_activation(device_id)
        
        if validation_result["action"] == "can_activate":
            # Create new device
            device = Device(
                id=uuid4(),
                subscription_id=subscription.id,
                device_id=device_id,
                device_name=device_info.get("device_name") if device_info else None,
                device_type=device_info.get("device_type") if device_info else None,
                fingerprint=device_info.get("fingerprint") if device_info else None,
                os_name=device_info.get("os_name") if device_info else None,
                os_version=device_info.get("os_version") if device_info else None,
                app_version=device_info.get("app_version") if device_info else None,
                last_seen_at=datetime.now(timezone.utc),
            )
            
            # Save device
            created_device = await self.device_repo.create(device)
            
            # Add device to subscription
            subscription.add_device(created_device)
            await self.subscription_repo.update(subscription)
            
            validation_result["device"] = created_device
        
        elif validation_result["action"] == "reactivated":
            # Update last seen for reactivated device
            device = validation_result["device"]
            device.update_last_seen()
            await self.device_repo.update(device)
        
        # Generate JWT token
        token_payload = subscription.to_token_payload(device_id)
        token = self.security_manager.generate_subscription_token(token_payload)
        
        logger.info(
            "License activated",
            subscription_id=str(subscription.id),
            device_id=device_id,
            action=validation_result["action"],
        )
        
        return {
            "token": token,
            "subscription": subscription,
            "device": validation_result["device"],
            "action": validation_result["action"],
            "message": validation_result["message"],
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
        }
    
    async def validate_license(
        self,
        license_key: str,
        device_id: str,
        update_last_seen: bool = True,
    ) -> Dict[str, Any]:
        """
        Validate a license for a specific device.
        
        Args:
            license_key: License key to validate
            device_id: Device identifier
            update_last_seen: Whether to update device last_seen timestamp
            
        Returns:
            Dictionary containing validation result
            
        Raises:
            LicenseKeyInvalidException: If license key is invalid
        """
        # Get subscription by license key
        subscription = await self.subscription_repo.get_by_license_key(license_key)
        if not subscription:
            raise LicenseKeyInvalidException(reason="License key not found")
        
        # Check if device exists for this subscription
        device = subscription.get_device(device_id)
        if not device or not device.is_active:
            return {
                "valid": False,
                "reason": "device_not_activated",
                "message": "Device not activated for this subscription",
            }
        
        # Check if subscription is active
        if not subscription.is_active():
            status = "expired" if subscription.is_expired() else "inactive"
            return {
                "valid": False,
                "reason": status,
                "message": f"Subscription is {status}",
                "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            }
        
        # Update device last seen if requested
        if update_last_seen:
            device.update_last_seen()
            await self.device_repo.update(device)
        
        # Check if in grace period
        in_grace_period = subscription.is_in_grace_period()
        days_until_expiry = subscription.days_until_expiry()
        
        return {
            "valid": True,
            "subscription": subscription,
            "device": device,
            "in_grace_period": in_grace_period,
            "days_until_expiry": days_until_expiry,
            "features": subscription.feature_set.features,
        }
    
    async def deactivate_device(
        self,
        license_key: str,
        device_id: str,
    ) -> bool:
        """
        Deactivate a device from a subscription.
        
        Args:
            license_key: License key
            device_id: Device identifier
            
        Returns:
            True if device was deactivated, False if not found
            
        Raises:
            LicenseKeyInvalidException: If license key is invalid
        """
        # Get subscription by license key
        subscription = await self.subscription_repo.get_by_license_key(license_key)
        if not subscription:
            raise LicenseKeyInvalidException(reason="License key not found")
        
        # Remove device from subscription
        removed = subscription.remove_device(device_id)
        
        if removed:
            await self.subscription_repo.update(subscription)
            logger.info(
                "Device deactivated",
                subscription_id=str(subscription.id),
                device_id=device_id,
            )
        
        return removed
    
    async def extend_subscription(
        self,
        subscription_id: UUID,
        days: int,
    ) -> Subscription:
        """
        Extend a subscription by specified days.
        
        Args:
            subscription_id: Subscription identifier
            days: Number of days to extend
            
        Returns:
            Updated subscription entity
            
        Raises:
            SubscriptionNotFoundException: If subscription doesn't exist
        """
        subscription = await self.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise SubscriptionNotFoundException(subscription_id=str(subscription_id))
        
        subscription.extend_expiry(days)
        updated_subscription = await self.subscription_repo.update(subscription)
        
        logger.info(
            "Subscription extended",
            subscription_id=str(subscription_id),
            days=days,
            new_expiry=updated_subscription.expires_at.isoformat() if updated_subscription.expires_at else None,
        )
        
        return updated_subscription
    
    async def update_subscription_tier(
        self,
        subscription_id: UUID,
        new_tier: SubscriptionTier,
        custom_features: Optional[Dict[str, Any]] = None,
    ) -> Subscription:
        """
        Update subscription tier and features.
        
        Args:
            subscription_id: Subscription identifier
            new_tier: New subscription tier
            custom_features: Optional custom feature overrides
            
        Returns:
            Updated subscription entity
            
        Raises:
            SubscriptionNotFoundException: If subscription doesn't exist
        """
        subscription = await self.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise SubscriptionNotFoundException(subscription_id=str(subscription_id))
        
        old_tier = subscription.tier
        subscription.update_tier(new_tier, custom_features)
        updated_subscription = await self.subscription_repo.update(subscription)
        
        logger.info(
            "Subscription tier updated",
            subscription_id=str(subscription_id),
            old_tier=old_tier.value,
            new_tier=new_tier.value,
        )
        
        return updated_subscription
    
    async def suspend_subscription(
        self,
        subscription_id: UUID,
    ) -> Subscription:
        """
        Suspend a subscription.
        
        Args:
            subscription_id: Subscription identifier
            
        Returns:
            Updated subscription entity
            
        Raises:
            SubscriptionNotFoundException: If subscription doesn't exist
        """
        subscription = await self.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise SubscriptionNotFoundException(subscription_id=str(subscription_id))
        
        subscription.suspend()
        updated_subscription = await self.subscription_repo.update(subscription)
        
        logger.info("Subscription suspended", subscription_id=str(subscription_id))
        
        return updated_subscription
    
    async def cancel_subscription(
        self,
        subscription_id: UUID,
    ) -> Subscription:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Subscription identifier
            
        Returns:
            Updated subscription entity
            
        Raises:
            SubscriptionNotFoundException: If subscription doesn't exist
        """
        subscription = await self.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise SubscriptionNotFoundException(subscription_id=str(subscription_id))
        
        subscription.cancel()
        updated_subscription = await self.subscription_repo.update(subscription)
        
        # Update all devices in database
        for device in subscription.devices:
            await self.device_repo.update(device)
        
        logger.info("Subscription cancelled", subscription_id=str(subscription_id))
        
        return updated_subscription
    
    async def resume_subscription(
        self,
        subscription_id: UUID,
    ) -> Subscription:
        """
        Resume a suspended or cancelled subscription.
        
        Args:
            subscription_id: Subscription identifier
            
        Returns:
            Updated subscription entity
            
        Raises:
            SubscriptionNotFoundException: If subscription doesn't exist
        """
        subscription = await self.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise SubscriptionNotFoundException(subscription_id=str(subscription_id))
        
        # Resume the subscription (sets status back to active)
        subscription.resume()
        updated_subscription = await self.subscription_repo.update(subscription)
        
        logger.info("Subscription resumed", subscription_id=str(subscription_id))
        
        return updated_subscription
    
    async def get_subscription_analytics(
        self,
        subscription_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get analytics data for a subscription.
        
        Args:
            subscription_id: Subscription identifier
            
        Returns:
            Dictionary containing analytics data
            
        Raises:
            SubscriptionNotFoundException: If subscription doesn't exist
        """
        subscription = await self.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise SubscriptionNotFoundException(subscription_id=str(subscription_id))
        
        # Get device analytics
        devices = await self.device_repo.get_by_subscription_id(subscription_id)
        active_devices = [d for d in devices if d.is_active]
        inactive_devices = [d for d in devices if not d.is_active]
        
        # Calculate usage metrics
        recent_activity = []
        for device in active_devices:
            if device.last_seen_at:
                days_since_last_seen = (datetime.now(timezone.utc) - device.last_seen_at).days
                recent_activity.append(days_since_last_seen)
        
        return {
            "subscription_id": str(subscription_id),
            "status": subscription.status.value,
            "tier": subscription.tier.value,
            "is_active": subscription.is_active(),
            "is_expired": subscription.is_expired(),
            "is_in_grace_period": subscription.is_in_grace_period(),
            "days_until_expiry": subscription.days_until_expiry(),
            "devices": {
                "total": len(devices),
                "active": len(active_devices),
                "inactive": len(inactive_devices),
                "max_allowed": subscription.max_devices,
                "utilization_percent": round((len(active_devices) / subscription.max_devices) * 100, 2),
            },
            "activity": {
                "recent_activity_days": recent_activity,
                "avg_days_since_last_seen": round(sum(recent_activity) / len(recent_activity), 2) if recent_activity else 0,
            },
            "features": subscription.feature_set.features,
            "created_at": subscription.created_at.isoformat(),
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
        }
    
    async def get_expiring_subscriptions(
        self,
        days: int = 7,
    ) -> List[Dict[str, Any]]:
        """
        Get subscriptions expiring within specified days.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of expiring subscription data
        """
        expiring_subscriptions = await self.subscription_repo.get_expiring_soon(days)
        
        result = []
        for subscription in expiring_subscriptions:
            customer = await self.customer_repo.get_by_id(subscription.customer_id)
            
            result.append({
                "subscription_id": str(subscription.id),
                "customer": {
                    "id": str(customer.id) if customer else None,
                    "name": customer.name if customer else "Unknown",
                    "email": customer.email if customer else "Unknown",
                },
                "tier": subscription.tier.value,
                "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
                "days_until_expiry": subscription.days_until_expiry(),
                "license_key": subscription.license_key[:8] + "***",
            })
        
        return result


class CustomerService:
    """
    Customer business logic service.
    
    Handles customer management and related operations.
    Follows Instructions file standards for service layer design.
    """
    
    def __init__(
        self,
        customer_repo: ICustomerRepository,
        subscription_repo: ISubscriptionRepository,
    ):
        self.customer_repo = customer_repo
        self.subscription_repo = subscription_repo
    
    async def create_customer(
        self,
        name: str,
        email: str,
        company: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Customer:
        """
        Create a new customer.
        
        Args:
            name: Customer name
            email: Customer email address
            company: Optional company name
            phone: Optional phone number
            address: Optional address
            metadata: Optional metadata
            
        Returns:
            Created customer entity
        """
        customer = Customer(
            id=uuid4(),
            name=name,
            email=email,
            company=company,
            phone=phone,
            address=address,
            metadata=metadata or {},
        )
        
        created_customer = await self.customer_repo.create(customer)
        
        logger.info(
            "Customer created",
            customer_id=str(created_customer.id),
            email=email,
        )
        
        return created_customer
    
    async def list_customers(
        self,
        limit: int = 10,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List customers with pagination and filtering.
        
        Args:
            limit: Maximum number of customers to return
            offset: Number of customers to skip
            search: Optional search term for filtering customers
            
        Returns:
            Dictionary containing customers list and total count
        """
        
        # Get customers from repository using the correct method names
        customers = await self.customer_repo.list_all(
            limit=limit,
            offset=offset,
            search=search,
        )
        
        # Get total count for pagination using the correct method
        total = await self.customer_repo.count(search=search)
        
        logger.info(
            "Customers listed",
            count=len(customers),
            total=total,
            limit=limit,
            offset=offset,
        )
        
        return {
            "customers": customers,
            "total": total,
        }
    
    async def get_customer_with_subscriptions(
        self,
        customer_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get customer with their subscriptions.
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            Dictionary containing customer and subscription data
            
        Raises:
            CustomerNotFoundException: If customer doesn't exist
        """
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise CustomerNotFoundException(customer_id=str(customer_id))
        
        subscriptions = await self.subscription_repo.get_by_customer_id(customer_id)
        
        return {
            "customer": customer,
            "subscriptions": subscriptions,
            "subscription_count": len(subscriptions),
            "active_subscriptions": len([s for s in subscriptions if s.is_active()]),
        } 