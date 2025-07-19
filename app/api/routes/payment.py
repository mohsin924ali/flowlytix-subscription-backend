"""
Payment API Routes

FastAPI routes for payment management operations.
Following Instructions file standards for API design and documentation.
"""

import structlog
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import BusinessLogicException, ValidationException
from app.domain.entities.payment import PaymentType
from app.domain.services.payment_service import PaymentService
from app.domain.value_objects.payment_status import PaymentStatus
from app.domain.value_objects.payment_method import PaymentMethod
from app.domain.value_objects.money import Money
from app.infrastructure.database.repositories.payment_repository import (
    PaymentRepository,
    PaymentHistoryRepository,
)
from app.schemas.payment import (
    CreatePaymentRequest,
    ProcessPaymentRequest,
    FailPaymentRequest,
    RefundPaymentRequest,
    AddPaymentNoteRequest,
    BulkPaymentActionRequest,
    PaymentSearchRequest,
    PaymentResponse,
    PaymentListResponse,
    PaymentHistoryResponse,
    RefundResponse,
    BulkPaymentActionResponse,
    PaymentAnalyticsResponse,
    RevenueByPeriodResponse,
    PaymentMethodStatsResponse,
    PaymentStatusSummary,
    AdminActivityResponse,
    PaymentErrorResponse,
    ValidationErrorResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


# Dependency to get payment service
async def get_payment_service(session: AsyncSession = Depends(get_session)) -> PaymentService:
    """Get payment service with dependencies."""
    payment_repo = PaymentRepository(session)
    history_repo = PaymentHistoryRepository(session)
    return PaymentService(payment_repo, history_repo)


# Payment CRUD Operations

@router.post(
    "/",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new payment",
    description="Create a new payment record with the specified details.",
    responses={
        201: {"description": "Payment created successfully"},
        400: {"model": ValidationErrorResponse, "description": "Invalid request data"},
        409: {"model": PaymentErrorResponse, "description": "Business logic conflict"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def create_payment(
    request: CreatePaymentRequest,
    payment_service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Create a new payment."""
    try:
        logger.info(
            "Creating payment via API",
            subscription_id=str(request.subscription_id),
            amount=request.amount,
            currency=request.currency,
            payment_method=str(request.payment_method),
            payment_type=str(request.payment_type)
        )
        
        # Create Money value object
        amount = Money(request.amount, request.currency)
        
        # Create payment
        payment = await payment_service.create_payment(
            subscription_id=request.subscription_id,
            amount=amount,
            payment_method=request.payment_method,
            payment_type=request.payment_type,
            description=request.description,
            reference_id=request.reference_id,
            metadata=request.metadata,
        )
        
        return PaymentResponse.from_domain(payment)
        
    except ValidationException as e:
        logger.warning("Payment creation validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_error", "message": str(e)}
        )
    except BusinessLogicException as e:
        logger.warning("Payment creation business logic error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "business_logic_error", "message": str(e)}
        )
    except Exception as e:
        logger.error("Unexpected error creating payment", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )


@router.get(
    "/",
    response_model=PaymentListResponse,
    summary="List all payments",
    description="Retrieve a list of all payments with optional pagination.",
    responses={
        200: {"description": "Payments retrieved successfully"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def list_payments(
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: Optional[int] = Query(0, ge=0, description="Number of results to skip"),
    payment_service: PaymentService = Depends(get_payment_service),
) -> PaymentListResponse:
    """List all payments with pagination."""
    try:
        payments, total_count = await payment_service.search_payments(
            filters={},
            limit=limit,
            offset=offset,
            order_by="created_at",
            order_direction="desc",
        )
        
        # Convert to response
        payment_responses = [PaymentResponse.from_domain(payment) for payment in payments]
        
        has_more = (offset + len(payment_responses)) < total_count
        
        return PaymentListResponse(
            payments=payment_responses,
            total=total_count,
            limit=limit,
            offset=offset,
            has_more=has_more,
        )
        
    except Exception as e:
        logger.error("Unexpected error listing payments", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Get payment by ID",
    description="Retrieve a specific payment by its unique identifier.",
    responses={
        200: {"description": "Payment retrieved successfully"},
        404: {"model": PaymentErrorResponse, "description": "Payment not found"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def get_payment(
    payment_id: UUID = Path(..., description="Payment unique identifier"),
    payment_service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Get a payment by ID."""
    try:
        payment = await payment_service.get_payment_by_id(payment_id)
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "not_found", "message": f"Payment {payment_id} not found"}
            )
        
        return PaymentResponse.from_domain(payment)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error getting payment", payment_id=str(payment_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )


@router.post(
    "/search",
    response_model=PaymentListResponse,
    summary="Search payments",
    description="Search and filter payments with pagination support.",
    responses={
        200: {"description": "Payments retrieved successfully"},
        400: {"model": ValidationErrorResponse, "description": "Invalid search parameters"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def search_payments(
    request: PaymentSearchRequest,
    payment_service: PaymentService = Depends(get_payment_service),
) -> PaymentListResponse:
    """Search payments with filters and pagination."""
    try:
        # Build filters dictionary
        filters = {}
        
        if request.status:
            filters["status"] = request.status
        if request.payment_method:
            filters["payment_method"] = request.payment_method
        if request.payment_type:
            filters["payment_type"] = request.payment_type
        if request.subscription_id:
            filters["subscription_id"] = request.subscription_id
        if request.admin_user_id:
            filters["admin_user_id"] = request.admin_user_id
        if request.start_date:
            filters["start_date"] = request.start_date
        if request.end_date:
            filters["end_date"] = request.end_date
        if request.min_amount:
            filters["min_amount"] = request.min_amount
        if request.max_amount:
            filters["max_amount"] = request.max_amount
        if request.currency:
            filters["currency"] = request.currency
        
        # Search payments
        payments, total_count = await payment_service.search_payments(
            filters=filters,
            limit=request.limit,
            offset=request.offset,
            order_by=request.order_by,
            order_direction=request.order_direction,
        )
        
        # Convert to response
        payment_responses = [PaymentResponse.from_domain(payment) for payment in payments]
        
        has_more = False
        if request.limit and request.offset is not None:
            has_more = (request.offset + len(payment_responses)) < total_count
        
        return PaymentListResponse(
            payments=payment_responses,
            total=total_count,
            limit=request.limit,
            offset=request.offset,
            has_more=has_more,
        )
        
    except ValidationException as e:
        logger.warning("Payment search validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_error", "message": str(e)}
        )
    except Exception as e:
        logger.error("Unexpected error searching payments", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )


# Payment Action Operations

@router.post(
    "/{payment_id}/process",
    response_model=PaymentResponse,
    summary="Process payment manually",
    description="Manually process a pending payment as an administrator.",
    responses={
        200: {"description": "Payment processed successfully"},
        404: {"model": PaymentErrorResponse, "description": "Payment not found"},
        409: {"model": PaymentErrorResponse, "description": "Payment cannot be processed"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def process_payment(
    payment_id: UUID = Path(..., description="Payment unique identifier"),
    request: ProcessPaymentRequest = Body(..., description="Processing details"),
    payment_service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Process a payment manually."""
    try:
        payment = await payment_service.process_payment_manually(
            payment_id=payment_id,
            admin_user_id=request.admin_user_id,
            notes=request.notes,
        )
        
        return PaymentResponse.from_domain(payment)
        
    except BusinessLogicException as e:
        logger.warning(
            "Payment processing error",
            payment_id=str(payment_id),
            error=str(e)
        )
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "not_found", "message": str(e), "payment_id": payment_id}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "business_logic_error", "message": str(e), "payment_id": payment_id}
            )
    except Exception as e:
        logger.error("Unexpected error processing payment", payment_id=str(payment_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )


@router.post(
    "/{payment_id}/fail",
    response_model=PaymentResponse,
    summary="Fail payment",
    description="Mark a payment as failed with a reason.",
    responses={
        200: {"description": "Payment marked as failed successfully"},
        404: {"model": PaymentErrorResponse, "description": "Payment not found"},
        409: {"model": PaymentErrorResponse, "description": "Payment cannot be failed"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def fail_payment(
    payment_id: UUID = Path(..., description="Payment unique identifier"),
    request: FailPaymentRequest = Body(..., description="Failure details"),
    payment_service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Mark a payment as failed."""
    try:
        payment = await payment_service.fail_payment(
            payment_id=payment_id,
            admin_user_id=request.admin_user_id,
            reason=request.reason,
        )
        
        return PaymentResponse.from_domain(payment)
        
    except BusinessLogicException as e:
        logger.warning(
            "Payment failure error",
            payment_id=str(payment_id),
            error=str(e)
        )
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "not_found", "message": str(e), "payment_id": payment_id}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "business_logic_error", "message": str(e), "payment_id": payment_id}
            )
    except Exception as e:
        logger.error("Unexpected error failing payment", payment_id=str(payment_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )


@router.post(
    "/{payment_id}/refund",
    response_model=RefundResponse,
    summary="Refund payment",
    description="Create a refund for a completed payment.",
    responses={
        200: {"description": "Payment refunded successfully"},
        404: {"model": PaymentErrorResponse, "description": "Payment not found"},
        409: {"model": PaymentErrorResponse, "description": "Payment cannot be refunded"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def refund_payment(
    payment_id: UUID = Path(..., description="Payment unique identifier"),
    request: RefundPaymentRequest = Body(..., description="Refund details"),
    payment_service: PaymentService = Depends(get_payment_service),
) -> RefundResponse:
    """Refund a payment."""
    try:
        original_payment, refund_payment = await payment_service.refund_payment(
            payment_id=payment_id,
            admin_user_id=request.admin_user_id,
            reason=request.reason,
        )
        
        return RefundResponse(
            original_payment=PaymentResponse.from_domain(original_payment),
            refund_payment=PaymentResponse.from_domain(refund_payment),
        )
        
    except BusinessLogicException as e:
        logger.warning(
            "Payment refund error",
            payment_id=str(payment_id),
            error=str(e)
        )
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "not_found", "message": str(e), "payment_id": payment_id}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "business_logic_error", "message": str(e), "payment_id": payment_id}
            )
    except Exception as e:
        logger.error("Unexpected error refunding payment", payment_id=str(payment_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )


@router.post(
    "/{payment_id}/notes",
    response_model=PaymentResponse,
    summary="Add payment note",
    description="Add an administrative note to a payment.",
    responses={
        200: {"description": "Note added successfully"},
        404: {"model": PaymentErrorResponse, "description": "Payment not found"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def add_payment_note(
    payment_id: UUID = Path(..., description="Payment unique identifier"),
    request: AddPaymentNoteRequest = Body(..., description="Note details"),
    payment_service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Add a note to a payment."""
    try:
        payment = await payment_service.add_payment_note(
            payment_id=payment_id,
            admin_user_id=request.admin_user_id,
            note=request.note,
        )
        
        return PaymentResponse.from_domain(payment)
        
    except BusinessLogicException as e:
        logger.warning(
            "Add payment note error",
            payment_id=str(payment_id),
            error=str(e)
        )
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "not_found", "message": str(e), "payment_id": payment_id}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "internal_error", "message": str(e)}
            )
    except Exception as e:
        logger.error("Unexpected error adding payment note", payment_id=str(payment_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )


# Bulk Operations

@router.post(
    "/bulk-action",
    response_model=BulkPaymentActionResponse,
    summary="Bulk payment action",
    description="Process multiple payments in bulk (process or fail).",
    responses={
        200: {"description": "Bulk action completed"},
        400: {"model": ValidationErrorResponse, "description": "Invalid request data"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def bulk_payment_action(
    request: BulkPaymentActionRequest,
    payment_service: PaymentService = Depends(get_payment_service),
) -> BulkPaymentActionResponse:
    """Perform bulk actions on payments."""
    try:
        result = await payment_service.bulk_process_payments(
            payment_ids=request.payment_ids,
            admin_user_id=request.admin_user_id,
            action=request.action,
            reason=request.reason,
        )
        
        return BulkPaymentActionResponse(**result)
        
    except ValidationException as e:
        logger.warning("Bulk payment action validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_error", "message": str(e)}
        )
    except Exception as e:
        logger.error("Unexpected error in bulk payment action", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )


# Query Operations

@router.get(
    "/subscription/{subscription_id}",
    response_model=PaymentListResponse,
    summary="Get payments for subscription",
    description="Retrieve all payments for a specific subscription.",
    responses={
        200: {"description": "Payments retrieved successfully"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def get_subscription_payments(
    subscription_id: UUID = Path(..., description="Subscription unique identifier"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of results"),
    offset: Optional[int] = Query(None, ge=0, description="Number of results to skip"),
    payment_service: PaymentService = Depends(get_payment_service),
) -> PaymentListResponse:
    """Get all payments for a subscription."""
    try:
        payments = await payment_service.get_payments_for_subscription(
            subscription_id=subscription_id,
            limit=limit,
            offset=offset,
        )
        
        payment_responses = [PaymentResponse.from_domain(payment) for payment in payments]
        
        # For simplicity, we're not implementing total count for this endpoint
        # In a production system, you might want to add a separate count query
        
        return PaymentListResponse(
            payments=payment_responses,
            total=len(payment_responses),
            limit=limit,
            offset=offset,
            has_more=len(payment_responses) == limit if limit else False,
        )
        
    except Exception as e:
        logger.error(
            "Unexpected error getting subscription payments",
            subscription_id=str(subscription_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )


@router.get(
    "/pending",
    response_model=PaymentListResponse,
    summary="Get pending payments",
    description="Retrieve all payments that require manual processing.",
    responses={
        200: {"description": "Pending payments retrieved successfully"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def get_pending_payments(
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of results"),
    offset: Optional[int] = Query(None, ge=0, description="Number of results to skip"),
    payment_service: PaymentService = Depends(get_payment_service),
) -> PaymentListResponse:
    """Get all pending payments."""
    try:
        payments = await payment_service.get_pending_payments(limit=limit, offset=offset)
        
        payment_responses = [PaymentResponse.from_domain(payment) for payment in payments]
        
        return PaymentListResponse(
            payments=payment_responses,
            total=len(payment_responses),
            limit=limit,
            offset=offset,
            has_more=len(payment_responses) == limit if limit else False,
        )
        
    except Exception as e:
        logger.error("Unexpected error getting pending payments", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )


@router.get(
    "/failed",
    response_model=PaymentListResponse,
    summary="Get failed payments",
    description="Retrieve all payments that have failed processing.",
    responses={
        200: {"description": "Failed payments retrieved successfully"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def get_failed_payments(
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of results"),
    offset: Optional[int] = Query(None, ge=0, description="Number of results to skip"),
    payment_service: PaymentService = Depends(get_payment_service),
) -> PaymentListResponse:
    """Get all failed payments."""
    try:
        payments = await payment_service.get_failed_payments(limit=limit, offset=offset)
        
        payment_responses = [PaymentResponse.from_domain(payment) for payment in payments]
        
        return PaymentListResponse(
            payments=payment_responses,
            total=len(payment_responses),
            limit=limit,
            offset=offset,
            has_more=len(payment_responses) == limit if limit else False,
        )
        
    except Exception as e:
        logger.error("Unexpected error getting failed payments", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )


# Analytics and Reporting

@router.get(
    "/analytics",
    response_model=PaymentAnalyticsResponse,
    summary="Get payment analytics",
    description="Retrieve payment analytics and statistics.",
    responses={
        200: {"description": "Analytics retrieved successfully"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def get_payment_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date for analytics"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics"),
    payment_service: PaymentService = Depends(get_payment_service),
) -> PaymentAnalyticsResponse:
    """Get payment analytics."""
    try:
        analytics = await payment_service.get_payment_analytics(
            start_date=start_date,
            end_date=end_date,
        )
        
        return PaymentAnalyticsResponse(**analytics)
        
    except Exception as e:
        logger.error("Unexpected error getting payment analytics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )


@router.get(
    "/analytics/revenue",
    response_model=RevenueByPeriodResponse,
    summary="Get revenue by period",
    description="Retrieve revenue data grouped by time period.",
    responses={
        200: {"description": "Revenue data retrieved successfully"},
        400: {"model": ValidationErrorResponse, "description": "Invalid period parameter"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def get_revenue_by_period(
    period: str = Query(..., regex="^(day|week|month|year)$", description="Time period for grouping"),
    start_date: Optional[datetime] = Query(None, description="Start date for revenue data"),
    end_date: Optional[datetime] = Query(None, description="End date for revenue data"),
    payment_service: PaymentService = Depends(get_payment_service),
) -> RevenueByPeriodResponse:
    """Get revenue data by period."""
    try:
        revenue_data = await payment_service.get_revenue_by_period(
            period=period,
            start_date=start_date,
            end_date=end_date,
        )
        
        return RevenueByPeriodResponse(
            data=revenue_data,
            period=period,
            start_date=start_date,
            end_date=end_date,
        )
        
    except Exception as e:
        logger.error("Unexpected error getting revenue by period", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )


@router.get(
    "/analytics/methods",
    response_model=PaymentMethodStatsResponse,
    summary="Get payment method statistics",
    description="Retrieve statistics for different payment methods.",
    responses={
        200: {"description": "Payment method statistics retrieved successfully"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def get_payment_method_stats(
    payment_service: PaymentService = Depends(get_payment_service),
) -> PaymentMethodStatsResponse:
    """Get payment method statistics."""
    try:
        stats = await payment_service.get_payment_methods_stats()
        
        return PaymentMethodStatsResponse(methods=stats)
        
    except Exception as e:
        logger.error("Unexpected error getting payment method stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )


# History and Audit

@router.get(
    "/{payment_id}/history",
    response_model=PaymentHistoryResponse,
    summary="Get payment history",
    description="Retrieve the complete history of changes for a payment.",
    responses={
        200: {"description": "Payment history retrieved successfully"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def get_payment_history(
    payment_id: UUID = Path(..., description="Payment unique identifier"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of results"),
    offset: Optional[int] = Query(None, ge=0, description="Number of results to skip"),
    payment_service: PaymentService = Depends(get_payment_service),
) -> PaymentHistoryResponse:
    """Get payment history."""
    try:
        history_entries = await payment_service.get_payment_history(
            payment_id=payment_id,
            limit=limit,
            offset=offset,
        )
        
        return PaymentHistoryResponse(
            entries=history_entries,
            total=len(history_entries),
            limit=limit,
            offset=offset,
        )
        
    except Exception as e:
        logger.error("Unexpected error getting payment history", payment_id=str(payment_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        )


@router.get(
    "/admin/{admin_user_id}/activity",
    response_model=AdminActivityResponse,
    summary="Get admin activity",
    description="Retrieve payment-related activity for a specific admin user.",
    responses={
        200: {"description": "Admin activity retrieved successfully"},
        500: {"model": PaymentErrorResponse, "description": "Internal server error"},
    },
)
async def get_admin_activity(
    admin_user_id: UUID = Path(..., description="Admin user unique identifier"),
    start_date: Optional[datetime] = Query(None, description="Start date for activity"),
    end_date: Optional[datetime] = Query(None, description="End date for activity"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of results"),
    offset: Optional[int] = Query(None, ge=0, description="Number of results to skip"),
    payment_service: PaymentService = Depends(get_payment_service),
) -> AdminActivityResponse:
    """Get admin activity."""
    try:
        activity_entries = await payment_service.get_admin_activity(
            admin_user_id=admin_user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
        
        return AdminActivityResponse(
            entries=activity_entries,
            total=len(activity_entries),
            limit=limit,
            offset=offset,
            admin_user_id=admin_user_id,
            start_date=start_date,
            end_date=end_date,
        )
        
    except Exception as e:
        logger.error("Unexpected error getting admin activity", admin_user_id=str(admin_user_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An unexpected error occurred"}
        ) 