"""
Payment Service

Contains business logic for payment operations following DDD principles.
Orchestrates payment workflows and enforces business rules.
"""

import structlog
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID, uuid4

from app.domain.entities.payment import Payment, PaymentType, PaymentException
from app.domain.repositories.payment_repository import IPaymentRepository, IPaymentHistoryRepository
from app.domain.value_objects.payment_status import PaymentStatus
from app.domain.value_objects.payment_method import PaymentMethod
from app.domain.value_objects.money import Money
from app.core.exceptions import BusinessLogicException, ValidationException

logger = structlog.get_logger(__name__)


class PaymentService:
    """
    Payment service containing business logic for payment operations.
    
    Orchestrates payment workflows and enforces business rules.
    Follows DDD principles with clear separation of concerns.
    """
    
    def __init__(
        self,
        payment_repository: IPaymentRepository,
        payment_history_repository: IPaymentHistoryRepository,
    ):
        """
        Initialize payment service with dependencies.
        
        Args:
            payment_repository: Payment repository interface
            payment_history_repository: Payment history repository interface
        """
        self.payment_repo = payment_repository
        self.history_repo = payment_history_repository
    
    async def create_payment(
        self,
        subscription_id: UUID,
        amount: Money,
        payment_method: PaymentMethod,
        payment_type: PaymentType,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Payment:
        """
        Create a new payment.
        
        Args:
            subscription_id: Associated subscription ID
            amount: Payment amount
            payment_method: Method of payment
            payment_type: Type of payment
            description: Payment description
            reference_id: External reference ID
            metadata: Additional metadata
            
        Returns:
            Created payment entity
            
        Raises:
            ValidationException: If payment data is invalid
            BusinessLogicException: If business rules are violated
        """
        try:
            logger.info(
                "Creating payment",
                subscription_id=str(subscription_id),
                amount=amount.amount,
                currency=amount.currency,
                payment_method=str(payment_method),
                payment_type=str(payment_type)
            )
            
            # Validate amount
            if amount.amount <= 0:
                raise ValidationException("Payment amount must be positive")
            
            # Check for duplicate reference ID if provided
            if reference_id:
                existing_payment = await self.payment_repo.get_by_reference_id(reference_id)
                if existing_payment:
                    raise BusinessLogicException(
                        f"Payment with reference ID {reference_id} already exists"
                    )
            
            # Comprehensive debug logging
            logger.info(
                "Creating Payment entity with detailed debug info",
                payment_method_type=type(payment_method).__name__,
                payment_method_value=payment_method,
                payment_method_str=str(payment_method),
                payment_type_type=type(payment_type).__name__,
                payment_type_value=payment_type,
                payment_type_str=str(payment_type),
                amount_type=type(amount).__name__,
                amount_value=amount,
                subscription_id=str(subscription_id)
            )
            
            # Create payment entity with comprehensive error handling
            try:
                payment = Payment(
                    id=uuid4(),
                    subscription_id=subscription_id,
                    amount=amount,
                    payment_method=payment_method,
                    payment_type=payment_type,
                    status=PaymentStatus.PENDING,
                    reference_id=reference_id,
                    description=description,
                    metadata=metadata or {},
                )
                logger.info("Payment entity created successfully", payment_id=str(payment.id))
            except Exception as e:
                logger.error(
                    "Error creating Payment entity",
                    error=str(e),
                    error_type=type(e).__name__,
                    payment_method=payment_method,
                    payment_type=payment_type,
                    traceback=str(e.__traceback__)
                )
                raise
            
            # Save payment with error handling
            try:
                logger.info("Attempting to save payment to repository")
                created_payment = await self.payment_repo.create(payment)
                logger.info("Payment saved successfully", payment_id=str(created_payment.id))
            except Exception as e:
                logger.error(
                    "Error saving payment to repository",
                    error=str(e),
                    error_type=type(e).__name__,
                    payment_id=str(payment.id)
                )
                raise
            
            # Create history entry
            await self.history_repo.create_history_entry(
                payment_id=created_payment.id,
                old_status=None,
                new_status=PaymentStatus.PENDING,
                action="created",
                reason="Payment created",
            )
            
            logger.info(
                "Payment created successfully",
                payment_id=str(created_payment.id),
                subscription_id=str(subscription_id)
            )
            
            return created_payment
            
        except PaymentException as e:
            logger.error("Payment creation failed", error=str(e))
            raise BusinessLogicException(f"Payment creation failed: {e}")
        except Exception as e:
            logger.error("Unexpected error creating payment", error=str(e))
            raise BusinessLogicException(f"Unexpected error creating payment: {e}")
    
    async def process_payment_manually(
        self,
        payment_id: UUID,
        admin_user_id: UUID,
        notes: Optional[str] = None,
    ) -> Payment:
        """
        Process a payment manually by admin.
        
        Args:
            payment_id: Payment identifier
            admin_user_id: Admin user processing the payment
            notes: Processing notes
            
        Returns:
            Updated payment entity
            
        Raises:
            BusinessLogicException: If payment cannot be processed
        """
        try:
            logger.info(
                "Processing payment manually",
                payment_id=str(payment_id),
                admin_user_id=str(admin_user_id)
            )
            
            # Get payment
            payment = await self.payment_repo.get_by_id(payment_id)
            if not payment:
                raise BusinessLogicException(f"Payment {payment_id} not found")
            
            # Validate payment can be processed
            if payment.is_processed:
                raise BusinessLogicException(
                    f"Payment {payment_id} is already processed with status {payment.status}"
                )
            
            # Store old status for history
            old_status = payment.status
            
            # Process payment
            payment.process_payment(admin_user_id, notes)
            
            # Update payment
            updated_payment = await self.payment_repo.update(payment)
            
            # Create history entry
            await self.history_repo.create_history_entry(
                payment_id=payment_id,
                old_status=old_status,
                new_status=PaymentStatus.COMPLETED,
                action="processed",
                admin_user_id=admin_user_id,
                reason="Manual processing",
                notes=notes,
            )
            
            logger.info(
                "Payment processed successfully",
                payment_id=str(payment_id),
                admin_user_id=str(admin_user_id)
            )
            
            return updated_payment
            
        except PaymentException as e:
            logger.error("Payment processing failed", payment_id=str(payment_id), error=str(e))
            raise BusinessLogicException(f"Payment processing failed: {e}")
        except Exception as e:
            logger.error("Unexpected error processing payment", error=str(e))
            raise BusinessLogicException(f"Unexpected error processing payment: {e}")
    
    async def fail_payment(
        self,
        payment_id: UUID,
        admin_user_id: UUID,
        reason: str,
    ) -> Payment:
        """
        Mark a payment as failed.
        
        Args:
            payment_id: Payment identifier
            admin_user_id: Admin user failing the payment
            reason: Reason for failure
            
        Returns:
            Updated payment entity
            
        Raises:
            BusinessLogicException: If payment cannot be failed
        """
        try:
            logger.info(
                "Failing payment",
                payment_id=str(payment_id),
                admin_user_id=str(admin_user_id),
                reason=reason
            )
            
            # Get payment
            payment = await self.payment_repo.get_by_id(payment_id)
            if not payment:
                raise BusinessLogicException(f"Payment {payment_id} not found")
            
            # Validate payment can be failed
            if payment.is_processed:
                raise BusinessLogicException(
                    f"Payment {payment_id} is already processed with status {payment.status}"
                )
            
            # Store old status for history
            old_status = payment.status
            
            # Fail payment
            payment.fail_payment(admin_user_id, reason)
            
            # Update payment
            updated_payment = await self.payment_repo.update(payment)
            
            # Create history entry
            await self.history_repo.create_history_entry(
                payment_id=payment_id,
                old_status=old_status,
                new_status=PaymentStatus.FAILED,
                action="failed",
                admin_user_id=admin_user_id,
                reason=reason,
            )
            
            logger.info(
                "Payment failed successfully",
                payment_id=str(payment_id),
                admin_user_id=str(admin_user_id)
            )
            
            return updated_payment
            
        except PaymentException as e:
            logger.error("Payment failure failed", payment_id=str(payment_id), error=str(e))
            raise BusinessLogicException(f"Payment failure failed: {e}")
        except Exception as e:
            logger.error("Unexpected error failing payment", error=str(e))
            raise BusinessLogicException(f"Unexpected error failing payment: {e}")
    
    async def refund_payment(
        self,
        payment_id: UUID,
        admin_user_id: UUID,
        reason: str,
    ) -> Tuple[Payment, Payment]:
        """
        Refund a payment.
        
        Args:
            payment_id: Payment identifier to refund
            admin_user_id: Admin user creating the refund
            reason: Reason for refund
            
        Returns:
            Tuple of (original payment, refund payment)
            
        Raises:
            BusinessLogicException: If payment cannot be refunded
        """
        try:
            logger.info(
                "Refunding payment",
                payment_id=str(payment_id),
                admin_user_id=str(admin_user_id),
                reason=reason
            )
            
            # Get payment
            payment = await self.payment_repo.get_by_id(payment_id)
            if not payment:
                raise BusinessLogicException(f"Payment {payment_id} not found")
            
            # Validate payment can be refunded
            if not payment.can_be_refunded:
                raise BusinessLogicException(
                    f"Payment {payment_id} cannot be refunded. Status: {payment.status}"
                )
            
            # Store old status for history
            old_status = payment.status
            
            # Create refund
            refund_payment = payment.refund_payment(admin_user_id, reason)
            
            # Save both payments
            updated_original = await self.payment_repo.update(payment)
            created_refund = await self.payment_repo.create(refund_payment)
            
            # Create history entries
            await self.history_repo.create_history_entry(
                payment_id=payment_id,
                old_status=old_status,
                new_status=PaymentStatus.REFUNDED,
                action="refunded",
                admin_user_id=admin_user_id,
                reason=reason,
            )
            
            await self.history_repo.create_history_entry(
                payment_id=created_refund.id,
                old_status=None,
                new_status=PaymentStatus.COMPLETED,
                action="created_refund",
                admin_user_id=admin_user_id,
                reason=f"Refund for payment {payment_id}",
            )
            
            logger.info(
                "Payment refunded successfully",
                original_payment_id=str(payment_id),
                refund_payment_id=str(created_refund.id),
                admin_user_id=str(admin_user_id)
            )
            
            return updated_original, created_refund
            
        except PaymentException as e:
            logger.error("Payment refund failed", payment_id=str(payment_id), error=str(e))
            raise BusinessLogicException(f"Payment refund failed: {e}")
        except Exception as e:
            logger.error("Unexpected error refunding payment", error=str(e))
            raise BusinessLogicException(f"Unexpected error refunding payment: {e}")
    
    async def add_payment_note(
        self,
        payment_id: UUID,
        admin_user_id: UUID,
        note: str,
    ) -> Payment:
        """
        Add a note to a payment.
        
        Args:
            payment_id: Payment identifier
            admin_user_id: Admin user adding the note
            note: Note to add
            
        Returns:
            Updated payment entity
            
        Raises:
            BusinessLogicException: If payment not found
        """
        try:
            logger.info(
                "Adding payment note",
                payment_id=str(payment_id),
                admin_user_id=str(admin_user_id)
            )
            
            # Get payment
            payment = await self.payment_repo.get_by_id(payment_id)
            if not payment:
                raise BusinessLogicException(f"Payment {payment_id} not found")
            
            # Add note
            payment.add_note(note, admin_user_id)
            
            # Update payment
            updated_payment = await self.payment_repo.update(payment)
            
            # Create history entry
            await self.history_repo.create_history_entry(
                payment_id=payment_id,
                old_status=payment.status,
                new_status=payment.status,
                action="note_added",
                admin_user_id=admin_user_id,
                notes=note,
            )
            
            logger.info(
                "Payment note added successfully",
                payment_id=str(payment_id),
                admin_user_id=str(admin_user_id)
            )
            
            return updated_payment
            
        except Exception as e:
            logger.error("Unexpected error adding payment note", error=str(e))
            raise BusinessLogicException(f"Unexpected error adding payment note: {e}")
    
    async def get_payment_by_id(self, payment_id: UUID) -> Optional[Payment]:
        """
        Get a payment by ID.
        
        Args:
            payment_id: Payment identifier
            
        Returns:
            Payment entity if found, None otherwise
        """
        try:
            return await self.payment_repo.get_by_id(payment_id)
        except Exception as e:
            logger.error("Failed to get payment by ID", payment_id=str(payment_id), error=str(e))
            raise BusinessLogicException(f"Failed to get payment: {e}")
    
    async def get_payments_for_subscription(
        self,
        subscription_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """
        Get all payments for a subscription.
        
        Args:
            subscription_id: Subscription identifier
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of payment entities
        """
        try:
            return await self.payment_repo.get_by_subscription_id(
                subscription_id, limit, offset
            )
        except Exception as e:
            logger.error(
                "Failed to get payments for subscription",
                subscription_id=str(subscription_id),
                error=str(e)
            )
            raise BusinessLogicException(f"Failed to get payments for subscription: {e}")
    
    async def get_pending_payments(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """
        Get all pending payments requiring admin action.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of pending payment entities
        """
        try:
            return await self.payment_repo.get_pending_payments(limit, offset)
        except Exception as e:
            logger.error("Failed to get pending payments", error=str(e))
            raise BusinessLogicException(f"Failed to get pending payments: {e}")
    
    async def get_failed_payments(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """
        Get all failed payments for review.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of failed payment entities
        """
        try:
            return await self.payment_repo.get_failed_payments(limit, offset)
        except Exception as e:
            logger.error("Failed to get failed payments", error=str(e))
            raise BusinessLogicException(f"Failed to get failed payments: {e}")
    
    async def search_payments(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_direction: str = "desc"
    ) -> Tuple[List[Payment], int]:
        """
        Search payments with filters and pagination.
        
        Args:
            filters: Search filters
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by
            order_direction: Order direction (asc/desc)
            
        Returns:
            Tuple of (payment list, total count)
        """
        try:
            payments = await self.payment_repo.list_all(
                filters, limit, offset, order_by, order_direction
            )
            total_count = await self.payment_repo.count(filters)
            
            return payments, total_count
        except Exception as e:
            logger.error("Failed to search payments", error=str(e))
            raise BusinessLogicException(f"Failed to search payments: {e}")
    
    async def get_payment_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get payment analytics and statistics.
        
        Args:
            start_date: Optional start date for analytics
            end_date: Optional end date for analytics
            
        Returns:
            Analytics data dictionary
        """
        try:
            return await self.payment_repo.get_payment_analytics(start_date, end_date)
        except Exception as e:
            logger.error("Failed to get payment analytics", error=str(e))
            raise BusinessLogicException(f"Failed to get payment analytics: {e}")
    
    async def get_revenue_by_period(
        self,
        period: str,
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
        try:
            return await self.payment_repo.get_revenue_by_period(
                period, start_date, end_date
            )
        except Exception as e:
            logger.error("Failed to get revenue by period", error=str(e))
            raise BusinessLogicException(f"Failed to get revenue by period: {e}")
    
    async def get_payment_methods_stats(self) -> Dict[str, Any]:
        """
        Get payment method statistics.
        
        Returns:
            Payment method statistics
        """
        try:
            return await self.payment_repo.get_payment_methods_stats()
        except Exception as e:
            logger.error("Failed to get payment methods stats", error=str(e))
            raise BusinessLogicException(f"Failed to get payment methods stats: {e}")
    
    async def get_payment_history(
        self,
        payment_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get payment history entries.
        
        Args:
            payment_id: Payment identifier
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of history entries
        """
        try:
            return await self.history_repo.get_payment_history(
                payment_id, limit, offset
            )
        except Exception as e:
            logger.error("Failed to get payment history", error=str(e))
            raise BusinessLogicException(f"Failed to get payment history: {e}")
    
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
        try:
            return await self.history_repo.get_admin_activity(
                admin_user_id, start_date, end_date, limit, offset
            )
        except Exception as e:
            logger.error("Failed to get admin activity", error=str(e))
            raise BusinessLogicException(f"Failed to get admin activity: {e}")
    
    async def bulk_process_payments(
        self,
        payment_ids: List[UUID],
        admin_user_id: UUID,
        action: str,  # 'process', 'fail'
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process multiple payments in bulk.
        
        Args:
            payment_ids: List of payment identifiers
            admin_user_id: Admin user performing the action
            action: Action to perform ('process' or 'fail')
            reason: Reason for the action
            
        Returns:
            Results summary
        """
        try:
            logger.info(
                "Processing payments in bulk",
                payment_count=len(payment_ids),
                admin_user_id=str(admin_user_id),
                action=action
            )
            
            successful = []
            failed = []
            
            for payment_id in payment_ids:
                try:
                    if action == "process":
                        await self.process_payment_manually(payment_id, admin_user_id, reason)
                    elif action == "fail":
                        await self.fail_payment(payment_id, admin_user_id, reason or "Bulk failure")
                    else:
                        raise ValueError(f"Invalid action: {action}")
                    
                    successful.append(str(payment_id))
                except Exception as e:
                    failed.append({"payment_id": str(payment_id), "error": str(e)})
            
            logger.info(
                "Bulk payment processing completed",
                successful_count=len(successful),
                failed_count=len(failed),
                admin_user_id=str(admin_user_id)
            )
            
            return {
                "successful": successful,
                "failed": failed,
                "total": len(payment_ids),
                "success_count": len(successful),
                "failure_count": len(failed),
            }
            
        except Exception as e:
            logger.error("Bulk payment processing failed", error=str(e))
            raise BusinessLogicException(f"Bulk payment processing failed: {e}")
    
    def get_payment_status_summary(self, payments: List[Payment]) -> Dict[str, Any]:
        """
        Get a summary of payment statuses.
        
        Args:
            payments: List of payment entities
            
        Returns:
            Status summary dictionary
        """
        try:
            summary = {
                "total": len(payments),
                "by_status": {},
                "by_method": {},
                "total_amount": Decimal("0"),
                "completed_amount": Decimal("0"),
            }
            
            for payment in payments:
                # Count by status
                status = payment.status.value
                summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
                
                # Count by method
                method = payment.payment_method.value
                summary["by_method"][method] = summary["by_method"].get(method, 0) + 1
                
                # Sum amounts
                summary["total_amount"] += payment.amount.amount
                if payment.is_successful:
                    summary["completed_amount"] += payment.amount.amount
            
            return summary
            
        except Exception as e:
            logger.error("Failed to get payment status summary", error=str(e))
            raise BusinessLogicException(f"Failed to get payment status summary: {e}") 