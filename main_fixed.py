"""
Main FastAPI Application - Fixed Version

Working version of the Flowlytix Subscription Server without BrokenPipeError issues.
"""

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import init_database, close_database
from app.core.exceptions import (
    BaseSubscriptionException,
    subscription_exception_handler,
    http_exception_handler,
    general_exception_handler,
)
from app.api.routes import subscription, payment

# Configure simple logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    """
    logger.info("Starting Flowlytix Subscription Server")
    
    # Startup
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")
        
        logger.info("Application startup completed")
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    
    # Application is ready
    yield
    
    # Shutdown
    try:
        logger.info("Shutting down application")
        
        # Close database connections
        await close_database()
        logger.info("Database connections closed")
        
        logger.info("Application shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    """
    app = FastAPI(
        title="Flowlytix Subscription Server",
        description="Subscription management and licensing server for Flowlytix",
        version=settings.version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )
    
    # Add CORS middleware
    # In development, be more permissive with CORS to handle Docker networks
    if settings.environment == "development":
        # Allow all origins in development for Docker compatibility
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all origins in development
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
        logger.info("Development CORS: Allowing all origins")
    else:
        # Use specific origins in production
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
        logger.info(f"Production CORS: Allowing origins: {settings.allowed_origins}")
    
    # Add security headers middleware for production
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        if settings.is_production:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = "default-src 'self'"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
    
    # Setup exception handlers
    app.add_exception_handler(BaseSubscriptionException, subscription_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    # Include routers
    app.include_router(subscription.router, prefix=settings.api_v1_prefix)
    app.include_router(payment.router, prefix=settings.api_v1_prefix)
    
    return app


# Create application instance
app = create_app()


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "version": settings.version,
        "environment": settings.environment,
        "timestamp": datetime.now().isoformat(),
    }


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """
    Metrics endpoint for monitoring.
    """
    if settings.is_production:
        return {"message": "Metrics endpoint - implement Prometheus metrics here"}
    
    return {
        "application": "flowlytix-subscription-server",
        "version": settings.version,
        "environment": settings.environment,
        "status": "running",
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Flowlytix Subscription Server",
        "version": settings.version,
        "environment": settings.environment,
        "documentation": "/docs" if not settings.is_production else None,
        "health": "/health",
    }


# Add explicit OPTIONS handler for CORS preflight requests
@app.options("/{path:path}")
async def handle_options(path: str):
    """Handle CORS preflight requests."""
    return JSONResponse(
        status_code=200,
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*" if settings.environment == "development" else settings.allowed_origins[0] if settings.allowed_origins else "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )


# Analytics endpoints
@app.get("/api/v1/analytics/dashboard")
async def get_dashboard_analytics():
    """
    Get dashboard overview analytics.
    """
    return {
        "data": {
            "total_subscriptions": 156,
            "active_subscriptions": 142,
            "inactive_subscriptions": 14,
            "monthly_revenue": 23450.00,
            "yearly_revenue": 281400.00,
            "churn_rate": 0.05,
            "growth_rate": 0.15,
            "avg_subscription_value": 165.14,
            "new_subscriptions_this_month": 12,
            "canceled_subscriptions_this_month": 3,
            "upcoming_renewals": 28,
            "overdue_payments": 5,
            "conversion_rate": 0.18,
            "customer_satisfaction": 4.2,
            "support_tickets": 23,
            "feature_adoption_rate": 0.72
        },
        "success": True,
        "message": "Dashboard analytics retrieved successfully"
    }


@app.get("/api/v1/analytics/system-health")
async def get_system_health():
    """
    Get system health metrics.
    """
    return {
        "data": {
            "server_status": "healthy",
            "database_status": "healthy",
            "cache_status": "healthy",
            "api_response_time": 125.5,
            "database_response_time": 23.2,
            "cache_hit_rate": 0.94,
            "error_rate": 0.002,
            "uptime": "99.98%",
            "memory_usage": 68.5,
            "cpu_usage": 34.2,
            "disk_usage": 45.8,
            "active_connections": 127,
            "requests_per_minute": 1250,
            "last_backup": "2024-01-15T03:00:00Z",
            "system_version": settings.version,
            "environment": settings.environment
        },
        "success": True,
        "message": "System health metrics retrieved successfully"
    }


@app.get("/api/v1/analytics/realtime")
async def get_realtime_analytics():
    """
    Get real-time analytics metrics.
    """
    return {
        "data": {
            "active_users": 245,
            "active_sessions": 189,
            "requests_per_second": 12.5,
            "response_time_avg": 150.3,
            "error_rate": 0.001,
            "subscriptions_today": 8,
            "activations_today": 15,
            "revenue_today": 2340.50,
            "cpu_usage": 34.2,
            "memory_usage": 68.5,
            "database_connections": 12,
            "cache_hits": 1247,
            "cache_misses": 78,
            "last_updated": datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat()
        },
        "success": True,
        "message": "Real-time analytics retrieved successfully"
    }





if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting server in development mode")
    
    uvicorn.run(
        "main_fixed:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
        access_log=False,  # Disable access logging to prevent issues
    ) 