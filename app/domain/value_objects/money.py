"""
Money Value Object

Represents monetary amounts with currency in the subscription system.
Immutable value object following DDD principles and Instructions file standards.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Union
from app.core.exceptions import ValidationException


class Money:
    """
    Money value object representing an amount with currency.
    
    Immutable value object with proper validation and business rules.
    Follows Instructions file standards for value objects.
    """
    
    # Supported currencies with their decimal places
    SUPPORTED_CURRENCIES = {
        "USD": 2,
        "EUR": 2,
        "GBP": 2,
        "CAD": 2,
        "AUD": 2,
        "JPY": 0,
        "CHF": 2,
        "CNY": 2,
        "INR": 2,
        "BRL": 2,
    }
    
    def __init__(self, amount: Union[str, float, Decimal], currency: str = "USD"):
        """
        Initialize Money value object.
        
        Args:
            amount: Monetary amount
            currency: Currency code (ISO 4217)
            
        Raises:
            ValidationException: If amount or currency is invalid
        """
        self._validate_currency(currency)
        self._currency = currency.upper()
        self._amount = self._validate_and_normalize_amount(amount)
    
    @property
    def amount(self) -> Decimal:
        """Get the monetary amount."""
        return self._amount
    
    @property
    def currency(self) -> str:
        """Get the currency code."""
        return self._currency
    
    @property
    def currency_symbol(self) -> str:
        """Get the currency symbol."""
        symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "CAD": "C$",
            "AUD": "A$",
            "JPY": "¥",
            "CHF": "CHF",
            "CNY": "¥",
            "INR": "₹",
            "BRL": "R$",
        }
        return symbols.get(self._currency, self._currency)
    
    def _validate_currency(self, currency: str) -> None:
        """Validate currency code."""
        if not currency:
            raise ValidationException("Currency code cannot be empty")
        
        currency_upper = currency.upper()
        if currency_upper not in self.SUPPORTED_CURRENCIES:
            raise ValidationException(
                f"Unsupported currency: {currency}. "
                f"Supported currencies: {', '.join(self.SUPPORTED_CURRENCIES.keys())}"
            )
    
    def _validate_and_normalize_amount(self, amount: Union[str, float, Decimal]) -> Decimal:
        """Validate and normalize the amount."""
        try:
            # Convert to Decimal for precision
            if isinstance(amount, str):
                decimal_amount = Decimal(amount)
            elif isinstance(amount, float):
                # Convert float to string first to avoid precision issues
                decimal_amount = Decimal(str(amount))
            elif isinstance(amount, Decimal):
                decimal_amount = amount
            else:
                raise ValidationException(f"Invalid amount type: {type(amount)}")
            
            # Validate amount is not negative
            if decimal_amount < 0:
                raise ValidationException("Amount cannot be negative")
            
            # Round to appropriate decimal places for currency
            decimal_places = self.SUPPORTED_CURRENCIES[self._currency]
            normalized_amount = decimal_amount.quantize(
                Decimal('0.1') ** decimal_places,
                rounding=ROUND_HALF_UP
            )
            
            return normalized_amount
            
        except (ValueError, TypeError) as e:
            raise ValidationException(f"Invalid amount: {amount}") from e
    
    def add(self, other: "Money") -> "Money":
        """Add another Money object."""
        self._validate_same_currency(other)
        return Money(self._amount + other._amount, self._currency)
    
    def subtract(self, other: "Money") -> "Money":
        """Subtract another Money object."""
        self._validate_same_currency(other)
        result_amount = self._amount - other._amount
        if result_amount < 0:
            raise ValidationException("Result cannot be negative")
        return Money(result_amount, self._currency)
    
    def multiply(self, factor: Union[int, float, Decimal]) -> "Money":
        """Multiply by a numeric factor."""
        if factor < 0:
            raise ValidationException("Factor cannot be negative")
        return Money(self._amount * Decimal(str(factor)), self._currency)
    
    def divide(self, divisor: Union[int, float, Decimal]) -> "Money":
        """Divide by a numeric divisor."""
        if divisor <= 0:
            raise ValidationException("Divisor must be positive")
        return Money(self._amount / Decimal(str(divisor)), self._currency)
    
    def is_zero(self) -> bool:
        """Check if amount is zero."""
        return self._amount == 0
    
    def is_positive(self) -> bool:
        """Check if amount is positive."""
        return self._amount > 0
    
    def _validate_same_currency(self, other: "Money") -> None:
        """Validate that both Money objects have the same currency."""
        if self._currency != other._currency:
            raise ValidationException(
                f"Cannot operate on different currencies: {self._currency} and {other._currency}"
            )
    
    def format(self, include_symbol: bool = True) -> str:
        """
        Format money as string.
        
        Args:
            include_symbol: Whether to include currency symbol
            
        Returns:
            Formatted money string
        """
        decimal_places = self.SUPPORTED_CURRENCIES[self._currency]
        
        if decimal_places == 0:
            amount_str = f"{self._amount:,.0f}"
        else:
            amount_str = f"{self._amount:,.{decimal_places}f}"
        
        if include_symbol:
            return f"{self.currency_symbol}{amount_str}"
        else:
            return f"{amount_str} {self._currency}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "amount": str(self._amount),
            "currency": self._currency,
            "formatted": self.format(),
        }
    
    @classmethod
    def zero(cls, currency: str = "USD") -> "Money":
        """Create a zero Money object."""
        return cls(Decimal("0"), currency)
    
    @classmethod
    def from_cents(cls, cents: int, currency: str = "USD") -> "Money":
        """
        Create Money from cents/smallest currency unit.
        
        Args:
            cents: Amount in cents (e.g., 299 for $2.99)
            currency: Currency code
            
        Returns:
            Money object
        """
        decimal_places = cls.SUPPORTED_CURRENCIES.get(currency.upper(), 2)
        amount = Decimal(cents) / (10 ** decimal_places)
        return cls(amount, currency)
    
    def to_cents(self) -> int:
        """Convert to cents/smallest currency unit."""
        decimal_places = self.SUPPORTED_CURRENCIES[self._currency]
        return int(self._amount * (10 ** decimal_places))
    
    def __eq__(self, other: object) -> bool:
        """Check equality with another Money object."""
        if not isinstance(other, Money):
            return False
        return self._amount == other._amount and self._currency == other._currency
    
    def __lt__(self, other: "Money") -> bool:
        """Less than comparison."""
        self._validate_same_currency(other)
        return self._amount < other._amount
    
    def __le__(self, other: "Money") -> bool:
        """Less than or equal comparison."""
        self._validate_same_currency(other)
        return self._amount <= other._amount
    
    def __gt__(self, other: "Money") -> bool:
        """Greater than comparison."""
        self._validate_same_currency(other)
        return self._amount > other._amount
    
    def __ge__(self, other: "Money") -> bool:
        """Greater than or equal comparison."""
        self._validate_same_currency(other)
        return self._amount >= other._amount
    
    def __hash__(self) -> int:
        """Hash for use in sets and dictionaries."""
        return hash((self._amount, self._currency))
    
    def __str__(self) -> str:
        """String representation."""
        return self.format()
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"Money(amount={self._amount}, currency='{self._currency}')" 