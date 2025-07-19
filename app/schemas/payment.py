"""
Payment Schemas

Pydantic models for payment API requests and responses.
Following Instructions file standards for validation and serialization.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, validator, ConfigDict

from app.domain.entities.payment import PaymentType
from app.domain.value_objects.payment_status import PaymentStatus
from app.domain.value_objects.payment_method import PaymentMethod


# Request Schemas

class CreatePaymentRequest(BaseModel):
    """Request schema for creating a payment."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True
    )
    
    subscription_id: UUID = Field(..., description="Associated subscription ID")
    amount: Decimal = Field(..., gt=0, description="Payment amount (must be positive)")
    currency: str = Field("USD", min_length=3, max_length=3, description="Currency code (ISO 4217)")
    payment_method: PaymentMethod = Field(..., description="Payment method")
    payment_type: PaymentType = Field(..., description="Type of payment")
    
    @validator("payment_method", pre=True)
    def validate_payment_method(cls, v):
        """Convert string to PaymentMethod enum if needed."""
        if isinstance(v, str):
            try:
                return PaymentMethod(v)
            except ValueError:
                raise ValueError(f"Invalid payment method: {v}")
        return v
    
    @validator("payment_type", pre=True)
    def validate_payment_type(cls, v):
        """Convert string to PaymentType enum if needed."""
        if isinstance(v, str):
            try:
                return PaymentType(v)
            except ValueError:
                raise ValueError(f"Invalid payment type: {v}")
        return v
    description: Optional[str] = Field(None, max_length=500, description="Payment description")
    reference_id: Optional[str] = Field(None, max_length=255, description="External reference ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @validator("currency")
    def validate_currency(cls, v):
        """Validate currency code format."""
        if not v.isupper():
            raise ValueError("Currency code must be uppercase")
        return v
    
    @validator("amount")
    def validate_amount(cls, v):
        """Validate amount precision."""
        if v.as_tuple().exponent < -2:
            raise ValueError("Amount cannot have more than 2 decimal places")
        return v


class ProcessPaymentRequest(BaseModel):
    """Request schema for processing a payment manually."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    admin_user_id: UUID = Field(..., description="Admin user processing the payment")
    notes: Optional[str] = Field(None, max_length=1000, description="Processing notes")


class FailPaymentRequest(BaseModel):
    """Request schema for failing a payment."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    admin_user_id: UUID = Field(..., description="Admin user failing the payment")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for failure")


class RefundPaymentRequest(BaseModel):
    """Request schema for refunding a payment."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    admin_user_id: UUID = Field(..., description="Admin user creating the refund")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for refund")


class AddPaymentNoteRequest(BaseModel):
    """Request schema for adding a note to a payment."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    admin_user_id: UUID = Field(..., description="Admin user adding the note")
    note: str = Field(..., min_length=1, max_length=1000, description="Note to add")


class BulkPaymentActionRequest(BaseModel):
    """Request schema for bulk payment actions."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    payment_ids: List[UUID] = Field(..., min_items=1, max_items=100, description="Payment IDs to process")
    admin_user_id: UUID = Field(..., description="Admin user performing the action")
    action: str = Field(..., pattern="^(process|fail)$", description="Action to perform")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for the action")


class PaymentSearchRequest(BaseModel):
    """Request schema for searching payments."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True
    )
    
    # Filters
    status: Optional[List[PaymentStatus]] = Field(None, description="Payment statuses to filter by")
    payment_method: Optional[List[PaymentMethod]] = Field(None, description="Payment methods to filter by")
    payment_type: Optional[List[PaymentType]] = Field(None, description="Payment types to filter by")
    subscription_id: Optional[UUID] = Field(None, description="Subscription ID to filter by")
    admin_user_id: Optional[UUID] = Field(None, description="Admin user ID to filter by")
    start_date: Optional[datetime] = Field(None, description="Start date for date range filter")
    end_date: Optional[datetime] = Field(None, description="End date for date range filter")
    min_amount: Optional[Decimal] = Field(None, ge=0, description="Minimum amount filter")
    max_amount: Optional[Decimal] = Field(None, ge=0, description="Maximum amount filter")
    currency: Optional[str] = Field(None, min_length=3, max_length=3, description="Currency filter")
    
    # Pagination
    limit: Optional[int] = Field(None, ge=1, le=1000, description="Maximum number of results")
    offset: Optional[int] = Field(None, ge=0, description="Number of results to skip")
    
    # Ordering
    order_by: Optional[str] = Field("created_at", description="Field to order by")
    order_direction: str = Field("desc", pattern="^(asc|desc)$", description="Order direction")
    
    @validator("end_date")
    def validate_date_range(cls, v, values):
        """Validate that end_date is after start_date."""
        if v and "start_date" in values and values["start_date"] and v <= values["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


# Response Schemas

class PaymentResponse(BaseModel):
    """Response schema for payment data."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    subscription_id: UUID
    amount: Decimal
    currency: str
    payment_method: PaymentMethod
    payment_type: PaymentType
    status: PaymentStatus
    reference_id: Optional[str]
    description: Optional[str]
    notes: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime]
    admin_user_id: Optional[UUID]
    
    @classmethod
    def from_domain(cls, payment: "Payment") -> "PaymentResponse":
        """Create response from domain entity."""
        return cls(
            id=payment.id,
            subscription_id=payment.subscription_id,
            amount=payment.amount.amount,
            currency=payment.amount.currency,
            payment_method=payment.payment_method,
            payment_type=payment.payment_type,
            status=payment.status,
            reference_id=payment.reference_id,
            description=payment.description,
            notes=payment.notes,
            metadata=payment.metadata,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
            processed_at=payment.processed_at,
            admin_user_id=payment.admin_user_id,
        )


class PaymentListResponse(BaseModel):
    """Response schema for payment list with pagination."""
    
    payments: List[PaymentResponse]
    total: int
    limit: Optional[int]
    offset: Optional[int]
    has_more: bool


class PaymentHistoryEntry(BaseModel):
    """Response schema for payment history entry."""
    
    id: UUID
    payment_id: UUID
    old_status: Optional[PaymentStatus]
    new_status: PaymentStatus
    action: str
    admin_user_id: Optional[UUID]
    reason: Optional[str]
    notes: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime


class PaymentHistoryResponse(BaseModel):
    """Response schema for payment history."""
    
    entries: List[PaymentHistoryEntry]
    total: int
    limit: Optional[int]
    offset: Optional[int]


class RefundResponse(BaseModel):
    """Response schema for refund operation."""
    
    original_payment: PaymentResponse
    refund_payment: PaymentResponse


class BulkPaymentActionResponse(BaseModel):
    """Response schema for bulk payment actions."""
    
    successful: List[UUID]
    failed: List[Dict[str, Any]]
    total: int
    success_count: int
    failure_count: int


class PaymentAnalyticsResponse(BaseModel):
    """Response schema for payment analytics."""
    
    total_payments: int
    total_revenue: Decimal
    status_breakdown: Dict[str, int]
    method_breakdown: Dict[str, int]
    period: Dict[str, Optional[datetime]]


class RevenueDataPoint(BaseModel):
    """Response schema for revenue data point."""
    
    period: datetime
    revenue: Decimal
    count: int


class RevenueByPeriodResponse(BaseModel):
    """Response schema for revenue by period."""
    
    data: List[RevenueDataPoint]
    period: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]


class PaymentMethodStats(BaseModel):
    """Response schema for payment method statistics."""
    
    count: int
    total_amount: Decimal
    average_amount: Decimal


class PaymentMethodStatsResponse(BaseModel):
    """Response schema for payment method statistics."""
    
    methods: Dict[str, PaymentMethodStats]


class PaymentStatusSummary(BaseModel):
    """Response schema for payment status summary."""
    
    total: int
    by_status: Dict[str, int]
    by_method: Dict[str, int]
    total_amount: Decimal
    completed_amount: Decimal


class AdminActivityEntry(BaseModel):
    """Response schema for admin activity entry."""
    
    id: UUID
    payment_id: UUID
    old_status: Optional[PaymentStatus]
    new_status: PaymentStatus
    action: str
    reason: Optional[str]
    notes: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime


class AdminActivityResponse(BaseModel):
    """Response schema for admin activity."""
    
    entries: List[AdminActivityEntry]
    total: int
    limit: Optional[int]
    offset: Optional[int]
    admin_user_id: UUID
    start_date: Optional[datetime]
    end_date: Optional[datetime]


# Error Response Schemas

class PaymentErrorResponse(BaseModel):
    """Response schema for payment errors."""
    
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    payment_id: Optional[UUID] = None


class ValidationErrorResponse(BaseModel):
    """Response schema for validation errors."""
    
    error: str = "validation_error"
    message: str
    field_errors: List[Dict[str, Any]] 