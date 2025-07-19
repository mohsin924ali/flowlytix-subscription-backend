"""
Payment Domain Entity

Represents a payment in the subscription system following DDD principles.
Contains business rules and invariants for payment processing.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from enum import Enum

from app.domain.value_objects.payment_status import PaymentStatus
from app.domain.value_objects.payment_method import PaymentMethod
from app.domain.value_objects.money import Money
from app.core.exceptions import DomainException


class PaymentType(str, Enum):
    """Payment type enumeration."""
    SUBSCRIPTION = "subscription"
    RENEWAL = "renewal"
    UPGRADE = "upgrade"
    REFUND = "refund"


class PaymentException(DomainException):
    """Base exception for payment-related errors."""
    pass


class InvalidPaymentAmountException(PaymentException):
    """Exception raised when payment amount is invalid."""
    pass


class PaymentAlreadyProcessedException(PaymentException):
    """Exception raised when trying to process an already processed payment."""
    pass


class Payment:
    """
    Payment domain entity representing a payment transaction.
    
    Follows DDD principles with encapsulated business logic and invariants.
    """
    
    def __init__(
        self,
        id: UUID,
        subscription_id: UUID,
        amount: Money,
        payment_method: PaymentMethod,
        payment_type: PaymentType,
        status: PaymentStatus = PaymentStatus.PENDING,
        reference_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        processed_at: Optional[datetime] = None,
        notes: Optional[str] = None,
        admin_user_id: Optional[UUID] = None,
    ):
        """
        Initialize a Payment entity.
        
        Args:
            id: Unique payment identifier
            subscription_id: Associated subscription ID
            amount: Payment amount with currency
            payment_method: Method of payment
            payment_type: Type of payment
            status: Payment status
            reference_id: External reference ID
            description: Payment description
            metadata: Additional payment metadata
            created_at: Creation timestamp
            updated_at: Last update timestamp
            processed_at: Processing timestamp
            notes: Admin notes
            admin_user_id: Admin user who processed the payment
        """
        # Set attributes first
        self._id = id
        self._subscription_id = subscription_id
        self._amount = amount
        self._payment_method = payment_method
        self._payment_type = payment_type
        
        # Validate business rules after setting attributes
        self._validate_amount(amount)
        self._status = status
        self._reference_id = reference_id
        self._description = description
        self._metadata = metadata or {}
        self._created_at = created_at or datetime.now(timezone.utc)
        self._updated_at = updated_at or datetime.now(timezone.utc)
        self._processed_at = processed_at
        self._notes = notes
        self._admin_user_id = admin_user_id
    
    @property
    def id(self) -> UUID:
        """Get payment ID."""
        return self._id
    
    @property
    def subscription_id(self) -> UUID:
        """Get subscription ID."""
        return self._subscription_id
    
    @property
    def amount(self) -> Money:
        """Get payment amount."""
        return self._amount
    
    @property
    def payment_method(self) -> PaymentMethod:
        """Get payment method."""
        return self._payment_method
    
    @property
    def payment_type(self) -> PaymentType:
        """Get payment type."""
        return self._payment_type
    
    @property
    def status(self) -> PaymentStatus:
        """Get payment status."""
        return self._status
    
    @property
    def reference_id(self) -> Optional[str]:
        """Get reference ID."""
        return self._reference_id
    
    @property
    def description(self) -> Optional[str]:
        """Get payment description."""
        return self._description
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Get payment metadata."""
        return self._metadata.copy()
    
    @property
    def created_at(self) -> datetime:
        """Get creation timestamp."""
        return self._created_at
    
    @property
    def updated_at(self) -> datetime:
        """Get last update timestamp."""
        return self._updated_at
    
    @property
    def processed_at(self) -> Optional[datetime]:
        """Get processing timestamp."""
        return self._processed_at
    
    @property
    def notes(self) -> Optional[str]:
        """Get admin notes."""
        return self._notes
    
    @property
    def admin_user_id(self) -> Optional[UUID]:
        """Get admin user ID."""
        return self._admin_user_id
    
    @property
    def is_processed(self) -> bool:
        """Check if payment is processed."""
        return self._status in (PaymentStatus.COMPLETED, PaymentStatus.FAILED, PaymentStatus.REFUNDED)
    
    @property
    def is_successful(self) -> bool:
        """Check if payment is successful."""
        return self._status == PaymentStatus.COMPLETED
    
    @property
    def can_be_refunded(self) -> bool:
        """Check if payment can be refunded."""
        return (
            self._status == PaymentStatus.COMPLETED 
            and self._payment_type != PaymentType.REFUND
        )
    
    def process_payment(self, admin_user_id: UUID, notes: Optional[str] = None) -> None:
        """
        Process the payment manually.
        
        Args:
            admin_user_id: ID of admin user processing the payment
            notes: Optional processing notes
            
        Raises:
            PaymentAlreadyProcessedException: If payment is already processed
        """
        if self.is_processed:
            raise PaymentAlreadyProcessedException(
                f"Payment {self.id} is already processed with status {self.status}"
            )
        
        self._status = PaymentStatus.COMPLETED
        self._processed_at = datetime.now(timezone.utc)
        self._admin_user_id = admin_user_id
        self._notes = notes
        self._updated_at = datetime.now(timezone.utc)
    
    def fail_payment(self, admin_user_id: UUID, reason: str) -> None:
        """
        Mark payment as failed.
        
        Args:
            admin_user_id: ID of admin user failing the payment
            reason: Reason for failure
            
        Raises:
            PaymentAlreadyProcessedException: If payment is already processed
        """
        if self.is_processed:
            raise PaymentAlreadyProcessedException(
                f"Payment {self.id} is already processed with status {self.status}"
            )
        
        self._status = PaymentStatus.FAILED
        self._processed_at = datetime.now(timezone.utc)
        self._admin_user_id = admin_user_id
        self._notes = reason
        self._updated_at = datetime.now(timezone.utc)
    
    def refund_payment(self, admin_user_id: UUID, reason: str) -> "Payment":
        """
        Create a refund for this payment.
        
        Args:
            admin_user_id: ID of admin user creating the refund
            reason: Reason for refund
            
        Returns:
            New Payment entity representing the refund
            
        Raises:
            PaymentException: If payment cannot be refunded
        """
        if not self.can_be_refunded:
            raise PaymentException(
                f"Payment {self.id} cannot be refunded. Status: {self.status}"
            )
        
        # Create refund payment
        refund = Payment(
            id=uuid4(),
            subscription_id=self._subscription_id,
            amount=Money(-self._amount.amount, self._amount.currency),
            payment_method=self._payment_method,
            payment_type=PaymentType.REFUND,
            status=PaymentStatus.COMPLETED,
            reference_id=str(self._id),
            description=f"Refund for payment {self._id}",
            metadata={
                "original_payment_id": str(self._id),
                "refund_reason": reason,
            },
            processed_at=datetime.now(timezone.utc),
            admin_user_id=admin_user_id,
            notes=reason,
        )
        
        # Update original payment status
        self._status = PaymentStatus.REFUNDED
        self._updated_at = datetime.now(timezone.utc)
        
        return refund
    
    def add_note(self, note: str, admin_user_id: UUID) -> None:
        """
        Add a note to the payment.
        
        Args:
            note: Note to add
            admin_user_id: ID of admin user adding the note
        """
        current_notes = self._notes or ""
        timestamp = datetime.now(timezone.utc).isoformat()
        new_note = f"[{timestamp}] Admin {admin_user_id}: {note}"
        
        if current_notes:
            self._notes = f"{current_notes}\n{new_note}"
        else:
            self._notes = new_note
        
        self._updated_at = datetime.now(timezone.utc)
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Update payment metadata.
        
        Args:
            metadata: New metadata to merge
        """
        self._metadata.update(metadata)
        self._updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert payment to dictionary representation.
        
        Returns:
            Dictionary representation of the payment
        """
        return {
            "id": str(self._id),
            "subscription_id": str(self._subscription_id),
            "amount": self._amount.amount,
            "currency": self._amount.currency,
            "payment_method": str(self._payment_method),
            "payment_type": str(self._payment_type),
            "status": str(self._status),
            "reference_id": self._reference_id,
            "description": self._description,
            "metadata": self._metadata,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
            "processed_at": self._processed_at.isoformat() if self._processed_at else None,
            "notes": self._notes,
            "admin_user_id": str(self._admin_user_id) if self._admin_user_id else None,
        }
    
    @classmethod
    def create_subscription_payment(
        cls,
        subscription_id: UUID,
        amount: Money,
        payment_method: PaymentMethod,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> "Payment":
        """
        Factory method to create a subscription payment.
        
        Args:
            subscription_id: Subscription ID
            amount: Payment amount
            payment_method: Payment method
            description: Payment description
            reference_id: External reference ID
            
        Returns:
            New Payment entity
        """
        return cls(
            id=uuid4(),
            subscription_id=subscription_id,
            amount=amount,
            payment_method=payment_method,
            payment_type=PaymentType.SUBSCRIPTION,
            description=description or "Subscription payment",
            reference_id=reference_id,
        )
    
    @classmethod
    def create_renewal_payment(
        cls,
        subscription_id: UUID,
        amount: Money,
        payment_method: PaymentMethod,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> "Payment":
        """
        Factory method to create a renewal payment.
        
        Args:
            subscription_id: Subscription ID
            amount: Payment amount
            payment_method: Payment method
            description: Payment description
            reference_id: External reference ID
            
        Returns:
            New Payment entity
        """
        return cls(
            id=uuid4(),
            subscription_id=subscription_id,
            amount=amount,
            payment_method=payment_method,
            payment_type=PaymentType.RENEWAL,
            description=description or "Subscription renewal payment",
            reference_id=reference_id,
        )
    
    def _validate_amount(self, amount: Money) -> None:
        """
        Validate payment amount.
        
        Args:
            amount: Amount to validate
            
        Raises:
            InvalidPaymentAmountException: If amount is invalid
        """
        if amount.amount == 0:
            raise InvalidPaymentAmountException("Payment amount cannot be zero")
        
        # Allow negative amounts only for refunds
        if amount.amount < 0 and self._payment_type != PaymentType.REFUND:
            raise InvalidPaymentAmountException("Payment amount cannot be negative except for refunds")
    
    def __eq__(self, other: object) -> bool:
        """Check equality based on ID."""
        if not isinstance(other, Payment):
            return False
        return self._id == other._id
    
    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self._id)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Payment(id={self._id}, amount={self._amount}, status={self._status})" 