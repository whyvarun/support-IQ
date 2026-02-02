"""
Semantic Search Service using Sentence Transformers MiniLM.
Provides hybrid search combining semantic similarity and keyword matching.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from sklearn.metrics.pairwise import cosine_similarity

from app.config import get_settings
from app.models.knowledge import KnowledgeBase
from app.models.ticket import KnowledgeTier

settings = get_settings()


class SemanticSearchService:
    """
    Semantic search service using MiniLM for embeddings.
    Supports hybrid search combining semantic and keyword matching.
    """
    
    _instance = None
    _model = None
    
    def __new__(cls):
        """Singleton pattern to avoid loading model multiple times."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the sentence transformer model."""
        if self._initialized:
            return
        
        print(f"Loading MiniLM model: {settings.minilm_model}")
        self._model = SentenceTransformer(settings.minilm_model)
        self._initialized = True
        print("MiniLM model loaded successfully!")
    
    def encode(self, text: str) -> np.ndarray:
        """
        Encode text into a 384-dimensional vector embedding.
        
        Args:
            text: Input text to encode
            
        Returns:
            numpy array of shape (384,)
        """
        if not text or not text.strip():
            return np.zeros(384)
        
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding
    
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        Encode multiple texts into embeddings.
        
        Args:
            texts: List of input texts
            
        Returns:
            numpy array of shape (n, 384)
        """
        if not texts:
            return np.array([])
        
        embeddings = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between 0 and 1
        """
        if embedding1.ndim == 1:
            embedding1 = embedding1.reshape(1, -1)
        if embedding2.ndim == 1:
            embedding2 = embedding2.reshape(1, -1)
        
        return float(cosine_similarity(embedding1, embedding2)[0][0])
    
    async def hybrid_search(
        self,
        session: AsyncSession,
        query: str,
        tier: Optional[KnowledgeTier] = None,
        top_k: int = None,
        semantic_weight: float = None,
        keyword_weight: float = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic similarity and keyword matching.
        
        Args:
            session: Database session
            query: Search query text
            tier: Optional tier filter (L1, L2, L3)
            top_k: Number of results to return
            semantic_weight: Weight for semantic similarity (0-1)
            keyword_weight: Weight for keyword matching (0-1)
            
        Returns:
            List of knowledge base entries with scores
        """
        top_k = top_k or settings.top_k_results
        semantic_weight = semantic_weight or settings.semantic_weight
        keyword_weight = keyword_weight or settings.keyword_weight
        
        # Generate query embedding
        query_embedding = self.encode(query)
        query_embedding_list = query_embedding.tolist()
        
        # Build the hybrid search query
        # Semantic similarity using pgvector cosine distance
        # Keyword search using PostgreSQL full-text search
        
        base_query = """
            SELECT 
                kb.id,
                kb.tier,
                kb.title,
                kb.content,
                kb.keywords,
                kb.category,
                kb.usage_count,
                kb.avg_feedback_score,
                1 - (kb.embedding <=> :query_embedding::vector) as semantic_score,
                ts_rank(
                    to_tsvector('english', kb.title || ' ' || kb.content),
                    plainto_tsquery('english', :query_text)
                ) as keyword_score
            FROM knowledge_base kb
            WHERE kb.is_active = true
                AND kb.embedding IS NOT NULL
        """
        
        params = {
            "query_embedding": str(query_embedding_list),
            "query_text": query
        }
        
        if tier:
            base_query += " AND kb.tier = :tier"
            params["tier"] = tier.value
        
        # Wrap with hybrid scoring
        hybrid_query = f"""
            SELECT *,
                (semantic_score * :semantic_weight + keyword_score * :keyword_weight) as hybrid_score
            FROM ({base_query}) subq
            ORDER BY hybrid_score DESC
            LIMIT :top_k
        """
        
        params.update({
            "semantic_weight": semantic_weight,
            "keyword_weight": keyword_weight,
            "top_k": top_k
        })
        
        result = await session.execute(text(hybrid_query), params)
        rows = result.fetchall()
        
        return [
            {
                "id": row.id,
                "tier": row.tier,
                "title": row.title,
                "content": row.content,
                "keywords": row.keywords,
                "category": row.category,
                "usage_count": row.usage_count,
                "avg_feedback_score": row.avg_feedback_score,
                "semantic_score": float(row.semantic_score) if row.semantic_score else 0.0,
                "keyword_score": float(row.keyword_score) if row.keyword_score else 0.0,
                "hybrid_score": float(row.hybrid_score) if row.hybrid_score else 0.0
            }
            for row in rows
        ]
    
    async def search_by_tier(
        self,
        session: AsyncSession,
        query: str,
        tiers: List[KnowledgeTier],
        top_k: int = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search across multiple tiers and return results grouped by tier.
        
        Args:
            session: Database session
            query: Search query
            tiers: List of tiers to search
            top_k: Results per tier
            
        Returns:
            Dictionary with tier names as keys and results as values
        """
        results = {}
        for tier in tiers:
            tier_results = await self.hybrid_search(
                session=session,
                query=query,
                tier=tier,
                top_k=top_k
            )
            results[tier.value] = tier_results
        
        return results
    
    async def find_similar_tickets(
        self,
        session: AsyncSession,
        query_embedding: np.ndarray,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar past tickets based on embedding similarity.
        
        Args:
            session: Database session
            query_embedding: Query embedding vector
            limit: Number of results
            
        Returns:
            List of similar tickets with similarity scores
        """
        query = """
            SELECT 
                t.id,
                t.title,
                t.description,
                t.status,
                t.category,
                r.solution,
                r.feedback_score,
                1 - (te.embedding <=> :query_embedding::vector) as similarity
            FROM tickets t
            JOIN ticket_embeddings te ON t.id = te.ticket_id
            LEFT JOIN resolutions r ON t.id = r.ticket_id
            WHERE t.status IN ('resolved', 'closed')
            ORDER BY similarity DESC
            LIMIT :limit
        """
        
        result = await session.execute(
            text(query),
            {
                "query_embedding": str(query_embedding.tolist()),
                "limit": limit
            }
        )
        rows = result.fetchall()
        
        return [
            {
                "id": row.id,
                "title": row.title,
                "description": row.description,
                "status": row.status,
                "category": row.category,
                "solution": row.solution,
                "feedback_score": row.feedback_score,
                "similarity": float(row.similarity) if row.similarity else 0.0
            }
            for row in rows
        ]


# Global instance
semantic_search_service = SemanticSearchService()
