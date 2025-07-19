"""
Payment Status Value Object

Represents the status of a payment following DDD principles.
Immutable value object with proper validation and business rules.
"""

from enum import Enum
from typing import Set, Dict, List


class PaymentStatus(str, Enum):
    """
    Payment status enumeration.
    
    Represents all possible states of a payment in the system.
    """
    
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    EXPIRED = "expired"
    
    @property
    def is_final(self) -> bool:
        """Check if this is a final status that cannot be changed."""
        return self in (
            PaymentStatus.COMPLETED,
            PaymentStatus.FAILED,
            PaymentStatus.CANCELLED,
            PaymentStatus.REFUNDED,
            PaymentStatus.EXPIRED,
        )
    
    @property
    def is_successful(self) -> bool:
        """Check if this status represents a successful payment."""
        return self in (
            PaymentStatus.COMPLETED,
            PaymentStatus.PARTIALLY_REFUNDED,
        )
    
    @property
    def is_failed(self) -> bool:
        """Check if this status represents a failed payment."""
        return self in (
            PaymentStatus.FAILED,
            PaymentStatus.CANCELLED,
            PaymentStatus.EXPIRED,
        )
    
    @property
    def is_refunded(self) -> bool:
        """Check if this status represents a refunded payment."""
        return self in (
            PaymentStatus.REFUNDED,
            PaymentStatus.PARTIALLY_REFUNDED,
        )
    
    @property
    def display_name(self) -> str:
        """Get user-friendly display name."""
        display_names = {
            PaymentStatus.PENDING: "Pending",
            PaymentStatus.PROCESSING: "Processing",
            PaymentStatus.COMPLETED: "Completed",
            PaymentStatus.FAILED: "Failed",
            PaymentStatus.CANCELLED: "Cancelled",
            PaymentStatus.REFUNDED: "Refunded",
            PaymentStatus.PARTIALLY_REFUNDED: "Partially Refunded",
            PaymentStatus.EXPIRED: "Expired",
        }
        return display_names[self]
    
    @property
    def color(self) -> str:
        """Get color for UI display."""
        colors = {
            PaymentStatus.PENDING: "warning",
            PaymentStatus.PROCESSING: "info",
            PaymentStatus.COMPLETED: "success",
            PaymentStatus.FAILED: "error",
            PaymentStatus.CANCELLED: "default",
            PaymentStatus.REFUNDED: "secondary",
            PaymentStatus.PARTIALLY_REFUNDED: "secondary",
            PaymentStatus.EXPIRED: "error",
        }
        return colors[self]
    
    @classmethod
    def get_valid_transitions(cls) -> Dict["PaymentStatus", Set["PaymentStatus"]]:
        """
        Get valid status transitions.
        
        Returns:
            Dictionary mapping current status to set of valid next statuses
        """
        return {
            cls.PENDING: {cls.PROCESSING, cls.COMPLETED, cls.FAILED, cls.CANCELLED, cls.EXPIRED},
            cls.PROCESSING: {cls.COMPLETED, cls.FAILED, cls.CANCELLED},
            cls.COMPLETED: {cls.REFUNDED, cls.PARTIALLY_REFUNDED},
            cls.FAILED: set(),  # Final status
            cls.CANCELLED: set(),  # Final status
            cls.REFUNDED: set(),  # Final status
            cls.PARTIALLY_REFUNDED: {cls.REFUNDED},
            cls.EXPIRED: set(),  # Final status
        }
    
    def can_transition_to(self, new_status: "PaymentStatus") -> bool:
        """
        Check if transition to new status is valid.
        
        Args:
            new_status: Target status
            
        Returns:
            True if transition is valid, False otherwise
        """
        valid_transitions = self.get_valid_transitions()
        return new_status in valid_transitions.get(self, set())
    
    @classmethod
    def get_active_statuses(cls) -> Set["PaymentStatus"]:
        """Get statuses that represent active payments."""
        return {cls.PENDING, cls.PROCESSING, cls.COMPLETED, cls.PARTIALLY_REFUNDED}
    
    @classmethod
    def get_processable_statuses(cls) -> Set["PaymentStatus"]:
        """Get statuses that can be manually processed."""
        return {cls.PENDING}
    
    @classmethod
    def get_refundable_statuses(cls) -> Set["PaymentStatus"]:
        """Get statuses that allow refunds."""
        return {cls.COMPLETED, cls.PARTIALLY_REFUNDED}
    
    def __str__(self) -> str:
        """String representation."""
        return self.value
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"PaymentStatus.{self.name}" 