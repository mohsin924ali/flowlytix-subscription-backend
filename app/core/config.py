"""
Application Configuration Module

Centralized configuration management using Pydantic Settings.
Follows Instructions file standards for configuration management.
"""

from typing import Optional
from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    All settings can be overridden via environment variables.
    Follows Instructions file standards for configuration management.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = Field(default="Flowlytix Subscription Server", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(default="development", description="Environment (development/staging/production)")
    
    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=False, description="Auto-reload on code changes")
    
    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://user:pass@localhost:5432/flowlytix_subscriptions",
        description="Database connection URL"
    )
    database_pool_size: int = Field(default=10, description="Database connection pool size")
    database_max_overflow: int = Field(default=20, description="Database max overflow connections")
    database_echo: bool = Field(default=False, description="Echo SQL statements")
    
    # Redis
    redis_url: Optional[RedisDsn] = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    redis_max_connections: int = Field(default=50, description="Redis max connections")
    redis_key_prefix: str = Field(default="flowlytix:subscription:", description="Redis key prefix")
    
    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT signing"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration in minutes")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration in days")
    
    # JWT RSA Keys for subscription tokens
    private_key_path: str = Field(
        default="keys/private_key.pem",
        description="Path to RSA private key for JWT signing"
    )
    public_key_path: str = Field(
        default="keys/public_key.pem",
        description="Path to RSA public key for JWT verification"
    )
    
    # API
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")
    max_request_size: int = Field(default=10 * 1024 * 1024, description="Max request size in bytes (10MB)")
    
    # CORS
    allowed_hosts: list[str] = Field(
        default=["localhost", "127.0.0.1", "0.0.0.0"],
        description="Allowed hosts for CORS"
    )
    allowed_origins: list[str] = Field(
        default=[
            "https://flowlytix-subscription-dashboard.vercel.app",
            "http://localhost:3000", 
            "http://localhost:8080"
        ],
        description="Allowed origins for CORS"
    )
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per window")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # External Services
    email_service_api_key: Optional[str] = Field(default=None, description="Email service API key")
    email_from: str = Field(default="noreply@flowlytix.com", description="Email from address")
    
    # Subscription Settings
    default_grace_period_days: int = Field(default=7, description="Default grace period in days")
    max_devices_per_subscription: int = Field(default=10, description="Max devices per subscription")
    license_key_length: int = Field(default=32, description="License key length")
    
    # Feature Flags
    enable_analytics: bool = Field(default=True, description="Enable analytics collection")
    enable_notifications: bool = Field(default=True, description="Enable email notifications")
    enable_device_tracking: bool = Field(default=True, description="Enable device tracking")
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() in ("development", "dev")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() in ("production", "prod")
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment.lower() in ("testing", "test")


# Global settings instance
settings = Settings() 