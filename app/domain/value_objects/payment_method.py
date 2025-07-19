"""
Payment Method Value Object

Represents payment methods in the subscription system following DDD principles.
Immutable value object with proper validation and business rules.
"""

from enum import Enum
from typing import Dict, Optional, Set


class PaymentMethod(str, Enum):
    """
    Payment method enumeration.
    
    Represents all supported payment methods in the system.
    """
    
    MANUAL = "manual"
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    CASH = "cash"
    CHECK = "check"
    WIRE_TRANSFER = "wire_transfer"
    CRYPTOCURRENCY = "cryptocurrency"
    OTHER = "other"
    
    @property
    def display_name(self) -> str:
        """Get user-friendly display name."""
        display_names = {
            PaymentMethod.MANUAL: "Manual Payment",
            PaymentMethod.BANK_TRANSFER: "Bank Transfer",
            PaymentMethod.CREDIT_CARD: "Credit Card",
            PaymentMethod.DEBIT_CARD: "Debit Card",
            PaymentMethod.PAYPAL: "PayPal",
            PaymentMethod.STRIPE: "Stripe",
            PaymentMethod.CASH: "Cash",
            PaymentMethod.CHECK: "Check",
            PaymentMethod.WIRE_TRANSFER: "Wire Transfer",
            PaymentMethod.CRYPTOCURRENCY: "Cryptocurrency",
            PaymentMethod.OTHER: "Other",
        }
        return display_names[self]
    
    @property
    def is_automated(self) -> bool:
        """Check if this is an automated payment method."""
        automated_methods = {
            PaymentMethod.CREDIT_CARD,
            PaymentMethod.DEBIT_CARD,
            PaymentMethod.PAYPAL,
            PaymentMethod.STRIPE,
        }
        return self in automated_methods
    
    @property
    def is_manual(self) -> bool:
        """Check if this is a manual payment method."""
        manual_methods = {
            PaymentMethod.MANUAL,
            PaymentMethod.BANK_TRANSFER,
            PaymentMethod.CASH,
            PaymentMethod.CHECK,
            PaymentMethod.WIRE_TRANSFER,
            PaymentMethod.CRYPTOCURRENCY,
            PaymentMethod.OTHER,
        }
        return self in manual_methods
    
    @property
    def requires_verification(self) -> bool:
        """Check if this payment method requires admin verification."""
        verification_required = {
            PaymentMethod.MANUAL,
            PaymentMethod.BANK_TRANSFER,
            PaymentMethod.CASH,
            PaymentMethod.CHECK,
            PaymentMethod.WIRE_TRANSFER,
            PaymentMethod.CRYPTOCURRENCY,
        }
        return self in verification_required
    
    @property
    def icon(self) -> str:
        """Get icon name for UI display."""
        icons = {
            PaymentMethod.MANUAL: "edit",
            PaymentMethod.BANK_TRANSFER: "account_balance",
            PaymentMethod.CREDIT_CARD: "credit_card",
            PaymentMethod.DEBIT_CARD: "credit_card",
            PaymentMethod.PAYPAL: "paypal",
            PaymentMethod.STRIPE: "stripe",
            PaymentMethod.CASH: "attach_money",
            PaymentMethod.CHECK: "receipt",
            PaymentMethod.WIRE_TRANSFER: "send",
            PaymentMethod.CRYPTOCURRENCY: "currency_bitcoin",
            PaymentMethod.OTHER: "payment",
        }
        return icons[self]
    
    @property
    def color(self) -> str:
        """Get color for UI display."""
        colors = {
            PaymentMethod.MANUAL: "primary",
            PaymentMethod.BANK_TRANSFER: "info",
            PaymentMethod.CREDIT_CARD: "success",
            PaymentMethod.DEBIT_CARD: "success",
            PaymentMethod.PAYPAL: "warning",
            PaymentMethod.STRIPE: "secondary",
            PaymentMethod.CASH: "success",
            PaymentMethod.CHECK: "info",
            PaymentMethod.WIRE_TRANSFER: "primary",
            PaymentMethod.CRYPTOCURRENCY: "warning",
            PaymentMethod.OTHER: "default",
        }
        return colors[self]
    
    @classmethod
    def get_manual_methods(cls) -> Set["PaymentMethod"]:
        """Get all manual payment methods."""
        return {
            cls.MANUAL,
            cls.BANK_TRANSFER,
            cls.CASH,
            cls.CHECK,
            cls.WIRE_TRANSFER,
            cls.CRYPTOCURRENCY,
            cls.OTHER,
        }
    
    @classmethod
    def get_automated_methods(cls) -> Set["PaymentMethod"]:
        """Get all automated payment methods."""
        return {
            cls.CREDIT_CARD,
            cls.DEBIT_CARD,
            cls.PAYPAL,
            cls.STRIPE,
        }
    
    @classmethod
    def get_admin_verifiable_methods(cls) -> Set["PaymentMethod"]:
        """Get payment methods that can be verified by admin."""
        return {
            cls.MANUAL,
            cls.BANK_TRANSFER,
            cls.CASH,
            cls.CHECK,
            cls.WIRE_TRANSFER,
            cls.CRYPTOCURRENCY,
        }
    
    def get_processing_time(self) -> str:
        """Get expected processing time for this payment method."""
        processing_times = {
            PaymentMethod.MANUAL: "Immediate (admin verification)",
            PaymentMethod.BANK_TRANSFER: "1-3 business days",
            PaymentMethod.CREDIT_CARD: "Immediate",
            PaymentMethod.DEBIT_CARD: "Immediate",
            PaymentMethod.PAYPAL: "Immediate",
            PaymentMethod.STRIPE: "Immediate",
            PaymentMethod.CASH: "Immediate (admin verification)",
            PaymentMethod.CHECK: "3-5 business days",
            PaymentMethod.WIRE_TRANSFER: "1-2 business days",
            PaymentMethod.CRYPTOCURRENCY: "10-60 minutes",
            PaymentMethod.OTHER: "Varies",
        }
        return processing_times[self]
    
    def get_fees(self) -> str:
        """Get fee structure for this payment method."""
        fees = {
            PaymentMethod.MANUAL: "No fees",
            PaymentMethod.BANK_TRANSFER: "Bank charges may apply",
            PaymentMethod.CREDIT_CARD: "2.9% + $0.30",
            PaymentMethod.DEBIT_CARD: "2.9% + $0.30",
            PaymentMethod.PAYPAL: "2.9% + $0.30",
            PaymentMethod.STRIPE: "2.9% + $0.30",
            PaymentMethod.CASH: "No fees",
            PaymentMethod.CHECK: "No fees",
            PaymentMethod.WIRE_TRANSFER: "Wire transfer fees apply",
            PaymentMethod.CRYPTOCURRENCY: "Network fees apply",
            PaymentMethod.OTHER: "Varies",
        }
        return fees[self]
    
    def get_required_fields(self) -> Dict[str, bool]:
        """
        Get required fields for this payment method.
        
        Returns:
            Dictionary with field names as keys and required status as values
        """
        base_fields = {
            "amount": True,
            "currency": True,
            "description": False,
            "reference_id": False,
        }
        
        method_specific_fields = {
            PaymentMethod.MANUAL: {
                "notes": True,
                "admin_verification": True,
            },
            PaymentMethod.BANK_TRANSFER: {
                "account_number": True,
                "routing_number": True,
                "bank_name": True,
                "account_holder": True,
            },
            PaymentMethod.CREDIT_CARD: {
                "card_number": True,
                "expiry_date": True,
                "cvv": True,
                "card_holder": True,
            },
            PaymentMethod.DEBIT_CARD: {
                "card_number": True,
                "expiry_date": True,
                "cvv": True,
                "card_holder": True,
            },
            PaymentMethod.PAYPAL: {
                "paypal_email": True,
                "paypal_transaction_id": False,
            },
            PaymentMethod.STRIPE: {
                "stripe_payment_intent_id": True,
                "stripe_customer_id": False,
            },
            PaymentMethod.CASH: {
                "receipt_number": False,
                "location": True,
                "received_by": True,
            },
            PaymentMethod.CHECK: {
                "check_number": True,
                "bank_name": True,
                "account_holder": True,
                "check_date": True,
            },
            PaymentMethod.WIRE_TRANSFER: {
                "wire_reference": True,
                "sending_bank": True,
                "receiving_bank": True,
                "swift_code": False,
            },
            PaymentMethod.CRYPTOCURRENCY: {
                "crypto_currency": True,
                "wallet_address": True,
                "transaction_hash": True,
                "network": True,
            },
            PaymentMethod.OTHER: {
                "payment_details": True,
                "notes": True,
            },
        }
        
        return {**base_fields, **method_specific_fields.get(self, {})}
    
    def __str__(self) -> str:
        """String representation."""
        return self.value
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"PaymentMethod.{self.name}" 