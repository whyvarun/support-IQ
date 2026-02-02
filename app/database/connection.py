"""
Database connection and session management for SupportIQ.
Supports both async (for API) and sync (for ML operations) connections.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.config import get_settings

settings = get_settings()

# Base class for all ORM models
Base = declarative_base()

# Async engine for FastAPI endpoints
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

# Sync engine for ML operations that don't support async
sync_engine = create_engine(
    settings.database_url_sync,
    echo=settings.debug,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)

# Session factories
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autoflush=False,
    autocommit=False
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_async_context_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for async session outside of FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session():
    """Get synchronous session for ML operations."""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def init_db():
    """Initialize database tables (for development/testing)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    await async_engine.dispose()
