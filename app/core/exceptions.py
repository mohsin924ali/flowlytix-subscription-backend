"""
Custom Exceptions Module

Centralized exception handling for the subscription server.
Follows Instructions file standards for error handling and logging.
"""

import structlog
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


class BaseSubscriptionException(Exception):
    """
    Base exception for subscription-related errors.
    
    Follows Instructions file standards for exception design.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "SUBSCRIPTION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(BaseSubscriptionException):
    """Exception for data validation errors."""
    
    def __init__(self, message: str, field: str = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details or {}
        )
        if field:
            self.details["field"] = field


class AuthenticationException(BaseSubscriptionException):
    """Exception for authentication errors."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=details or {}
        )


class AuthorizationException(BaseSubscriptionException):
    """Exception for authorization errors."""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=details or {}
        )


class SubscriptionNotFoundException(BaseSubscriptionException):
    """Exception for subscription not found errors."""
    
    def __init__(self, subscription_id: str = None, license_key: str = None):
        message = "Subscription not found"
        details = {}
        
        if subscription_id:
            details["subscription_id"] = subscription_id
        if license_key:
            details["license_key"] = license_key[:8] + "***"  # Mask license key for security
            
        super().__init__(
            message=message,
            error_code="SUBSCRIPTION_NOT_FOUND",
            details=details
        )


class DeviceNotFoundException(BaseSubscriptionException):
    """Exception for device not found errors."""
    
    def __init__(self, device_id: str = None):
        message = "Device not found"
        details = {}
        
        if device_id:
            details["device_id"] = device_id
            
        super().__init__(
            message=message,
            error_code="DEVICE_NOT_FOUND",
            details=details
        )


class CustomerNotFoundException(BaseSubscriptionException):
    """Exception for customer not found errors."""
    
    def __init__(self, customer_id: str = None):
        message = "Customer not found"
        details = {}
        
        if customer_id:
            details["customer_id"] = customer_id
            
        super().__init__(
            message=message,
            error_code="CUSTOMER_NOT_FOUND",
            details=details
        )


class SubscriptionExpiredException(BaseSubscriptionException):
    """Exception for expired subscription errors."""
    
    def __init__(self, subscription_id: str = None, expired_at: str = None):
        message = "Subscription has expired"
        details = {}
        
        if subscription_id:
            details["subscription_id"] = subscription_id
        if expired_at:
            details["expired_at"] = expired_at
            
        super().__init__(
            message=message,
            error_code="SUBSCRIPTION_EXPIRED",
            details=details
        )


class DeviceLimitExceededException(BaseSubscriptionException):
    """Exception for device limit exceeded errors."""
    
    def __init__(self, current_devices: int = None, max_devices: int = None):
        message = "Device limit exceeded"
        details = {}
        
        if current_devices is not None:
            details["current_devices"] = current_devices
        if max_devices is not None:
            details["max_devices"] = max_devices
            
        super().__init__(
            message=message,
            error_code="DEVICE_LIMIT_EXCEEDED",
            details=details
        )


class LicenseKeyInvalidException(BaseSubscriptionException):
    """Exception for invalid license key errors."""
    
    def __init__(self, reason: str = "Invalid format"):
        super().__init__(
            message=f"License key is invalid: {reason}",
            error_code="LICENSE_KEY_INVALID",
            details={"reason": reason}
        )


class DatabaseException(BaseSubscriptionException):
    """Exception for database-related errors."""
    
    def __init__(self, message: str, operation: str = None):
        details = {}
        if operation:
            details["operation"] = operation
            
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details=details
        )


class RepositoryException(BaseSubscriptionException):
    """Exception for repository layer errors."""
    
    def __init__(self, message: str, entity: str = None, operation: str = None):
        details = {}
        if entity:
            details["entity"] = entity
        if operation:
            details["operation"] = operation
            
        super().__init__(
            message=message,
            error_code="REPOSITORY_ERROR",
            details=details
        )


class ExternalServiceException(BaseSubscriptionException):
    """Exception for external service errors."""
    
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"External service error: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service}
        )


class RateLimitExceededException(BaseSubscriptionException):
    """Exception for rate limit exceeded errors."""
    
    def __init__(self, retry_after: int = None):
        message = "Rate limit exceeded"
        details = {}
        
        if retry_after:
            details["retry_after"] = retry_after
            
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details
        )


class DomainException(BaseSubscriptionException):
    """Exception for domain model violations and business rule errors."""
    
    def __init__(self, message: str, entity: str = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if entity:
            details["entity"] = entity
            
        super().__init__(
            message=message,
            error_code="DOMAIN_ERROR",
            details=details
        )


class BusinessLogicException(BaseSubscriptionException):
    """Exception for business logic errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            details=details or {}
        )


# HTTP Exception mappings
EXCEPTION_STATUS_MAP = {
    ValidationException: status.HTTP_422_UNPROCESSABLE_ENTITY,
    AuthenticationException: status.HTTP_401_UNAUTHORIZED,
    AuthorizationException: status.HTTP_403_FORBIDDEN,
    SubscriptionNotFoundException: status.HTTP_404_NOT_FOUND,
    DeviceNotFoundException: status.HTTP_404_NOT_FOUND,
    CustomerNotFoundException: status.HTTP_404_NOT_FOUND,
    SubscriptionExpiredException: status.HTTP_410_GONE,
    DeviceLimitExceededException: status.HTTP_409_CONFLICT,
    LicenseKeyInvalidException: status.HTTP_400_BAD_REQUEST,
    DatabaseException: status.HTTP_500_INTERNAL_SERVER_ERROR,
    RepositoryException: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ExternalServiceException: status.HTTP_502_BAD_GATEWAY,
    RateLimitExceededException: status.HTTP_429_TOO_MANY_REQUESTS,
    DomainException: status.HTTP_400_BAD_REQUEST,
    BusinessLogicException: status.HTTP_400_BAD_REQUEST,
}


async def subscription_exception_handler(request: Request, exc: BaseSubscriptionException) -> JSONResponse:
    """
    Global exception handler for subscription-related exceptions.
    
    Follows Instructions file standards for error handling and logging.
    """
    # Log the exception with context
    logger.error(
        "Subscription exception occurred",
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        path=request.url.path,
        method=request.method,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    
    # Determine HTTP status code
    status_code = EXCEPTION_STATUS_MAP.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Prepare response
    response_data = {
        "error": exc.error_code,
        "message": exc.message,
        "details": exc.details,
        "timestamp": logger._context.get("timestamp"),
    }
    
    # Add retry_after header for rate limiting
    headers = {}
    if isinstance(exc, RateLimitExceededException) and "retry_after" in exc.details:
        headers["Retry-After"] = str(exc.details["retry_after"])
    
    return JSONResponse(
        status_code=status_code,
        content=response_data,
        headers=headers,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Global exception handler for HTTP exceptions.
    
    Provides consistent error response format.
    """
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "details": {},
            "timestamp": logger._context.get("timestamp"),
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unexpected exceptions.
    
    Ensures no sensitive information is exposed in production.
    """
    logger.error(
        "Unexpected exception occurred",
        error_type=type(exc).__name__,
        error_message=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=exc,
    )
    
    # Don't expose internal error details in production
    from app.core.config import settings
    
    if settings.is_production:
        message = "An internal server error occurred"
        details = {}
    else:
        message = str(exc)
        details = {"error_type": type(exc).__name__}
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": message,
            "details": details,
            "timestamp": logger._context.get("timestamp"),
        },
    ) 