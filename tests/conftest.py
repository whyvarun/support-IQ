"""
Pytest configuration and fixtures.
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Use SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API testing."""
    from app.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
