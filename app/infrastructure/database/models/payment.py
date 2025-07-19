"""
Payment Database Model

SQLAlchemy model for payments following the Infrastructure layer pattern.
Maps payment domain entities to database tables.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from uuid import UUID

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Index,
    CheckConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.domain.entities.payment import PaymentType
from app.domain.value_objects.payment_status import PaymentStatus
from app.domain.value_objects.payment_method import PaymentMethod


class PaymentModel(Base):
    """
    Payment database model.
    
    Maps payment domain entities to database representation.
    """
    
    __tablename__ = "payments"
    
    # Primary key
    id = Column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        comment="Unique payment identifier"
    )
    
    # Foreign keys
    subscription_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        comment="Associated subscription ID"
    )
    
    admin_user_id = Column(
        PostgresUUID(as_uuid=True),
        nullable=True,
        comment="Admin user who processed the payment"
    )
    
    # Payment details
    amount = Column(
        Float,
        nullable=False,
        comment="Payment amount"
    )
    
    currency = Column(
        String(3),
        nullable=False,
        default="USD",
        comment="Payment currency code (ISO 4217)"
    )
    
    payment_method = Column(
        SQLEnum(PaymentMethod, name="payment_method", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="Payment method used"
    )
    
    payment_type = Column(
        SQLEnum(PaymentType, name="payment_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="Type of payment"
    )
    
    status = Column(
        SQLEnum(PaymentStatus, name="payment_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=PaymentStatus.PENDING,
        comment="Payment status"
    )
    
    # Reference and description
    reference_id = Column(
        String(255),
        nullable=True,
        comment="External reference ID"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Payment description"
    )
    
    notes = Column(
        Text,
        nullable=True,
        comment="Admin notes and processing history"
    )
    
    # Metadata
    metadata_json = Column(
        JSON,
        nullable=True,
        default=lambda: {},
        comment="Additional payment metadata"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Payment creation timestamp"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Payment last update timestamp"
    )
    
    processed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Payment processing timestamp"
    )
    
    # Relationships
    subscription = relationship(
        "Subscription",
        back_populates="payments",
        lazy="select"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_payments_subscription_id", "subscription_id"),
        Index("idx_payments_status", "status"),
        Index("idx_payments_payment_method", "payment_method"),
        Index("idx_payments_payment_type", "payment_type"),
        Index("idx_payments_created_at", "created_at"),
        Index("idx_payments_processed_at", "processed_at"),
        Index("idx_payments_reference_id", "reference_id"),
        Index("idx_payments_admin_user_id", "admin_user_id"),
        Index("idx_payments_composite_status_created", "status", "created_at"),
        Index("idx_payments_composite_subscription_status", "subscription_id", "status"),
        
        # Check constraints
        CheckConstraint(
            "amount != 0",
            name="ck_payments_amount_not_zero"
        ),
        CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_payments_currency_format"
        ),
        CheckConstraint(
            "processed_at IS NULL OR processed_at >= created_at",
            name="ck_payments_processed_after_created"
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_payments_updated_after_created"
        ),
    )
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<PaymentModel(id={self.id}, amount={self.amount}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model to dictionary.
        
        Returns:
            Dictionary representation of the payment
        """
        return {
            "id": str(self.id),
            "subscription_id": str(self.subscription_id),
            "amount": float(self.amount),
            "currency": self.currency,
            "payment_method": str(self.payment_method) if self.payment_method else None,
            "payment_type": str(self.payment_type) if self.payment_type else None,
            "status": str(self.status) if self.status else None,
            "reference_id": self.reference_id,
            "description": self.description,
            "notes": self.notes,
            "metadata": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "admin_user_id": str(self.admin_user_id) if self.admin_user_id else None,
        }
    
    @classmethod
    def from_domain(cls, payment: "Payment") -> "PaymentModel":
        """
        Create model from domain entity.
        
        Args:
            payment: Payment domain entity
            
        Returns:
            PaymentModel instance
        """
        return cls(
            id=payment.id,
            subscription_id=payment.subscription_id,
            amount=float(payment.amount.amount),
            currency=payment.amount.currency,
            payment_method=payment.payment_method,
            payment_type=payment.payment_type,
            status=payment.status,
            reference_id=payment.reference_id,
            description=payment.description,
            notes=payment.notes,
            metadata_json=payment.metadata,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
            processed_at=payment.processed_at,
            admin_user_id=payment.admin_user_id,
        )
    
    def to_domain(self) -> "Payment":
        """
        Convert model to domain entity.
        
        Returns:
            Payment domain entity
        """
        from app.domain.entities.payment import Payment, PaymentType
        from app.domain.value_objects.money import Money
        from app.domain.value_objects.payment_method import PaymentMethod
        from app.domain.value_objects.payment_status import PaymentStatus
        
        # Convert string values to enum instances if necessary
        payment_method = self.payment_method
        if isinstance(payment_method, str):
            payment_method = PaymentMethod(payment_method)
            
        payment_type = self.payment_type
        if isinstance(payment_type, str):
            payment_type = PaymentType(payment_type)
            
        status = self.status
        if isinstance(status, str):
            status = PaymentStatus(status)
        
        return Payment(
            id=self.id,
            subscription_id=self.subscription_id,
            amount=Money(Decimal(str(self.amount)), self.currency),
            payment_method=payment_method,
            payment_type=payment_type,
            status=status,
            reference_id=self.reference_id,
            description=self.description,
            metadata=self.metadata_json or {},
            created_at=self.created_at,
            updated_at=self.updated_at,
            processed_at=self.processed_at,
            notes=self.notes,
            admin_user_id=self.admin_user_id,
        )


class PaymentHistoryModel(Base):
    """
    Payment history model for tracking payment status changes.
    
    Provides audit trail for payment processing.
    """
    
    __tablename__ = "payment_history"
    
    # Primary key
    id = Column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        comment="Unique history entry identifier"
    )
    
    # Foreign keys
    payment_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        comment="Associated payment ID"
    )
    
    admin_user_id = Column(
        PostgresUUID(as_uuid=True),
        nullable=True,
        comment="Admin user who made the change"
    )
    
    # Change details
    old_status = Column(
        SQLEnum(PaymentStatus, name="payment_status", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        comment="Previous payment status"
    )
    
    new_status = Column(
        SQLEnum(PaymentStatus, name="payment_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="New payment status"
    )
    
    action = Column(
        String(50),
        nullable=False,
        comment="Action performed (created, processed, failed, refunded, etc.)"
    )
    
    reason = Column(
        Text,
        nullable=True,
        comment="Reason for the change"
    )
    
    notes = Column(
        Text,
        nullable=True,
        comment="Additional notes"
    )
    
    # Metadata
    metadata_json = Column(
        JSON,
        nullable=True,
        default=lambda: {},
        comment="Additional change metadata"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="History entry creation timestamp"
    )
    
    # Relationships
    payment = relationship(
        "PaymentModel",
        backref="history",
        lazy="select"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_payment_history_payment_id", "payment_id"),
        Index("idx_payment_history_admin_user_id", "admin_user_id"),
        Index("idx_payment_history_created_at", "created_at"),
        Index("idx_payment_history_action", "action"),
        Index("idx_payment_history_new_status", "new_status"),
        Index("idx_payment_history_composite_payment_created", "payment_id", "created_at"),
    )
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<PaymentHistoryModel(id={self.id}, payment_id={self.payment_id}, action={self.action})>" 