"""
Unit tests for Semantic Search Service.
"""

import pytest
import numpy as np


class TestSemanticSearch:
    """Tests for MiniLM semantic search service."""
    
    def test_singleton_pattern(self):
        """Test that service uses singleton pattern."""
        from app.services.semantic_search import SemanticSearchService
        
        service1 = SemanticSearchService()
        service2 = SemanticSearchService()
        
        assert service1 is service2
    
    def test_encode_returns_correct_dimensions(self):
        """Test that encoding produces 384-dimensional vectors."""
        from app.services.semantic_search import semantic_search_service
        
        embedding = semantic_search_service.encode("Test query about password reset")
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
    
    def test_encode_empty_text(self):
        """Test encoding empty text returns zero vector."""
        from app.services.semantic_search import semantic_search_service
        
        embedding = semantic_search_service.encode("")
        
        assert np.allclose(embedding, np.zeros(384))
    
    def test_batch_encoding(self):
        """Test batch encoding of multiple texts."""
        from app.services.semantic_search import semantic_search_service
        
        texts = [
            "Password reset issue",
            "Email not working",
            "VPN connection problem"
        ]
        
        embeddings = semantic_search_service.encode_batch(texts)
        
        assert embeddings.shape == (3, 384)
    
    def test_similarity_calculation(self):
        """Test cosine similarity calculation."""
        from app.services.semantic_search import semantic_search_service
        
        # Similar texts should have high similarity
        emb1 = semantic_search_service.encode("Cannot reset my password")
        emb2 = semantic_search_service.encode("Password reset not working")
        
        similarity = semantic_search_service.similarity(emb1, emb2)
        
        assert 0 <= similarity <= 1
        assert similarity > 0.7  # Should be highly similar
    
    def test_dissimilar_texts(self):
        """Test that dissimilar texts have lower similarity."""
        from app.services.semantic_search import semantic_search_service
        
        emb1 = semantic_search_service.encode("Password reset issue")
        emb2 = semantic_search_service.encode("Weather forecast for tomorrow")
        
        similarity = semantic_search_service.similarity(emb1, emb2)
        
        assert similarity < 0.5  # Should be less similar
