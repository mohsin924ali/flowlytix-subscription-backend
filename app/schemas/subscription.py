"""
Subscription API Schemas

Pydantic models for API request and response validation.
Follows Instructions file standards for API design and data validation.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, validator

from app.domain.entities.subscription import SubscriptionStatus, SubscriptionTier


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
        # Removed use_enum_values = True to fix string enum serialization
        # String enums that inherit from str don't need .value extraction


# Customer schemas
class CustomerBase(BaseSchema):
    """Base customer schema."""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    company: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)


class CustomerCreate(CustomerBase):
    """Schema for creating a customer."""
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CustomerUpdate(BaseSchema):
    """Schema for updating a customer."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    company: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)


class CustomerResponse(CustomerBase):
    """Schema for customer response."""
    id: UUID
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# Device schemas
class DeviceBase(BaseSchema):
    """Base device schema."""
    device_id: str = Field(..., min_length=1, max_length=100)
    device_name: Optional[str] = Field(None, max_length=100)
    device_type: Optional[str] = Field(None, max_length=50)
    fingerprint: Optional[str] = Field(None, max_length=500)
    os_name: Optional[str] = Field(None, max_length=50)
    os_version: Optional[str] = Field(None, max_length=50)
    app_version: Optional[str] = Field(None, max_length=20)


class DeviceCreate(DeviceBase):
    """Schema for creating a device."""
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class DeviceUpdate(BaseSchema):
    """Schema for updating device information."""
    device_name: Optional[str] = Field(None, max_length=100)
    device_type: Optional[str] = Field(None, max_length=50)
    os_name: Optional[str] = Field(None, max_length=50)
    os_version: Optional[str] = Field(None, max_length=50)
    app_version: Optional[str] = Field(None, max_length=20)


class DeviceResponse(DeviceBase):
    """Schema for device response."""
    id: UUID
    subscription_id: UUID
    is_active: bool
    last_seen_at: Optional[datetime]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# Subscription schemas
class SubscriptionBase(BaseSchema):
    """Base subscription schema."""
    tier: SubscriptionTier
    max_devices: int = Field(default=1, ge=1, le=100)
    price: Optional[float] = Field(None, ge=0)
    currency: str = Field(default="USD", max_length=3)
    auto_renew: bool = Field(default=False)


class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a subscription."""
    customer_id: UUID
    duration_days: int = Field(..., ge=1, le=3650)  # Max 10 years
    grace_period_days: int = Field(default=7, ge=0, le=90)
    custom_features: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SubscriptionUpdate(BaseSchema):
    """Schema for updating a subscription."""
    tier: Optional[SubscriptionTier] = None
    status: Optional[SubscriptionStatus] = None
    max_devices: Optional[int] = Field(None, ge=1, le=100)
    expires_at: Optional[datetime] = None
    grace_period_days: Optional[int] = Field(None, ge=0, le=90)
    price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=3)
    auto_renew: Optional[bool] = None
    custom_features: Optional[Dict[str, Any]] = None


class SubscriptionTierUpdateRequest(BaseSchema):
    """Schema for updating subscription tier."""
    tier: SubscriptionTier
    custom_features: Optional[Dict[str, Any]] = None


class SubscriptionExtensionRequest(BaseSchema):
    """Schema for extending subscription."""
    days: int = Field(..., ge=1, le=3650, description="Number of days to extend the subscription")


class SubscriptionResponse(SubscriptionBase):
    """Schema for subscription response."""
    id: UUID
    customer_id: UUID
    customer: Optional[CustomerResponse] = None  # Include customer details
    license_key: str
    status: SubscriptionStatus
    features: Dict[str, Any]
    starts_at: datetime
    expires_at: Optional[datetime]
    grace_period_days: int
    renewal_period_days: Optional[int]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    devices: List[DeviceResponse] = Field(default_factory=list)


# License activation schemas
class LicenseActivationRequest(BaseSchema):
    """Schema for license activation request."""
    license_key: str = Field(..., min_length=10, max_length=100)
    device_id: str = Field(..., min_length=1, max_length=100)
    device_info: Optional[DeviceCreate] = None


class LicenseValidationRequest(BaseSchema):
    """Schema for license validation request."""
    license_key: str = Field(..., min_length=10, max_length=100)
    device_id: str = Field(..., min_length=1, max_length=100)


class LicenseDeactivationRequest(BaseSchema):
    """Schema for license deactivation request."""
    license_key: str = Field(..., min_length=10, max_length=100)
    device_id: str = Field(..., min_length=1, max_length=100)


class LicenseActivationResponse(BaseSchema):
    """Schema for license activation response."""
    token: str
    subscription: SubscriptionResponse
    device: DeviceResponse
    action: str
    message: str
    expires_at: Optional[str]


class LicenseValidationResponse(BaseSchema):
    """Schema for license validation response."""
    valid: bool
    subscription: Optional[SubscriptionResponse] = None
    device: Optional[DeviceResponse] = None
    reason: Optional[str] = None
    message: Optional[str] = None
    in_grace_period: Optional[bool] = None
    days_until_expiry: Optional[int] = None
    features: Optional[Dict[str, Any]] = None
    expires_at: Optional[str] = None


# Analytics schemas
class SubscriptionAnalyticsResponse(BaseSchema):
    """Schema for subscription analytics response."""
    subscription_id: str
    status: str
    tier: str
    is_active: bool
    is_expired: bool
    is_in_grace_period: bool
    days_until_expiry: Optional[int]
    devices: Dict[str, Any]
    activity: Dict[str, Any]
    features: Dict[str, Any]
    created_at: str
    expires_at: Optional[str]


class ExpiringSubscriptionResponse(BaseSchema):
    """Schema for expiring subscription response."""
    subscription_id: str
    customer: Dict[str, Any]
    tier: str
    expires_at: Optional[str]
    days_until_expiry: Optional[int]
    license_key: str


# List and pagination schemas
class PaginationParams(BaseSchema):
    """Schema for pagination parameters."""
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class SubscriptionFilters(BaseSchema):
    """Schema for subscription filters."""
    status: Optional[SubscriptionStatus] = None
    tier: Optional[SubscriptionTier] = None
    customer_id: Optional[UUID] = None
    expires_before: Optional[datetime] = None
    expires_after: Optional[datetime] = None


class CustomerFilters(BaseSchema):
    """Schema for customer filters."""
    search: Optional[str] = Field(None, max_length=100)


class DeviceFilters(BaseSchema):
    """Schema for device filters."""
    is_active: Optional[bool] = None
    subscription_id: Optional[UUID] = None
    device_type: Optional[str] = Field(None, max_length=50)


class PaginatedResponse(BaseSchema):
    """Schema for paginated response."""
    items: List[Any]
    total: int
    limit: int
    offset: int
    has_more: bool = Field(default=False)

    @validator('has_more', pre=False, always=True)
    def calculate_has_more(cls, v, values):
        """Calculate if there are more items."""
        if 'total' in values and 'limit' in values and 'offset' in values:
            return (values['offset'] + values['limit']) < values['total']
        return v if v is not None else False


class SubscriptionListResponse(PaginatedResponse):
    """Schema for subscription list response."""
    items: List[SubscriptionResponse]


class CustomerListResponse(PaginatedResponse):
    """Schema for customer list response."""
    items: List[CustomerResponse]


class DeviceListResponse(PaginatedResponse):
    """Schema for device list response."""
    items: List[DeviceResponse]


# Extension schemas
class SubscriptionExtensionRequest(BaseSchema):
    """Schema for subscription extension request."""
    days: int = Field(..., ge=1, le=3650)


class SubscriptionTierUpdateRequest(BaseSchema):
    """Schema for subscription tier update request."""
    tier: SubscriptionTier
    custom_features: Optional[Dict[str, Any]] = None


class CustomerWithSubscriptionsResponse(BaseSchema):
    """Schema for customer with subscriptions response."""
    customer: CustomerResponse
    subscriptions: List[SubscriptionResponse]
    subscription_count: int
    active_subscriptions: int


# Feature validation schemas
class FeatureCheckRequest(BaseSchema):
    """Schema for feature check request."""
    license_key: str = Field(..., min_length=10, max_length=100)
    feature_name: str = Field(..., min_length=1, max_length=50)


class FeatureCheckResponse(BaseSchema):
    """Schema for feature check response."""
    feature_name: str
    enabled: bool
    limit_value: Optional[int] = None
    subscription_tier: str


# Health check and monitoring schemas
class HealthCheckResponse(BaseSchema):
    """Schema for health check response."""
    status: str
    timestamp: datetime
    version: str
    environment: str


class MetricsResponse(BaseSchema):
    """Schema for metrics response."""
    total_subscriptions: int
    active_subscriptions: int
    expired_subscriptions: int
    total_customers: int
    total_devices: int
    active_devices: int
    subscriptions_by_tier: Dict[str, int]


# Error schemas
class ErrorDetail(BaseSchema):
    """Schema for error detail."""
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseSchema):
    """Schema for error response."""
    error: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime
    request_id: Optional[str] = None 