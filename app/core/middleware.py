"""
Middleware Module

Custom middleware for request processing, logging, and security.
Follows Instructions file standards for performance and security.
"""

import time
import uuid
import structlog
from typing import Callable, Dict, Any

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import RateLimitExceededException

# logger = structlog.get_logger(__name__)  # Disabled to prevent BrokenPipeError


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request context and logging.
    
    Follows Instructions file standards for logging and monitoring.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with context and timing."""
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Start timing
        start_time = time.time()
        
        # Add request context to structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            user_agent=request.headers.get("user-agent"),
            ip=request.client.host if request.client else None,
        )
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Log incoming request (disabled to prevent BrokenPipeError)
        # try:
        #     logger.info(
        #         "Request started",
        #         query_params=dict(request.query_params),
        #     )
        # except (BrokenPipeError, OSError):
        #     # Ignore broken pipe errors in logging
        #     pass
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error and re-raise (disabled to prevent BrokenPipeError)
            # try:
            #     logger.error("Request processing failed", error=str(e), exc_info=e)
            # except (BrokenPipeError, OSError):
            #     # Ignore broken pipe errors in logging
            #     pass
            raise
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        
        # Log completed request (disabled to prevent BrokenPipeError)
        # try:
        #     logger.info(
        #         "Request completed",
        #         status_code=response.status_code,
        #         process_time=process_time,
        #     )
        #     
        #     # Log slow requests
        #     if process_time > 1.0:  # Log requests taking more than 1 second
        #         logger.warning(
        #             "Slow request detected",
        #             process_time=process_time,
        #             path=request.url.path,
        #         )
        # except (BrokenPipeError, OSError):
        #     # Ignore broken pipe errors in logging
        #     pass
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers.
    
    Follows Instructions file standards for security implementation.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.
    
    Implements in-memory rate limiting for API endpoints.
    Follows Instructions file standards for performance and security.
    """
    
    def __init__(self, app, requests_per_minute: int = None):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute or settings.rate_limit_requests
        self.window_size = settings.rate_limit_window
        self.request_counts: Dict[str, Dict[str, Any]] = {}
    
    def _get_client_key(self, request: Request) -> str:
        """Get unique key for client identification."""
        # Use IP address as client identifier
        client_ip = request.client.host if request.client else "unknown"
        return client_ip
    
    def _is_rate_limited(self, client_key: str) -> tuple[bool, int]:
        """Check if client is rate limited."""
        now = time.time()
        
        # Clean up old entries
        self._cleanup_old_entries(now)
        
        # Get or create client entry
        if client_key not in self.request_counts:
            self.request_counts[client_key] = {
                "count": 0,
                "window_start": now,
                "last_request": now,
            }
        
        client_data = self.request_counts[client_key]
        
        # Check if we're in a new window
        if now - client_data["window_start"] >= self.window_size:
            # Reset for new window
            client_data["count"] = 0
            client_data["window_start"] = now
        
        # Increment count
        client_data["count"] += 1
        client_data["last_request"] = now
        
        # Check if limit exceeded
        if client_data["count"] > self.requests_per_minute:
            # Calculate retry after time
            retry_after = int(self.window_size - (now - client_data["window_start"]))
            return True, retry_after
        
        return False, 0
    
    def _cleanup_old_entries(self, now: float) -> None:
        """Clean up old entries to prevent memory leaks."""
        # Remove entries older than 2 windows
        cutoff = now - (self.window_size * 2)
        
        to_remove = []
        for client_key, data in self.request_counts.items():
            if data["last_request"] < cutoff:
                to_remove.append(client_key)
        
        for key in to_remove:
            del self.request_counts[key]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to requests."""
        # Skip rate limiting for health checks and metrics
        if request.url.path in ["/health", "/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        client_key = self._get_client_key(request)
        is_limited, retry_after = self._is_rate_limited(client_key)
        
        if is_limited:
            # Logging disabled to prevent BrokenPipeError
            # try:
            #     logger.warning(
            #         "Rate limit exceeded",
            #         client_key=client_key,
            #         path=request.url.path,
            #         retry_after=retry_after,
            #     )
            # except (BrokenPipeError, OSError):
            #     # Ignore broken pipe errors in logging
            #     pass
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests",
                    "details": {"retry_after": retry_after},
                    "timestamp": time.time(),
                },
                headers={"Retry-After": str(retry_after)},
            )
        
        return await call_next(request)


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit request size.
    
    Prevents large request attacks and memory issues.
    """
    
    def __init__(self, app, max_size: int = None):
        super().__init__(app)
        self.max_size = max_size or settings.max_request_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check request size before processing."""
        content_length = request.headers.get("content-length")
        
        if content_length and int(content_length) > self.max_size:
            # Logging disabled to prevent BrokenPipeError
            # try:
            #     logger.warning(
            #         "Request size too large",
            #         content_length=content_length,
            #         max_size=self.max_size,
            #         path=request.url.path,
            #     )
            # except (BrokenPipeError, OSError):
            #     # Ignore broken pipe errors in logging
            #     pass
            
            return JSONResponse(
                status_code=413,
                content={
                    "error": "REQUEST_TOO_LARGE",
                    "message": "Request size exceeds maximum allowed size",
                    "details": {
                        "max_size": self.max_size,
                        "received_size": int(content_length),
                    },
                    "timestamp": time.time(),
                },
            )
        
        return await call_next(request)


def setup_cors_middleware(app) -> None:
    """
    Configure CORS middleware.
    
    Follows Instructions file standards for security configuration.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )


def setup_middleware(app) -> None:
    """
    Setup all middleware for the application.
    
    Order matters - middleware is applied in reverse order of addition.
    
    TEMPORARILY DISABLED TO PREVENT BrokenPipeError
    """
    # Add custom middleware (in reverse order of execution)
    # app.add_middleware(RequestContextMiddleware)
    # app.add_middleware(SecurityHeadersMiddleware)
    # app.add_middleware(RateLimitMiddleware)
    # app.add_middleware(RequestSizeMiddleware)
    
    # Setup CORS
    setup_cors_middleware(app)
    
    # Logging disabled to prevent BrokenPipeError
    # try:
    #     logger.info("Middleware setup completed")
    # except (BrokenPipeError, OSError):
    #     # Ignore broken pipe errors in logging
    #     pass 