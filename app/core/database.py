"""
Database Configuration Module

SQLAlchemy 2.0+ configuration with async support.
Follows Instructions file standards for database management and memory leak prevention.
"""

import structlog
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import MetaData, event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Naming convention for constraints
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Base class for all database models.
    
    Follows Instructions file standards for proper abstraction and naming conventions.
    """
    
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class DatabaseManager:
    """
    Database manager for handling connections and sessions.
    
    Implements proper resource management and memory leak prevention
    as specified in Instructions file standards.
    """
    
    def __init__(self) -> None:
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    
    def initialize(self) -> None:
        """
        Initialize database engine and session factory.
        
        Follows Instructions file standards for resource management.
        """
        logger.info("Initializing database connection", database_url=database_url)
        # Convert Railway PostgreSQL URL to asyncpg format if needed
        database_url = str(settings.database_url)
        if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
            logger.info("Converted Railway PostgreSQL URL to asyncpg format")
        
        # Create async engine with proper pool configuration
        pool_class = AsyncAdaptedQueuePool if not settings.is_testing else NullPool
        
        self._engine = create_async_engine(
            database_url,
            echo=settings.database_echo,
            poolclass=pool_class,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,   # Recycle connections every hour
        )
        
        # Configure session factory
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        # Add event listeners for connection management
        self._add_event_listeners()
        
        logger.info("Database connection initialized successfully")
    
    def _add_event_listeners(self) -> None:
        """Add event listeners for connection lifecycle management."""
        if not self._engine:
            return
        
        @event.listens_for(self._engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for better performance (if using SQLite)."""
            if "sqlite" in database_url:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        
        @event.listens_for(self._engine.sync_engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log slow queries in development."""
            if settings.is_development:
                context._query_start_time = time.time()
        
        @event.listens_for(self._engine.sync_engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log slow queries in development."""
            if settings.is_development and hasattr(context, '_query_start_time'):
                total = time.time() - context._query_start_time
                if total > 0.1:  # Log queries taking more than 100ms
                    logger.warning("Slow query detected", duration=total, query=statement[:100])
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session with automatic cleanup.
        
        Implements proper resource management as per Instructions file standards.
        Ensures sessions are properly closed to prevent memory leaks.
        """
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def close(self) -> None:
        """
        Close database connections.
        
        Ensures proper cleanup to prevent memory leaks.
        """
        if self._engine:
            logger.info("Closing database connections")
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database connections closed")
    
    @property
    def engine(self) -> AsyncEngine:
        """Get the database engine."""
        if not self._engine:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine


# Global database manager instance
db_manager = DatabaseManager()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting database session.
    
    Implements proper resource cleanup as per Instructions file standards.
    """
    async with db_manager.get_session() as session:
        yield session


async def init_database() -> None:
    """
    Initialize database connection.
    
    Should be called during application startup.
    """
    db_manager.initialize()


async def close_database() -> None:
    """
    Close database connections.
    
    Should be called during application shutdown to prevent memory leaks.
    """
    await db_manager.close()


# Import time for event listeners
import time 