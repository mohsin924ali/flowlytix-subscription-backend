"""
Payment Repository Implementation

SQLAlchemy implementation of the payment repository interface.
Part of the infrastructure layer - handles database operations.
"""

import structlog
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities.payment import Payment, PaymentType
from app.domain.repositories.payment_repository import IPaymentRepository, IPaymentHistoryRepository
from app.domain.value_objects.payment_status import PaymentStatus
from app.domain.value_objects.payment_method import PaymentMethod
from app.domain.value_objects.money import Money
from app.infrastructure.database.models.payment import PaymentModel, PaymentHistoryModel
from app.core.exceptions import RepositoryException

logger = structlog.get_logger(__name__)


class PaymentRepository(IPaymentRepository):
    """
    Payment repository implementation using SQLAlchemy.
    
    Implements the payment repository interface for database operations.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def create(self, payment: Payment) -> Payment:
        """Create a new payment."""
        try:
            payment_model = PaymentModel.from_domain(payment)
            self.session.add(payment_model)
            await self.session.flush()
            await self.session.refresh(payment_model)
            
            logger.info(
                "Payment created",
                payment_id=str(payment.id),
                subscription_id=str(payment.subscription_id),
                amount=payment.amount.amount,
                currency=payment.amount.currency,
                status=str(payment.status)
            )
            
            return payment_model.to_domain()
        except Exception as e:
            logger.error("Failed to create payment", error=str(e))
            raise RepositoryException(f"Failed to create payment: {e}")
    
    async def get_by_id(self, payment_id: UUID) -> Optional[Payment]:
        """Get payment by ID."""
        try:
            stmt = select(PaymentModel).where(PaymentModel.id == payment_id)
            result = await self.session.execute(stmt)
            payment_model = result.scalar_one_or_none()
            
            if payment_model:
                return payment_model.to_domain()
            return None
        except Exception as e:
            logger.error("Failed to get payment by ID", payment_id=str(payment_id), error=str(e))
            raise RepositoryException(f"Failed to get payment by ID: {e}")
    
    async def update(self, payment: Payment) -> Payment:
        """Update an existing payment."""
        try:
            stmt = select(PaymentModel).where(PaymentModel.id == payment.id)
            result = await self.session.execute(stmt)
            payment_model = result.scalar_one_or_none()
            
            if not payment_model:
                raise RepositoryException(f"Payment {payment.id} not found")
            
            # Update fields
            payment_model.amount = float(payment.amount.amount)
            payment_model.currency = payment.amount.currency
            payment_model.payment_method = payment.payment_method
            payment_model.payment_type = payment.payment_type
            payment_model.status = payment.status
            payment_model.reference_id = payment.reference_id
            payment_model.description = payment.description
            payment_model.notes = payment.notes
            payment_model.metadata_json = payment.metadata
            payment_model.updated_at = payment.updated_at
            payment_model.processed_at = payment.processed_at
            payment_model.admin_user_id = payment.admin_user_id
            
            await self.session.flush()
            await self.session.refresh(payment_model)
            
            logger.info(
                "Payment updated",
                payment_id=str(payment.id),
                status=str(payment.status)
            )
            
            return payment_model.to_domain()
        except Exception as e:
            logger.error("Failed to update payment", payment_id=str(payment.id), error=str(e))
            raise RepositoryException(f"Failed to update payment: {e}")
    
    async def delete(self, payment_id: UUID) -> bool:
        """Delete a payment."""
        try:
            stmt = select(PaymentModel).where(PaymentModel.id == payment_id)
            result = await self.session.execute(stmt)
            payment_model = result.scalar_one_or_none()
            
            if payment_model:
                await self.session.delete(payment_model)
                await self.session.flush()
                
                logger.info("Payment deleted", payment_id=str(payment_id))
                return True
            return False
        except Exception as e:
            logger.error("Failed to delete payment", payment_id=str(payment_id), error=str(e))
            raise RepositoryException(f"Failed to delete payment: {e}")
    
    async def get_by_subscription_id(
        self, 
        subscription_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """Get payments for a subscription."""
        try:
            stmt = select(PaymentModel).where(
                PaymentModel.subscription_id == subscription_id
            ).order_by(desc(PaymentModel.created_at))
            
            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            
            result = await self.session.execute(stmt)
            payment_models = result.scalars().all()
            
            return [model.to_domain() for model in payment_models]
        except Exception as e:
            logger.error(
                "Failed to get payments by subscription ID",
                subscription_id=str(subscription_id),
                error=str(e)
            )
            raise RepositoryException(f"Failed to get payments by subscription ID: {e}")
    
    async def get_by_status(
        self, 
        status: PaymentStatus,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """Get payments by status."""
        try:
            stmt = select(PaymentModel).where(
                PaymentModel.status == status
            ).order_by(desc(PaymentModel.created_at))
            
            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            
            result = await self.session.execute(stmt)
            payment_models = result.scalars().all()
            
            return [model.to_domain() for model in payment_models]
        except Exception as e:
            logger.error("Failed to get payments by status", status=str(status), error=str(e))
            raise RepositoryException(f"Failed to get payments by status: {e}")
    
    async def get_by_reference_id(self, reference_id: str) -> Optional[Payment]:
        """Get payment by reference ID."""
        try:
            stmt = select(PaymentModel).where(PaymentModel.reference_id == reference_id)
            result = await self.session.execute(stmt)
            payment_model = result.scalar_one_or_none()
            
            if payment_model:
                return payment_model.to_domain()
            return None
        except Exception as e:
            logger.error("Failed to get payment by reference ID", reference_id=reference_id, error=str(e))
            raise RepositoryException(f"Failed to get payment by reference ID: {e}")
    
    async def list_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_direction: str = "desc"
    ) -> List[Payment]:
        """List payments with optional filtering and pagination."""
        try:
            stmt = select(PaymentModel)
            
            # Apply filters
            if filters:
                if "status" in filters:
                    if isinstance(filters["status"], list):
                        stmt = stmt.where(PaymentModel.status.in_(filters["status"]))
                    else:
                        stmt = stmt.where(PaymentModel.status == filters["status"])
                
                if "payment_method" in filters:
                    if isinstance(filters["payment_method"], list):
                        stmt = stmt.where(PaymentModel.payment_method.in_(filters["payment_method"]))
                    else:
                        stmt = stmt.where(PaymentModel.payment_method == filters["payment_method"])
                
                if "payment_type" in filters:
                    if isinstance(filters["payment_type"], list):
                        stmt = stmt.where(PaymentModel.payment_type.in_(filters["payment_type"]))
                    else:
                        stmt = stmt.where(PaymentModel.payment_type == filters["payment_type"])
                
                if "subscription_id" in filters:
                    stmt = stmt.where(PaymentModel.subscription_id == filters["subscription_id"])
                
                if "admin_user_id" in filters:
                    stmt = stmt.where(PaymentModel.admin_user_id == filters["admin_user_id"])
                
                if "start_date" in filters:
                    stmt = stmt.where(PaymentModel.created_at >= filters["start_date"])
                
                if "end_date" in filters:
                    stmt = stmt.where(PaymentModel.created_at <= filters["end_date"])
                
                if "min_amount" in filters:
                    stmt = stmt.where(PaymentModel.amount >= filters["min_amount"])
                
                if "max_amount" in filters:
                    stmt = stmt.where(PaymentModel.amount <= filters["max_amount"])
                
                if "currency" in filters:
                    stmt = stmt.where(PaymentModel.currency == filters["currency"])
            
            # Apply ordering
            order_field = getattr(PaymentModel, order_by, PaymentModel.created_at)
            if order_direction.lower() == "asc":
                stmt = stmt.order_by(asc(order_field))
            else:
                stmt = stmt.order_by(desc(order_field))
            
            # Apply pagination
            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            
            result = await self.session.execute(stmt)
            payment_models = result.scalars().all()
            
            return [model.to_domain() for model in payment_models]
        except Exception as e:
            logger.error("Failed to list payments", error=str(e))
            raise RepositoryException(f"Failed to list payments: {e}")
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count payments with optional filtering."""
        try:
            stmt = select(func.count(PaymentModel.id))
            
            # Apply filters (same as in list_all)
            if filters:
                if "status" in filters:
                    if isinstance(filters["status"], list):
                        stmt = stmt.where(PaymentModel.status.in_(filters["status"]))
                    else:
                        stmt = stmt.where(PaymentModel.status == filters["status"])
                
                if "payment_method" in filters:
                    if isinstance(filters["payment_method"], list):
                        stmt = stmt.where(PaymentModel.payment_method.in_(filters["payment_method"]))
                    else:
                        stmt = stmt.where(PaymentModel.payment_method == filters["payment_method"])
                
                if "payment_type" in filters:
                    if isinstance(filters["payment_type"], list):
                        stmt = stmt.where(PaymentModel.payment_type.in_(filters["payment_type"]))
                    else:
                        stmt = stmt.where(PaymentModel.payment_type == filters["payment_type"])
                
                if "subscription_id" in filters:
                    stmt = stmt.where(PaymentModel.subscription_id == filters["subscription_id"])
                
                if "admin_user_id" in filters:
                    stmt = stmt.where(PaymentModel.admin_user_id == filters["admin_user_id"])
                
                if "start_date" in filters:
                    stmt = stmt.where(PaymentModel.created_at >= filters["start_date"])
                
                if "end_date" in filters:
                    stmt = stmt.where(PaymentModel.created_at <= filters["end_date"])
                
                if "min_amount" in filters:
                    stmt = stmt.where(PaymentModel.amount >= filters["min_amount"])
                
                if "max_amount" in filters:
                    stmt = stmt.where(PaymentModel.amount <= filters["max_amount"])
                
                if "currency" in filters:
                    stmt = stmt.where(PaymentModel.currency == filters["currency"])
            
            result = await self.session.execute(stmt)
            return result.scalar()
        except Exception as e:
            logger.error("Failed to count payments", error=str(e))
            raise RepositoryException(f"Failed to count payments: {e}")
    
    async def get_pending_payments(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """Get pending payments that require processing."""
        return await self.get_by_status(PaymentStatus.PENDING, limit, offset)
    
    async def get_failed_payments(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """Get failed payments for review."""
        return await self.get_by_status(PaymentStatus.FAILED, limit, offset)
    
    async def get_payments_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """Get payments within a date range."""
        try:
            stmt = select(PaymentModel).where(
                and_(
                    PaymentModel.created_at >= start_date,
                    PaymentModel.created_at <= end_date
                )
            ).order_by(desc(PaymentModel.created_at))
            
            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            
            result = await self.session.execute(stmt)
            payment_models = result.scalars().all()
            
            return [model.to_domain() for model in payment_models]
        except Exception as e:
            logger.error("Failed to get payments by date range", error=str(e))
            raise RepositoryException(f"Failed to get payments by date range: {e}")
    
    async def get_refundable_payments(
        self,
        subscription_id: Optional[UUID] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """Get payments that can be refunded."""
        try:
            stmt = select(PaymentModel).where(
                and_(
                    PaymentModel.status == PaymentStatus.COMPLETED,
                    PaymentModel.payment_type != PaymentType.REFUND
                )
            )
            
            if subscription_id:
                stmt = stmt.where(PaymentModel.subscription_id == subscription_id)
            
            stmt = stmt.order_by(desc(PaymentModel.created_at))
            
            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            
            result = await self.session.execute(stmt)
            payment_models = result.scalars().all()
            
            return [model.to_domain() for model in payment_models]
        except Exception as e:
            logger.error("Failed to get refundable payments", error=str(e))
            raise RepositoryException(f"Failed to get refundable payments: {e}")
    
    async def get_payment_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get payment analytics data."""
        try:
            # Base query
            base_query = select(PaymentModel)
            
            if start_date:
                base_query = base_query.where(PaymentModel.created_at >= start_date)
            if end_date:
                base_query = base_query.where(PaymentModel.created_at <= end_date)
            
            # Total payments
            total_count = await self.session.execute(
                select(func.count(PaymentModel.id)).select_from(base_query.subquery())
            )
            total_payments = total_count.scalar()
            
            # Total revenue
            revenue_query = select(func.sum(PaymentModel.amount)).where(
                PaymentModel.status == PaymentStatus.COMPLETED
            )
            if start_date:
                revenue_query = revenue_query.where(PaymentModel.created_at >= start_date)
            if end_date:
                revenue_query = revenue_query.where(PaymentModel.created_at <= end_date)
            
            revenue_result = await self.session.execute(revenue_query)
            total_revenue = revenue_result.scalar() or 0
            
            # Status breakdown
            status_query = select(
                PaymentModel.status,
                func.count(PaymentModel.id).label('count')
            ).group_by(PaymentModel.status)
            
            if start_date:
                status_query = status_query.where(PaymentModel.created_at >= start_date)
            if end_date:
                status_query = status_query.where(PaymentModel.created_at <= end_date)
            
            status_result = await self.session.execute(status_query)
            status_breakdown = {row[0]: row[1] for row in status_result}
            
            # Payment method breakdown
            method_query = select(
                PaymentModel.payment_method,
                func.count(PaymentModel.id).label('count')
            ).group_by(PaymentModel.payment_method)
            
            if start_date:
                method_query = method_query.where(PaymentModel.created_at >= start_date)
            if end_date:
                method_query = method_query.where(PaymentModel.created_at <= end_date)
            
            method_result = await self.session.execute(method_query)
            method_breakdown = {row[0]: row[1] for row in method_result}
            
            return {
                "total_payments": total_payments,
                "total_revenue": float(total_revenue),
                "status_breakdown": status_breakdown,
                "method_breakdown": method_breakdown,
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                }
            }
        except Exception as e:
            logger.error("Failed to get payment analytics", error=str(e))
            raise RepositoryException(f"Failed to get payment analytics: {e}")
    
    async def get_revenue_by_period(
        self,
        period: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get revenue data grouped by period."""
        try:
            # Map period to PostgreSQL date_trunc format
            period_map = {
                "day": "day",
                "week": "week",
                "month": "month",
                "year": "year"
            }
            
            if period not in period_map:
                raise ValueError(f"Invalid period: {period}")
            
            trunc_period = period_map[period]
            
            query = select(
                func.date_trunc(trunc_period, PaymentModel.created_at).label('period'),
                func.sum(PaymentModel.amount).label('revenue'),
                func.count(PaymentModel.id).label('count')
            ).where(
                PaymentModel.status == PaymentStatus.COMPLETED
            ).group_by(
                func.date_trunc(trunc_period, PaymentModel.created_at)
            ).order_by(
                func.date_trunc(trunc_period, PaymentModel.created_at)
            )
            
            if start_date:
                query = query.where(PaymentModel.created_at >= start_date)
            if end_date:
                query = query.where(PaymentModel.created_at <= end_date)
            
            result = await self.session.execute(query)
            
            return [
                {
                    "period": row[0].isoformat(),
                    "revenue": float(row[1]),
                    "count": row[2]
                }
                for row in result
            ]
        except Exception as e:
            logger.error("Failed to get revenue by period", error=str(e))
            raise RepositoryException(f"Failed to get revenue by period: {e}")
    
    async def get_payment_methods_stats(self) -> Dict[str, Any]:
        """Get payment method statistics."""
        try:
            query = select(
                PaymentModel.payment_method,
                func.count(PaymentModel.id).label('count'),
                func.sum(PaymentModel.amount).label('total_amount'),
                func.avg(PaymentModel.amount).label('avg_amount')
            ).where(
                PaymentModel.status == PaymentStatus.COMPLETED
            ).group_by(
                PaymentModel.payment_method
            )
            
            result = await self.session.execute(query)
            
            return {
                str(row[0]): {
                    "count": row[1],
                    "total_amount": float(row[2]),
                    "average_amount": float(row[3])
                }
                for row in result
            }
        except Exception as e:
            logger.error("Failed to get payment methods stats", error=str(e))
            raise RepositoryException(f"Failed to get payment methods stats: {e}")
    
    async def get_subscription_payment_history(
        self,
        subscription_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Payment]:
        """Get complete payment history for a subscription."""
        return await self.get_by_subscription_id(subscription_id, limit, offset)


class PaymentHistoryRepository(IPaymentHistoryRepository):
    """
    Payment history repository implementation using SQLAlchemy.
    
    Handles payment history and audit trail operations.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
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
        """Create a payment history entry."""
        try:
            history_entry = PaymentHistoryModel(
                id=uuid4(),
                payment_id=payment_id,
                old_status=old_status,
                new_status=new_status,
                action=action,
                admin_user_id=admin_user_id,
                reason=reason,
                notes=notes,
                metadata_json=metadata or {},
                created_at=datetime.now(timezone.utc)
            )
            
            self.session.add(history_entry)
            await self.session.flush()
            
            logger.info(
                "Payment history entry created",
                payment_id=str(payment_id),
                action=action,
                new_status=new_status.value,
                admin_user_id=str(admin_user_id) if admin_user_id else None
            )
        except Exception as e:
            logger.error("Failed to create payment history entry", error=str(e))
            raise RepositoryException(f"Failed to create payment history entry: {e}")
    
    async def get_payment_history(
        self,
        payment_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get history entries for a payment."""
        try:
            stmt = select(PaymentHistoryModel).where(
                PaymentHistoryModel.payment_id == payment_id
            ).order_by(desc(PaymentHistoryModel.created_at))
            
            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            
            result = await self.session.execute(stmt)
            history_entries = result.scalars().all()
            
            return [
                {
                    "id": str(entry.id),
                    "payment_id": str(entry.payment_id),
                    "old_status": entry.old_status.value if entry.old_status else None,
                    "new_status": entry.new_status.value,
                    "action": entry.action,
                    "admin_user_id": str(entry.admin_user_id) if entry.admin_user_id else None,
                    "reason": entry.reason,
                    "notes": entry.notes,
                    "metadata": entry.metadata_json,
                    "created_at": entry.created_at.isoformat(),
                }
                for entry in history_entries
            ]
        except Exception as e:
            logger.error("Failed to get payment history", payment_id=str(payment_id), error=str(e))
            raise RepositoryException(f"Failed to get payment history: {e}")
    
    async def get_admin_activity(
        self,
        admin_user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get payment activity for an admin user."""
        try:
            stmt = select(PaymentHistoryModel).where(
                PaymentHistoryModel.admin_user_id == admin_user_id
            )
            
            if start_date:
                stmt = stmt.where(PaymentHistoryModel.created_at >= start_date)
            if end_date:
                stmt = stmt.where(PaymentHistoryModel.created_at <= end_date)
            
            stmt = stmt.order_by(desc(PaymentHistoryModel.created_at))
            
            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            
            result = await self.session.execute(stmt)
            activity_entries = result.scalars().all()
            
            return [
                {
                    "id": str(entry.id),
                    "payment_id": str(entry.payment_id),
                    "old_status": entry.old_status.value if entry.old_status else None,
                    "new_status": entry.new_status.value,
                    "action": entry.action,
                    "reason": entry.reason,
                    "notes": entry.notes,
                    "metadata": entry.metadata_json,
                    "created_at": entry.created_at.isoformat(),
                }
                for entry in activity_entries
            ]
        except Exception as e:
            logger.error("Failed to get admin activity", admin_user_id=str(admin_user_id), error=str(e))
            raise RepositoryException(f"Failed to get admin activity: {e}") 