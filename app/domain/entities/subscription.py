"""
Subscription Domain Entities

Core business entities for subscription management.
Follows Instructions file standards for domain-driven design and business logic.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from enum import Enum

from app.core.exceptions import (
    SubscriptionExpiredException,
    DeviceLimitExceededException,
    LicenseKeyInvalidException,
)


class SubscriptionStatus(str, Enum):
    """Subscription status enumeration with business rules."""
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    PENDING = "pending"


class SubscriptionTier(str, Enum):
    """Subscription tier enumeration with feature mapping."""
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    TRIAL = "trial"


class FeatureSet:
    """
    Feature set value object for subscription tiers.
    
    Defines what features are available for each tier.
    Follows Instructions file standards for value objects.
    """
    
    # Feature definitions by tier
    TIER_FEATURES = {
        SubscriptionTier.BASIC: {
            "max_customers": 100,
            "max_products": 500,
            "analytics": False,
            "multi_location": False,
            "api_access": False,
            "priority_support": False,
        },
        SubscriptionTier.PROFESSIONAL: {
            "max_customers": 1000,
            "max_products": 5000,
            "analytics": True,
            "multi_location": True,
            "api_access": True,
            "priority_support": False,
        },
        SubscriptionTier.ENTERPRISE: {
            "max_customers": -1,  # Unlimited
            "max_products": -1,   # Unlimited
            "analytics": True,
            "multi_location": True,
            "api_access": True,
            "priority_support": True,
        },
        SubscriptionTier.TRIAL: {
            "max_customers": 10,
            "max_products": 50,
            "analytics": False,
            "multi_location": False,
            "api_access": False,
            "priority_support": False,
        },
    }
    
    def __init__(self, tier: SubscriptionTier, custom_features: Optional[Dict[str, Any]] = None):
        self.tier = tier
        self.features = self.TIER_FEATURES.get(tier, {}).copy()
        
        # Override with custom features if provided
        if custom_features:
            self.features.update(custom_features)
    
    def has_feature(self, feature_name: str) -> bool:
        """Check if a feature is enabled."""
        return self.features.get(feature_name, False)
    
    def get_limit(self, limit_name: str) -> int:
        """Get a numeric limit for a feature."""
        return self.features.get(limit_name, 0)


class Customer:
    """
    Customer domain entity.
    
    Represents a customer who can have multiple subscriptions.
    Follows Instructions file standards for entity design.
    """
    
    def __init__(
        self,
        id: UUID,
        name: str,
        email: str,
        company: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.name = name
        self.email = email
        self.company = company
        self.phone = phone
        self.address = address
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
    
    def update_info(
        self,
        name: Optional[str] = None,
        email: Optional[str] = None,
        company: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
    ) -> None:
        """Update customer information."""
        if name is not None:
            self.name = name
        if email is not None:
            self.email = email
        if company is not None:
            self.company = company
        if phone is not None:
            self.phone = phone
        if address is not None:
            self.address = address
        
        self.updated_at = datetime.now(timezone.utc)
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to customer."""
        self.metadata[key] = value
        self.updated_at = datetime.now(timezone.utc)


class Device:
    """
    Device domain entity.
    
    Represents a device activated with a subscription.
    Follows Instructions file standards for entity design.
    """
    
    def __init__(
        self,
        id: UUID,
        subscription_id: UUID,
        device_id: str,
        device_name: Optional[str] = None,
        device_type: Optional[str] = None,
        fingerprint: Optional[str] = None,
        os_name: Optional[str] = None,
        os_version: Optional[str] = None,
        app_version: Optional[str] = None,
        is_active: bool = True,
        last_seen_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.subscription_id = subscription_id
        self.device_id = device_id
        self.device_name = device_name
        self.device_type = device_type
        self.fingerprint = fingerprint
        self.os_name = os_name
        self.os_version = os_version
        self.app_version = app_version
        self.is_active = is_active
        self.last_seen_at = last_seen_at
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
    
    def activate(self) -> None:
        """Activate the device."""
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
    
    def deactivate(self) -> None:
        """Deactivate the device."""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def update_last_seen(self) -> None:
        """Update last seen timestamp."""
        self.last_seen_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def update_device_info(
        self,
        device_name: Optional[str] = None,
        os_name: Optional[str] = None,
        os_version: Optional[str] = None,
        app_version: Optional[str] = None,
    ) -> None:
        """Update device information."""
        if device_name is not None:
            self.device_name = device_name
        if os_name is not None:
            self.os_name = os_name
        if os_version is not None:
            self.os_version = os_version
        if app_version is not None:
            self.app_version = app_version
        
        self.updated_at = datetime.now(timezone.utc)


class Subscription:
    """
    Subscription domain entity.
    
    Core business entity representing a subscription with its business rules.
    Follows Instructions file standards for domain-driven design.
    """
    
    def __init__(
        self,
        id: UUID,
        customer_id: UUID,
        license_key: str,
        tier: SubscriptionTier,
        status: SubscriptionStatus = SubscriptionStatus.PENDING,
        features: Optional[Dict[str, Any]] = None,
        max_devices: int = 1,
        starts_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        grace_period_days: int = 7,
        price: Optional[float] = None,
        currency: str = "USD",
        auto_renew: bool = False,
        renewal_period_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        devices: Optional[List[Device]] = None,
    ):
        self.id = id
        self.customer_id = customer_id
        self.license_key = license_key
        self.tier = tier
        self.status = status
        self.max_devices = max_devices
        self.starts_at = starts_at or datetime.now(timezone.utc)
        self.expires_at = expires_at
        self.grace_period_days = grace_period_days
        self.price = price
        self.currency = currency
        self.auto_renew = auto_renew
        self.renewal_period_days = renewal_period_days
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        self.devices = devices or []
        
        # Initialize feature set
        self.feature_set = FeatureSet(tier, features)
    
    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        if self.status != SubscriptionStatus.ACTIVE:
            return False
        
        now = datetime.now(timezone.utc)
        
        # Check if subscription has started
        if now < self.starts_at:
            return False
        
        # Check if subscription has expired (with grace period)
        if self.expires_at:
            grace_end = self.expires_at + timedelta(days=self.grace_period_days)
            if now > grace_end:
                return False
        
        return True
    
    def is_expired(self) -> bool:
        """Check if subscription is expired (beyond grace period)."""
        if not self.expires_at:
            return False
        
        now = datetime.now(timezone.utc)
        grace_end = self.expires_at + timedelta(days=self.grace_period_days)
        return now > grace_end
    
    def is_in_grace_period(self) -> bool:
        """Check if subscription is in grace period."""
        if not self.expires_at:
            return False
        
        now = datetime.now(timezone.utc)
        return self.expires_at < now <= (self.expires_at + timedelta(days=self.grace_period_days))
    
    def days_until_expiry(self) -> Optional[int]:
        """Get days until expiry, or None if no expiry date."""
        if not self.expires_at:
            return None
        
        now = datetime.now(timezone.utc)
        delta = self.expires_at - now
        return max(0, delta.days)
    
    def can_add_device(self) -> bool:
        """Check if more devices can be added."""
        active_devices = [d for d in self.devices if d.is_active]
        return len(active_devices) < self.max_devices
    
    def add_device(self, device: Device) -> None:
        """
        Add a device to the subscription.
        
        Raises:
            DeviceLimitExceededException: If device limit is exceeded
        """
        if not self.can_add_device():
            active_count = len([d for d in self.devices if d.is_active])
            raise DeviceLimitExceededException(
                current_devices=active_count,
                max_devices=self.max_devices
            )
        
        device.subscription_id = self.id
        self.devices.append(device)
        self.updated_at = datetime.now(timezone.utc)
    
    def remove_device(self, device_id: str) -> bool:
        """
        Remove a device from the subscription.
        
        Returns:
            True if device was found and removed, False otherwise
        """
        for device in self.devices:
            if device.device_id == device_id:
                device.deactivate()
                self.updated_at = datetime.now(timezone.utc)
                return True
        return False
    
    def get_device(self, device_id: str) -> Optional[Device]:
        """Get a device by device ID."""
        for device in self.devices:
            if device.device_id == device_id:
                return device
        return None
    
    def activate(self) -> None:
        """Activate the subscription."""
        self.status = SubscriptionStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc)
    
    def suspend(self) -> None:
        """Suspend the subscription."""
        self.status = SubscriptionStatus.SUSPENDED
        self.updated_at = datetime.now(timezone.utc)
    
    def cancel(self) -> None:
        """Cancel the subscription."""
        self.status = SubscriptionStatus.CANCELLED
        # Deactivate all devices
        for device in self.devices:
            device.deactivate()
        self.updated_at = datetime.now(timezone.utc)
    
    def resume(self) -> None:
        """Resume a suspended or cancelled subscription."""
        self.status = SubscriptionStatus.ACTIVE
        # Reactivate all devices that were active before
        for device in self.devices:
            if not device.is_active:
                device.activate()
        self.updated_at = datetime.now(timezone.utc)
    
    def extend_expiry(self, days: int) -> None:
        """Extend subscription expiry by specified days."""
        if self.expires_at:
            self.expires_at += timedelta(days=days)
        else:
            self.expires_at = datetime.now(timezone.utc) + timedelta(days=days)
        self.updated_at = datetime.now(timezone.utc)
    
    def update_tier(self, new_tier: SubscriptionTier, custom_features: Optional[Dict[str, Any]] = None) -> None:
        """Update subscription tier and features."""
        self.tier = new_tier
        self.feature_set = FeatureSet(new_tier, custom_features)
        self.updated_at = datetime.now(timezone.utc)
    
    def validate_for_activation(self, device_id: str) -> Dict[str, Any]:
        """
        Validate subscription for device activation.
        
        Returns:
            Dictionary with validation result
            
        Raises:
            SubscriptionExpiredException: If subscription is expired
            DeviceLimitExceededException: If device limit is exceeded
        """
        # Check if subscription is expired
        if self.is_expired():
            raise SubscriptionExpiredException(
                subscription_id=str(self.id),
                expired_at=self.expires_at.isoformat() if self.expires_at else None
            )
        
        # Check if device already exists
        existing_device = self.get_device(device_id)
        if existing_device:
            if existing_device.is_active:
                return {
                    "valid": True,
                    "action": "already_active",
                    "device": existing_device,
                    "message": "Device is already activated"
                }
            else:
                # Reactivate existing device
                existing_device.activate()
                return {
                    "valid": True,
                    "action": "reactivated",
                    "device": existing_device,
                    "message": "Device reactivated successfully"
                }
        
        # Check device limit for new device
        if not self.can_add_device():
            active_count = len([d for d in self.devices if d.is_active])
            raise DeviceLimitExceededException(
                current_devices=active_count,
                max_devices=self.max_devices
            )
        
        return {
            "valid": True,
            "action": "can_activate",
            "message": "Device can be activated"
        }
    
    def to_token_payload(self, device_id: str) -> Dict[str, Any]:
        """
        Generate token payload for this subscription.
        
        Returns:
            Dictionary containing subscription data for JWT token
        """
        return {
            "id": str(self.id),
            "customer_id": str(self.customer_id),
            "license_key": self.license_key,
            "tier": self.tier.value,
            "features": self.feature_set.features,
            "device_id": device_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "grace_period_days": self.grace_period_days,
            "status": self.status.value,
        } 