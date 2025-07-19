"""
Subscription Database Models

SQLAlchemy models for subscription management.
Follows Instructions file standards for database design and relationships.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    String,
    Integer,
    Text,
    ForeignKey,
    JSON,
    Enum,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.database import Base


class SubscriptionStatus(str, Enum):
    """Subscription status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    PENDING = "pending"


class SubscriptionTier(str, Enum):
    """Subscription tier enumeration."""
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    TRIAL = "trial"


class Customer(Base):
    """
    Customer model for subscription management.
    
    Represents a customer who can have multiple subscriptions.
    """
    __tablename__ = "customers"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique customer identifier"
    )
    
    # Basic information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Customer name"
    )
    
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="Customer email address"
    )
    
    company: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Customer company name"
    )
    
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Customer phone number"
    )
    
    # Address information
    address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Customer address"
    )
    
    # Metadata
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional customer metadata"
    )
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Customer creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Customer last update timestamp"
    )
    
    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription",
        back_populates="customer",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_customers_email", "email"),
        Index("idx_customers_company", "company"),
        Index("idx_customers_created_at", "created_at"),
    )


class Subscription(Base):
    """
    Subscription model for license management.
    
    Represents a subscription with features, devices, and payment information.
    """
    __tablename__ = "subscriptions"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique subscription identifier"
    )
    
    # Customer relationship
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        comment="Customer who owns this subscription"
    )
    
    # Subscription details
    license_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="Unique license key"
    )
    
    tier: Mapped[str] = mapped_column(
        Enum("basic", "professional", "enterprise", "trial", name="subscription_tier"),
        nullable=False,
        comment="Subscription tier"
    )
    
    status: Mapped[str] = mapped_column(
        Enum("active", "expired", "suspended", "cancelled", "pending", name="subscription_status"),
        nullable=False,
        default="pending",
        comment="Subscription status"
    )
    
    # Features and limits
    features: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Enabled features for this subscription"
    )
    
    max_devices: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Maximum number of devices allowed"
    )
    
    # Timing
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Subscription start date"
    )
    
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Subscription expiration date"
    )
    
    grace_period_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=7,
        comment="Grace period in days after expiration"
    )
    
    # Payment information
    price: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Subscription price"
    )
    
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
        comment="Price currency code"
    )
    
    # Renewal information
    auto_renew: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Auto-renewal flag"
    )
    
    renewal_period_days: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Renewal period in days"
    )
    
    # Metadata
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional subscription metadata"
    )
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Subscription creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Subscription last update timestamp"
    )
    
    # Relationships
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="subscriptions"
    )
    
    devices: Mapped[List["Device"]] = relationship(
        "Device",
        back_populates="subscription",
        cascade="all, delete-orphan"
    )
    
    payments: Mapped[List["PaymentModel"]] = relationship(
        "PaymentModel",
        back_populates="subscription",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_subscriptions_customer_id", "customer_id"),
        Index("idx_subscriptions_license_key", "license_key"),
        Index("idx_subscriptions_status", "status"),
        Index("idx_subscriptions_tier", "tier"),
        Index("idx_subscriptions_expires_at", "expires_at"),
        Index("idx_subscriptions_created_at", "created_at"),
    )


class Device(Base):
    """
    Device model for device management.
    
    Represents a device activated with a subscription.
    """
    __tablename__ = "devices"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique device identifier"
    )
    
    # Subscription relationship
    subscription_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        comment="Subscription this device is associated with"
    )
    
    # Device information
    device_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Device identifier from the client"
    )
    
    device_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Human-readable device name"
    )
    
    device_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Device type (desktop, mobile, etc.)"
    )
    
    # Device fingerprint for security
    fingerprint: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Device fingerprint hash"
    )
    
    # Operating system information
    os_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Operating system name"
    )
    
    os_version: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Operating system version"
    )
    
    # Application information
    app_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Application version"
    )
    
    # Status and activity
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Device active status"
    )
    
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last activity timestamp"
    )
    
    # Metadata
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional device metadata"
    )
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Device creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Device last update timestamp"
    )
    
    # Relationships
    subscription: Mapped["Subscription"] = relationship(
        "Subscription",
        back_populates="devices"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_devices_subscription_id", "subscription_id"),
        Index("idx_devices_device_id", "device_id"),
        Index("idx_devices_fingerprint", "fingerprint"),
        Index("idx_devices_is_active", "is_active"),
        Index("idx_devices_last_seen_at", "last_seen_at"),
        Index("idx_devices_created_at", "created_at"),
        # Unique constraint for device_id per subscription
        Index("idx_devices_subscription_device_unique", "subscription_id", "device_id", unique=True),
    ) 