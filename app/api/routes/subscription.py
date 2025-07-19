"""
Subscription API Routes

FastAPI endpoints for subscription management, license activation, and validation.
Follows Instructions file standards for REST API design and security.
"""

import structlog
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import (
    SubscriptionExpiredException,
    DeviceLimitExceededException,
    LicenseKeyInvalidException,
    SubscriptionNotFoundException,
    CustomerNotFoundException,
    DeviceNotFoundException,
)
from app.core.security import security_manager
from app.domain.services.subscription_service import SubscriptionService, CustomerService
from app.infrastructure.database.repositories.subscription_repository import (
    SubscriptionRepository,
    CustomerRepository,
    DeviceRepository,
)
from app.schemas.subscription import (
    # Request schemas
    LicenseActivationRequest,
    LicenseValidationRequest,
    LicenseDeactivationRequest,
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionExtensionRequest,
    SubscriptionTierUpdateRequest,
    CustomerCreate,
    CustomerUpdate,
    FeatureCheckRequest,
    PaginationParams,
    SubscriptionFilters,
    CustomerFilters,
    DeviceFilters,
    # Response schemas
    LicenseActivationResponse,
    LicenseValidationResponse,
    SubscriptionResponse,
    SubscriptionListResponse,
    CustomerResponse,
    CustomerListResponse,
    CustomerWithSubscriptionsResponse,
    DeviceResponse,
    DeviceListResponse,
    SubscriptionAnalyticsResponse,
    ExpiringSubscriptionResponse,
    FeatureCheckResponse,
    MetricsResponse,
    ErrorResponse,
)

logger = structlog.get_logger(__name__)
security = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/subscription", tags=["subscription"])


async def _subscription_to_response(subscription: "Subscription") -> SubscriptionResponse:
    """
    Convert subscription entity to response model with customer information.
    
    Args:
        subscription: Subscription domain entity with pre-loaded customer data
        
    Returns:
        SubscriptionResponse model
    """
    # Extract customer information from already-loaded subscription data
    customer_data = None
    if hasattr(subscription, 'customer_model') and subscription.customer_model:
        try:
            customer_data = CustomerResponse(
                id=subscription.customer_model.id,
                name=subscription.customer_model.name,
                email=subscription.customer_model.email,
                company=subscription.customer_model.company,
                phone=subscription.customer_model.phone,
                address=subscription.customer_model.address,
                metadata=subscription.customer_model.metadata_json or {},
                created_at=subscription.customer_model.created_at,
                updated_at=subscription.customer_model.updated_at,
            )
        except Exception as e:
            logger.warning("Failed to extract customer data from subscription", 
                         customer_id=str(subscription.customer_id), error=str(e))

    # Handle features properly
    features = {}
    if hasattr(subscription, 'feature_set') and subscription.feature_set:
        features = subscription.feature_set.features
    elif hasattr(subscription, 'features') and subscription.features:
        features = subscription.features
    
    # Handle devices properly - convert Device entities to DeviceResponse
    devices = []
    if hasattr(subscription, 'devices') and subscription.devices:
        for device in subscription.devices:
            if hasattr(device, '__dict__'):  # It's a Device entity
                devices.append(DeviceResponse(
                    id=device.id,
                    subscription_id=device.subscription_id,
                    device_id=device.device_id,
                    device_name=device.device_name,
                    device_type=device.device_type,
                    fingerprint=device.fingerprint,
                    os_name=device.os_name,
                    os_version=device.os_version,
                    app_version=device.app_version,
                    is_active=device.is_active,
                    last_seen_at=device.last_seen_at,
                    metadata=device.metadata,
                    created_at=device.created_at,
                    updated_at=device.updated_at,
                ))
    
    return SubscriptionResponse(
        id=subscription.id,
        customer_id=subscription.customer_id,
        customer=customer_data,  # Include customer information
        license_key=subscription.license_key,
        tier=subscription.tier,
        status=subscription.status,
        features=features,
        max_devices=subscription.max_devices,
        starts_at=subscription.starts_at,
        expires_at=subscription.expires_at,
        grace_period_days=subscription.grace_period_days,
        price=subscription.price,
        currency=subscription.currency,
        auto_renew=subscription.auto_renew,
        renewal_period_days=subscription.renewal_period_days,
        metadata=subscription.metadata,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
        devices=devices
    )


# Dependency injection
async def get_repositories(session: AsyncSession = Depends(get_session)):
    """Get repository instances."""
    subscription_repo = SubscriptionRepository(session)
    customer_repo = CustomerRepository(session)
    device_repo = DeviceRepository(session)
    return subscription_repo, customer_repo, device_repo


async def get_subscription_service(
    repos=Depends(get_repositories),
) -> SubscriptionService:
    """Get subscription service instance."""
    subscription_repo, customer_repo, device_repo = repos
    return SubscriptionService(subscription_repo, customer_repo, device_repo, security_manager)


async def get_customer_service(
    repos=Depends(get_repositories),
) -> CustomerService:
    """Get customer service instance."""
    subscription_repo, customer_repo, device_repo = repos
    return CustomerService(customer_repo, subscription_repo)


# License activation and validation endpoints
@router.post(
    "/activate",
    response_model=LicenseActivationResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate license on device",
    description="Activate a license key on a specific device and return JWT token",
)
async def activate_license(
    request: LicenseActivationRequest,
    request_obj: Request,
    service: SubscriptionService = Depends(get_subscription_service),
) -> LicenseActivationResponse:
    """
    Activate a license on a device.
    
    This endpoint validates the license key and activates it on the specified device.
    Returns a JWT token for subsequent API calls.
    """
    try:
        device_info = None
        if request.device_info:
            device_info = request.device_info.dict()
        
        result = await service.activate_license(
            license_key=request.license_key,
            device_id=request.device_id,
            device_info=device_info,
        )
        
        logger.info(
            "License activation requested",
            license_key=request.license_key[:8] + "***",
            device_id=request.device_id,
            action=result["action"],
            ip_address=request_obj.client.host,
        )
        
        return LicenseActivationResponse(
            token=result["token"],
            subscription=SubscriptionResponse(
                id=result["subscription"].id,
                customer_id=result["subscription"].customer_id,
                license_key=result["subscription"].license_key,
                tier=result["subscription"].tier,
                status=result["subscription"].status,
                features=result["subscription"].feature_set.features,
                max_devices=result["subscription"].max_devices,
                starts_at=result["subscription"].starts_at,
                expires_at=result["subscription"].expires_at,
                grace_period_days=result["subscription"].grace_period_days,
                price=result["subscription"].price,
                currency=result["subscription"].currency,
                auto_renew=result["subscription"].auto_renew,
                renewal_period_days=result["subscription"].renewal_period_days,
                metadata=result["subscription"].metadata,
                created_at=result["subscription"].created_at,
                updated_at=result["subscription"].updated_at,
                devices=[]  # Will be populated separately if needed
            ),
            device=DeviceResponse(
                id=result["device"].id,
                subscription_id=result["device"].subscription_id,
                device_id=result["device"].device_id,
                device_name=result["device"].device_name,
                device_type=result["device"].device_type,
                fingerprint=result["device"].fingerprint,
                os_name=result["device"].os_name,
                os_version=result["device"].os_version,
                app_version=result["device"].app_version,
                is_active=result["device"].is_active,
                last_seen_at=result["device"].last_seen_at,
                metadata=result["device"].metadata,
                created_at=result["device"].created_at,
                updated_at=result["device"].updated_at,
            ),
            action=result["action"],
            message=result["message"],
            expires_at=result["expires_at"],
        )
        
    except LicenseKeyInvalidException as e:
        logger.warning("Invalid license key", license_key=request.license_key[:8] + "***")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid license key",
        )
    except SubscriptionExpiredException as e:
        logger.warning("Expired subscription", license_key=request.license_key[:8] + "***")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscription has expired",
        )
    except DeviceLimitExceededException as e:
        logger.warning("Device limit exceeded", license_key=request.license_key[:8] + "***")
        max_devices = e.details.get("max_devices", "N/A")
        current_devices = e.details.get("current_devices", "N/A")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Device limit exceeded. {current_devices}/{max_devices} devices currently active.",
        )
    except Exception as e:
        logger.error("License activation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/validate",
    response_model=LicenseValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate license",
    description="Validate a license key for a specific device",
)
async def validate_license(
    request: LicenseValidationRequest,
    request_obj: Request,
    service: SubscriptionService = Depends(get_subscription_service),
) -> LicenseValidationResponse:
    """
    Validate a license for a specific device.
    
    This endpoint checks if the license is valid and active for the specified device.
    """
    try:
        result = await service.validate_license(
            license_key=request.license_key,
            device_id=request.device_id,
            update_last_seen=True,
        )
        
        if result["valid"]:
            return LicenseValidationResponse(
                valid=True,
                subscription=SubscriptionResponse(
                    id=result["subscription"].id,
                    customer_id=result["subscription"].customer_id,
                    license_key=result["subscription"].license_key,
                    tier=result["subscription"].tier,
                    status=result["subscription"].status,
                    features=result["subscription"].feature_set.features,
                    max_devices=result["subscription"].max_devices,
                    starts_at=result["subscription"].starts_at,
                    expires_at=result["subscription"].expires_at,
                    grace_period_days=result["subscription"].grace_period_days,
                    price=result["subscription"].price,
                    currency=result["subscription"].currency,
                    auto_renew=result["subscription"].auto_renew,
                    renewal_period_days=result["subscription"].renewal_period_days,
                    metadata=result["subscription"].metadata,
                    created_at=result["subscription"].created_at,
                    updated_at=result["subscription"].updated_at,
                    devices=[]
                ),
                device=DeviceResponse(
                    id=result["device"].id,
                    subscription_id=result["device"].subscription_id,
                    device_id=result["device"].device_id,
                    device_name=result["device"].device_name,
                    device_type=result["device"].device_type,
                    fingerprint=result["device"].fingerprint,
                    os_name=result["device"].os_name,
                    os_version=result["device"].os_version,
                    app_version=result["device"].app_version,
                    is_active=result["device"].is_active,
                    last_seen_at=result["device"].last_seen_at,
                    metadata=result["device"].metadata,
                    created_at=result["device"].created_at,
                    updated_at=result["device"].updated_at,
                ),
                in_grace_period=result.get("in_grace_period"),
                days_until_expiry=result.get("days_until_expiry"),
                features=result.get("features"),
            )
        else:
            return LicenseValidationResponse(
                valid=False,
                reason=result.get("reason"),
                message=result.get("message"),
                expires_at=result.get("expires_at"),
            )
        
    except LicenseKeyInvalidException as e:
        return LicenseValidationResponse(
            valid=False,
            reason="invalid_license",
            message="Invalid license key",
        )
    except Exception as e:
        logger.error("License validation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/deactivate",
    status_code=status.HTTP_200_OK,
    summary="Deactivate device",
    description="Deactivate a device from a subscription",
)
async def deactivate_device(
    request: LicenseDeactivationRequest,
    request_obj: Request,
    service: SubscriptionService = Depends(get_subscription_service),
) -> Dict[str, Any]:
    """
    Deactivate a device from a subscription.
    
    This endpoint removes a device from the subscription, freeing up a device slot.
    """
    try:
        result = await service.deactivate_device(
            license_key=request.license_key,
            device_id=request.device_id,
        )
        
        logger.info(
            "Device deactivation requested",
            license_key=request.license_key[:8] + "***",
            device_id=request.device_id,
            success=result,
        )
        
        return {
            "success": result,
            "message": "Device deactivated successfully" if result else "Device not found",
        }
        
    except LicenseKeyInvalidException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid license key",
        )
    except Exception as e:
        logger.error("Device deactivation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


# Feature validation endpoint
@router.post(
    "/check-feature",
    response_model=FeatureCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Check feature availability",
    description="Check if a specific feature is available for a license",
)
async def check_feature(
    request: FeatureCheckRequest,
    service: SubscriptionService = Depends(get_subscription_service),
) -> FeatureCheckResponse:
    """
    Check if a specific feature is available for a license.
    
    This endpoint validates feature availability based on subscription tier.
    """
    try:
        subscription = await service.subscription_repo.get_by_license_key(request.license_key)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid license key",
            )
        
        enabled = subscription.feature_set.has_feature(request.feature_name)
        limit_value = subscription.feature_set.get_limit(request.feature_name) if enabled else None
        
        return FeatureCheckResponse(
            feature_name=request.feature_name,
            enabled=enabled,
            limit_value=limit_value,
            subscription_tier=subscription.tier.value,
        )
        
    except Exception as e:
        logger.error("Feature check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


# Subscription management endpoints
@router.post(
    "/subscriptions",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create subscription",
    description="Create a new subscription for a customer",
)
async def create_subscription(
    request: SubscriptionCreate,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    """
    Create a new subscription for a customer.
    
    This endpoint creates a subscription with the specified tier and duration.
    """
    try:
        logger.info("Creating subscription", customer_id=str(request.customer_id), tier=request.tier)
        
        subscription = await service.create_subscription(
            customer_id=request.customer_id,
            tier=request.tier,
            duration_days=request.duration_days,
            max_devices=request.max_devices,
            custom_features=request.custom_features,
            price=request.price,
            currency=request.currency,
        )
        
        logger.info("Subscription created successfully", subscription_id=str(subscription.id))
        
        # Debug logging for subscription attributes
        logger.info(
            "Subscription attributes debug",
            tier_type=type(subscription.tier),
            tier_value=subscription.tier,
            status_type=type(subscription.status),
            status_value=subscription.status,
        )
        
        response = await _subscription_to_response(subscription)
        
        logger.info("Response created successfully", response_id=str(response.id))
        
        return response
        
    except CustomerNotFoundException as e:
        logger.error("Customer not found", customer_id=str(request.customer_id))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )
    except Exception as e:
        logger.error("Subscription creation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/subscriptions/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Get subscription",
    description="Get a subscription by ID",
)
async def get_subscription(
    subscription_id: UUID,
    service: SubscriptionService = Depends(get_subscription_service),
    session: AsyncSession = Depends(get_session),
) -> SubscriptionResponse:
    """Get a subscription by ID."""
    try:
        subscription = await service.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )
        
        
        return await _subscription_to_response(subscription)
        
    except Exception as e:
        logger.error("Get subscription failed", subscription_id=str(subscription_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/subscriptions",
    response_model=SubscriptionListResponse,
    summary="List subscriptions",
    description="List subscriptions with pagination and filtering",
)
async def list_subscriptions(
    pagination: PaginationParams = Depends(),
    filters: SubscriptionFilters = Depends(),
    service: SubscriptionService = Depends(get_subscription_service),
    session: AsyncSession = Depends(get_session),
) -> SubscriptionListResponse:
    """List subscriptions with pagination and filtering."""
    try:
        # Convert filters to dict
        filter_dict = {k: v for k, v in filters.dict().items() if v is not None}
        
        subscriptions = await service.subscription_repo.list_all(
            limit=pagination.limit,
            offset=pagination.offset,
            filters=filter_dict,
        )
        
        total = await service.subscription_repo.count(filters=filter_dict)
        
        subscription_responses = [
            await _subscription_to_response(sub)
            for sub in subscriptions
        ]
        
        return SubscriptionListResponse(
            items=subscription_responses,
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
            has_more=(pagination.offset + pagination.limit) < total,
        )
        
    except Exception as e:
        logger.error("List subscriptions failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put(
    "/subscriptions/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Update subscription",
    description="Update subscription fields like grace period, expiry date, etc.",
)
async def update_subscription(
    subscription_id: UUID,
    request: SubscriptionUpdate,
    service: SubscriptionService = Depends(get_subscription_service),
    session: AsyncSession = Depends(get_session),
) -> SubscriptionResponse:
    """Update subscription with provided fields."""
    try:
        logger.info("Received subscription update request", 
                   subscription_id=str(subscription_id), 
                   request_data=request.dict())
        
        # Get the current subscription
        subscription = await service.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )
        
        # Update fields that are provided
        if request.tier is not None:
            subscription.tier = request.tier
        if request.status is not None:
            subscription.status = request.status
        if request.max_devices is not None:
            subscription.max_devices = request.max_devices
        if request.expires_at is not None:
            subscription.expires_at = request.expires_at
        if request.grace_period_days is not None:
            subscription.grace_period_days = request.grace_period_days
        if request.price is not None:
            subscription.price = request.price
        if request.currency is not None:
            subscription.currency = request.currency
        if request.auto_renew is not None:
            subscription.auto_renew = request.auto_renew
        if request.custom_features is not None:
            # Update features
            if hasattr(subscription, 'feature_set') and subscription.feature_set:
                subscription.feature_set.features.update(request.custom_features)
        
        # Save the updated subscription
        updated_subscription = await service.subscription_repo.update(subscription)
        
        
        logger.info("Subscription updated successfully", subscription_id=str(subscription_id))
        
        
        return await _subscription_to_response(updated_subscription)
        
    except SubscriptionNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )
    except ValidationError as e:
        logger.error("Validation error in subscription update", 
                    subscription_id=str(subscription_id), 
                    validation_errors=e.errors())
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {e.errors()}",
        )
    except Exception as e:
        logger.error("Update subscription failed", error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put(
    "/subscriptions/{subscription_id}/extend",
    response_model=SubscriptionResponse,
    summary="Extend subscription",
    description="Extend a subscription by specified days",
)
async def extend_subscription(
    subscription_id: UUID,
    request: SubscriptionExtensionRequest,
    service: SubscriptionService = Depends(get_subscription_service),
    session: AsyncSession = Depends(get_session),
) -> SubscriptionResponse:
    """Extend a subscription by specified days."""
    try:
        subscription = await service.extend_subscription(subscription_id, request.days)
        
        return await _subscription_to_response(subscription)
        
    except SubscriptionNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )
    except Exception as e:
        logger.error("Extend subscription failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put(
    "/subscriptions/{subscription_id}/tier",
    response_model=SubscriptionResponse,
    summary="Update subscription tier",
    description="Update subscription tier and features",
)
async def update_subscription_tier(
    subscription_id: UUID,
    request: SubscriptionTierUpdateRequest,
    service: SubscriptionService = Depends(get_subscription_service),
    session: AsyncSession = Depends(get_session),
) -> SubscriptionResponse:
    """Update subscription tier and features."""
    try:
        subscription = await service.update_subscription_tier(
            subscription_id,
            request.tier,
            request.custom_features,
        )
        
        return await _subscription_to_response(subscription)
        
    except SubscriptionNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )
    except Exception as e:
        logger.error("Update subscription tier failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put(
    "/subscriptions/{subscription_id}/suspend",
    response_model=SubscriptionResponse,
    summary="Suspend subscription",
    description="Suspend a subscription",
)
async def suspend_subscription(
    subscription_id: UUID,
    service: SubscriptionService = Depends(get_subscription_service),
    session: AsyncSession = Depends(get_session),
) -> SubscriptionResponse:
    """Suspend a subscription."""
    try:
        subscription = await service.suspend_subscription(subscription_id)
        
        return await _subscription_to_response(subscription)
        
    except SubscriptionNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )
    except Exception as e:
        logger.error("Suspend subscription failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put(
    "/subscriptions/{subscription_id}/cancel",
    response_model=SubscriptionResponse,
    summary="Cancel subscription",
    description="Cancel a subscription",
)
async def cancel_subscription(
    subscription_id: UUID,
    service: SubscriptionService = Depends(get_subscription_service),
    session: AsyncSession = Depends(get_session),
) -> SubscriptionResponse:
    """Cancel a subscription."""
    try:
        subscription = await service.cancel_subscription(subscription_id)
        
        return await _subscription_to_response(subscription)
        
    except SubscriptionNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )
    except Exception as e:
        logger.error("Cancel subscription failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put(
    "/subscriptions/{subscription_id}/resume",
    response_model=SubscriptionResponse,
    summary="Resume subscription",
    description="Resume a suspended or cancelled subscription",
)
async def resume_subscription(
    subscription_id: UUID,
    service: SubscriptionService = Depends(get_subscription_service),
    session: AsyncSession = Depends(get_session),
) -> SubscriptionResponse:
    """Resume a suspended or cancelled subscription."""
    try:
        subscription = await service.resume_subscription(subscription_id)
        
        return await _subscription_to_response(subscription)
        
    except SubscriptionNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )
    except Exception as e:
        logger.error("Resume subscription failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


# Customer management endpoints
@router.post(
    "/customers",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create customer",
    description="Create a new customer",
)
async def create_customer(
    request: CustomerCreate,
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    """Create a new customer."""
    try:
        customer = await service.create_customer(
            name=request.name,
            email=request.email,
            company=request.company,
            phone=request.phone,
            address=request.address,
            metadata=request.metadata,
        )
        
        return CustomerResponse.parse_obj(customer.__dict__)
        
    except Exception as e:
        logger.error("Customer creation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/customers",
    response_model=CustomerListResponse,
    summary="List customers",
    description="List customers with pagination and filtering",
)
async def list_customers(
    pagination: PaginationParams = Depends(),
    filters: CustomerFilters = Depends(),
    service: CustomerService = Depends(get_customer_service),
) -> CustomerListResponse:
    """List customers with pagination and filtering."""
    try:
        result = await service.list_customers(
            limit=pagination.limit,
            offset=pagination.offset,
            search=filters.search,
        )
        
        return CustomerListResponse(
            items=[CustomerResponse.parse_obj(customer.__dict__) for customer in result["customers"]],
            total=result["total"],
            limit=pagination.limit,
            offset=pagination.offset,
            has_more=(pagination.offset + pagination.limit) < result["total"],
        )
        
    except Exception as e:
        logger.error("List customers failed", error=str(e))
        # Temporarily expose the actual error for debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get(
    "/customers/{customer_id}",
    response_model=CustomerWithSubscriptionsResponse,
    summary="Get customer with subscriptions",
    description="Get a customer with their subscriptions",
)
async def get_customer(
    customer_id: UUID,
    service: CustomerService = Depends(get_customer_service),
) -> CustomerWithSubscriptionsResponse:
    """Get a customer with their subscriptions."""
    try:
        result = await service.get_customer_with_subscriptions(customer_id)
        
        return CustomerWithSubscriptionsResponse(
            customer=CustomerResponse.parse_obj(result["customer"].__dict__),
            subscriptions=[
                SubscriptionResponse.parse_obj(sub.__dict__)
                for sub in result["subscriptions"]
            ],
            subscription_count=result["subscription_count"],
            active_subscriptions=result["active_subscriptions"],
        )
        
    except CustomerNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )
    except Exception as e:
        logger.error("Get customer failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


# Analytics endpoints
@router.get(
    "/subscriptions/{subscription_id}/analytics",
    response_model=SubscriptionAnalyticsResponse,
    summary="Get subscription analytics",
    description="Get analytics data for a subscription",
)
async def get_subscription_analytics(
    subscription_id: UUID,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionAnalyticsResponse:
    """Get analytics data for a subscription."""
    try:
        analytics = await service.get_subscription_analytics(subscription_id)
        return SubscriptionAnalyticsResponse.parse_obj(analytics)
        
    except SubscriptionNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )
    except Exception as e:
        logger.error("Get subscription analytics failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/analytics/expiring",
    response_model=List[ExpiringSubscriptionResponse],
    summary="Get expiring subscriptions",
    description="Get subscriptions expiring within specified days",
)
async def get_expiring_subscriptions(
    days: int = 7,
    service: SubscriptionService = Depends(get_subscription_service),
) -> List[ExpiringSubscriptionResponse]:
    """Get subscriptions expiring within specified days."""
    try:
        expiring = await service.get_expiring_subscriptions(days)
        return [ExpiringSubscriptionResponse.parse_obj(item) for item in expiring]
        
    except Exception as e:
        logger.error("Get expiring subscriptions failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/analytics/metrics",
    response_model=MetricsResponse,
    summary="Get system metrics",
    description="Get overall system metrics",
)
async def get_metrics(
    service: SubscriptionService = Depends(get_subscription_service),
) -> MetricsResponse:
    """Get overall system metrics."""
    try:
        # Get subscription metrics
        total_subscriptions = await service.subscription_repo.count()
        active_subscriptions = await service.subscription_repo.count({"status": "active"})
        expired_subscriptions = await service.subscription_repo.count({"status": "expired"})
        
        # Get customer metrics
        total_customers = await service.customer_repo.count()
        
        # Get device metrics
        total_devices = await service.device_repo.count()
        active_devices = await service.device_repo.count({"is_active": True})
        
        # Get subscriptions by tier
        subscriptions_by_tier = {}
        for tier in ["basic", "professional", "enterprise", "trial"]:
            count = await service.subscription_repo.count({"tier": tier})
            subscriptions_by_tier[tier] = count
        
        return MetricsResponse(
            total_subscriptions=total_subscriptions,
            active_subscriptions=active_subscriptions,
            expired_subscriptions=expired_subscriptions,
            total_customers=total_customers,
            total_devices=total_devices,
            active_devices=active_devices,
            subscriptions_by_tier=subscriptions_by_tier,
        )
        
    except Exception as e:
        logger.error("Get metrics failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) 