"""
Payment Repository Interface

Defines the contract for payment data access following the repository pattern.
Part of the domain layer - defines what operations are needed without implementation details.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.entities.payment import Payment, PaymentType
from app.domain.value_objects.payment_status import PaymentStatus
from app.domain.value_objects.payment_method import PaymentMethod


class IPaymentRepository(ABC):
    """
    Payment repository interface.
    
    Defines the contract for payment data access operations.
    Following the repository pattern from the Instructions file.
    """
    
    @abstractmethod
    async def create(self, payment: Payment) -> Payment:
        """
        Create a new payment.
        
        Args:
            payment: Payment entity to create
            
        Returns:
            Created payment entity
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, payment_id: UUID) -> Optional[Payment]:
        """
        Get payment by ID.
        
        Args:
            payment_id: Payment identifier
            
        Returns:
            Payment entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def update(self, payment: Payment) -> Payment:
        """
        Update an existing payment.
        
        Args:
            payment: Payment entity to update
            
        Returns:
            Updated payment entity
        """
        pass
    
    @abstractmethod
    async def delete(self, payment_id: UUID) -> bool:
        """
        Delete a payment.
        
        Args:
            payment_id: Payment identifier
            
        Returns:
            True if deleted, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_subscription_id(
        self, 
        subscription_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """
        Get payments for a subscription.
        
        Args:
            subscription_id: Subscription identifier
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of payment entities
        """
        pass
    
    @abstractmethod
    async def get_by_status(
        self, 
        status: PaymentStatus,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """
        Get payments by status.
        
        Args:
            status: Payment status
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of payment entities
        """
        pass
    
    @abstractmethod
    async def get_by_reference_id(self, reference_id: str) -> Optional[Payment]:
        """
        Get payment by reference ID.
        
        Args:
            reference_id: External reference identifier
            
        Returns:
            Payment entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def list_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_direction: str = "desc"
    ) -> List[Payment]:
        """
        List payments with optional filtering and pagination.
        
        Args:
            filters: Optional filter criteria
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by
            order_direction: Order direction (asc/desc)
            
        Returns:
            List of payment entities
        """
        pass
    
    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count payments with optional filtering.
        
        Args:
            filters: Optional filter criteria
            
        Returns:
            Number of payments matching criteria
        """
        pass
    
    @abstractmethod
    async def get_pending_payments(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """
        Get pending payments that require processing.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of pending payment entities
        """
        pass
    
    @abstractmethod
    async def get_failed_payments(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """
        Get failed payments for review.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of failed payment entities
        """
        pass
    
    @abstractmethod
    async def get_payments_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """
        Get payments within a date range.
        
        Args:
            start_date: Start date for range
            end_date: End date for range
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of payment entities
        """
        pass
    
    @abstractmethod
    async def get_refundable_payments(
        self,
        subscription_id: Optional[UUID] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """
        Get payments that can be refunded.
        
        Args:
            subscription_id: Optional subscription filter
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of refundable payment entities
        """
        pass
    
    @abstractmethod
    async def get_payment_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get payment analytics data.
        
        Args:
            start_date: Optional start date for analytics
            end_date: Optional end date for analytics
            
        Returns:
            Analytics data dictionary
        """
        pass
    
    @abstractmethod
    async def get_revenue_by_period(
        self,
        period: str,  # 'day', 'week', 'month', 'year'
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get revenue data grouped by period.
        
        Args:
            period: Grouping period (day, week, month, year)
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            List of revenue data points
        """
        pass
    
    @abstractmethod
    async def get_payment_methods_stats(self) -> Dict[str, Any]:
        """
        Get payment method statistics.
        
        Returns:
            Payment method statistics
        """
        pass
    
    @abstractmethod
    async def get_subscription_payment_history(
        self,
        subscription_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """
        Get complete payment history for a subscription.
        
        Args:
            subscription_id: Subscription identifier
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of payment entities ordered by date
        """
        pass


class IPaymentHistoryRepository(ABC):
    """
    Payment history repository interface.
    
    Defines the contract for payment history data access operations.
    """
    
    @abstractmethod
    async def create_history_entry(
        self,
        payment_id: UUID,
        old_status: Optional[PaymentStatus],
        new_status: PaymentStatus,
        action: str,
        admin_user_id: Optional[UUID] = None,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Create a payment history entry.
        
        Args:
            payment_id: Payment identifier
            old_status: Previous payment status
            new_status: New payment status
            action: Action performed
            admin_user_id: Admin user who performed the action
            reason: Reason for the change
            notes: Additional notes
            metadata: Additional metadata
        """
        pass
    
    @abstractmethod
    async def get_payment_history(
        self,
        payment_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get history entries for a payment.
        
        Args:
            payment_id: Payment identifier
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of history entries
        """
        pass
    
    @abstractmethod
    async def get_admin_activity(
        self,
        admin_user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get payment activity for an admin user.
        
        Args:
            admin_user_id: Admin user identifier
            start_date: Optional start date
            end_date: Optional end date
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of activity entries
        """
        pass 