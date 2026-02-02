"""
Integration tests for FastAPI REST API endpoints.
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, async_client: AsyncClient):
        """Test health check returns correct structure."""
        response = await async_client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "models_loaded" in data
        assert "version" in data


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    @pytest.mark.asyncio
    async def test_root_info(self, async_client: AsyncClient):
        """Test root endpoint returns API info."""
        response = await async_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "SupportIQ"
        assert "version" in data
        assert "features" in data
        assert "endpoints" in data


class TestAnalyzeEndpoint:
    """Tests for text analysis endpoint."""
    
    @pytest.mark.asyncio
    async def test_analyze_text(self, async_client: AsyncClient):
        """Test text analysis without creating ticket."""
        response = await async_client.post(
            "/api/v1/analyze",
            params={
                "title": "Cannot access email",
                "description": "Outlook is not working properly and I need help urgently!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check sentiment analysis
        assert "sentiment" in data
        assert "label" in data["sentiment"]
        assert "score" in data["sentiment"]
        
        # Check urgency analysis
        assert "urgency" in data
        assert "score" in data["urgency"]
        assert 1 <= data["urgency"]["score"] <= 10
        assert "level" in data["urgency"]
        assert "tier" in data["urgency"]


class TestSearchEndpoint:
    """Tests for search endpoint structure."""
    
    @pytest.mark.asyncio
    async def test_search_request_validation(self, async_client: AsyncClient):
        """Test search endpoint validates input."""
        # Short query should fail
        response = await async_client.post(
            "/api/v1/search",
            json={"query": "ab"}  # Too short
        )
        
        assert response.status_code == 422  # Validation error


class TestOpenAPIDocumentation:
    """Tests for API documentation."""
    
    @pytest.mark.asyncio
    async def test_openapi_docs_available(self, async_client: AsyncClient):
        """Test OpenAPI documentation is accessible."""
        response = await async_client.get("/docs")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_redoc_available(self, async_client: AsyncClient):
        """Test ReDoc documentation is accessible."""
        response = await async_client.get("/redoc")
        
        assert response.status_code == 200
