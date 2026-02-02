"""
Tiered Knowledge Base Service.
Manages L1/L2/L3 knowledge retrieval with cascading search.
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text, func, and_
from sqlalchemy.orm import selectinload
import numpy as np

from app.models.knowledge import KnowledgeBase, PromotionHistory
from app.models.ticket import KnowledgeTier
from app.services.semantic_search import SemanticSearchService, semantic_search_service
from app.config import get_settings

settings = get_settings()


class KnowledgeBaseService:
    """
    Tiered knowledge base management with cascading search.
    - L1: FAQ/Common Issues (self-service)
    - L2: Technical Guides (moderate complexity)
    - L3: Expert Solutions (specialist knowledge)
    """
    
    def __init__(self, search_service: SemanticSearchService = None):
        """Initialize with semantic search service."""
        self._search = search_service or semantic_search_service
    
    async def search_tiered(
        self,
        session: AsyncSession,
        query: str,
        start_tier: KnowledgeTier = KnowledgeTier.L1,
        min_score_threshold: float = 0.5,
        cascade: bool = True
    ) -> Dict[str, Any]:
        """
        Search knowledge base with tiered cascading.
        
        Starts at specified tier, cascades to higher tiers if
        no satisfactory results found.
        
        Args:
            session: Database session
            query: Search query
            start_tier: Tier to start searching from
            min_score_threshold: Minimum hybrid score to accept
            cascade: Whether to cascade to higher tiers
            
        Returns:
            Dictionary with results and search metadata
        """
        tier_order = [KnowledgeTier.L1, KnowledgeTier.L2, KnowledgeTier.L3]
        start_idx = tier_order.index(start_tier)
        
        all_results = []
        searched_tiers = []
        
        for tier in tier_order[start_idx:]:
            results = await self._search.hybrid_search(
                session=session,
                query=query,
                tier=tier,
                top_k=settings.top_k_results
            )
            
            searched_tiers.append(tier.value)
            
            # Filter by threshold
            qualified_results = [
                r for r in results 
                if r["hybrid_score"] >= min_score_threshold
            ]
            
            if qualified_results:
                all_results.extend(qualified_results)
                
                if not cascade:
                    break
                
                # If we found good results, stop cascading
                if qualified_results[0]["hybrid_score"] >= 0.7:
                    break
        
        # Sort all results by hybrid score
        all_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        
        return {
            "results": all_results[:settings.top_k_results],
            "searched_tiers": searched_tiers,
            "total_found": len(all_results),
            "query": query
        }
    
    async def get_by_tier(
        self,
        session: AsyncSession,
        tier: KnowledgeTier,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get all knowledge base entries for a specific tier.
        
        Args:
            session: Database session
            tier: Knowledge tier to retrieve
            category: Optional category filter
            limit: Maximum results
            
        Returns:
            List of knowledge base entries
        """
        query = select(KnowledgeBase).where(
            and_(
                KnowledgeBase.tier == tier,
                KnowledgeBase.is_active == True
            )
        )
        
        if category:
            query = query.where(KnowledgeBase.category == category)
        
        query = query.order_by(KnowledgeBase.usage_count.desc()).limit(limit)
        
        result = await session.execute(query)
        entries = result.scalars().all()
        
        return [
            {
                "id": entry.id,
                "tier": entry.tier.value,
                "title": entry.title,
                "content": entry.content,
                "keywords": entry.keywords,
                "category": entry.category,
                "usage_count": entry.usage_count,
                "avg_feedback_score": entry.avg_feedback_score
            }
            for entry in entries
        ]
    
    async def get_by_id(
        self,
        session: AsyncSession,
        kb_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get a single knowledge base entry by ID."""
        result = await session.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        entry = result.scalar_one_or_none()
        
        if not entry:
            return None
        
        return {
            "id": entry.id,
            "tier": entry.tier.value,
            "title": entry.title,
            "content": entry.content,
            "keywords": entry.keywords,
            "category": entry.category,
            "usage_count": entry.usage_count,
            "success_rate": entry.success_rate,
            "avg_feedback_score": entry.avg_feedback_score,
            "created_at": entry.created_at.isoformat() if entry.created_at else None
        }
    
    async def create_entry(
        self,
        session: AsyncSession,
        tier: KnowledgeTier,
        title: str,
        content: str,
        keywords: List[str] = None,
        category: str = None
    ) -> Dict[str, Any]:
        """
        Create a new knowledge base entry with embedding.
        
        Args:
            session: Database session
            tier: Knowledge tier
            title: Entry title
            content: Solution content
            keywords: Optional keywords list
            category: Optional category
            
        Returns:
            Created entry details
        """
        # Generate embedding for the entry
        combined_text = f"{title} {content}"
        embedding = self._search.encode(combined_text)
        
        entry = KnowledgeBase(
            tier=tier,
            title=title,
            content=content,
            keywords=keywords or [],
            category=category,
            embedding=embedding.tolist()
        )
        
        session.add(entry)
        await session.flush()
        await session.refresh(entry)
        
        return {
            "id": entry.id,
            "tier": entry.tier.value,
            "title": entry.title,
            "message": "Knowledge base entry created successfully"
        }
    
    async def record_usage(
        self,
        session: AsyncSession,
        kb_id: int,
        feedback_score: Optional[int] = None,
        was_successful: bool = True
    ) -> None:
        """
        Record usage of a knowledge base entry.
        Updates usage count, success rate, and feedback score.
        
        Args:
            session: Database session
            kb_id: Knowledge base entry ID
            feedback_score: Optional user feedback (1-5)
            was_successful: Whether resolution was successful
        """
        # Get current entry
        result = await session.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        entry = result.scalar_one_or_none()
        
        if not entry:
            return
        
        # Update usage count
        new_usage_count = entry.usage_count + 1
        
        # Update success rate
        current_successes = entry.success_rate * entry.usage_count
        new_successes = current_successes + (1 if was_successful else 0)
        new_success_rate = new_successes / new_usage_count
        
        # Update average feedback score
        if feedback_score:
            current_feedback_sum = entry.avg_feedback_score * entry.usage_count
            new_feedback_avg = (current_feedback_sum + feedback_score) / new_usage_count
        else:
            new_feedback_avg = entry.avg_feedback_score
        
        await session.execute(
            update(KnowledgeBase)
            .where(KnowledgeBase.id == kb_id)
            .values(
                usage_count=new_usage_count,
                success_rate=new_success_rate,
                avg_feedback_score=new_feedback_avg
            )
        )
    
    async def get_categories(
        self,
        session: AsyncSession,
        tier: Optional[KnowledgeTier] = None
    ) -> List[Dict[str, Any]]:
        """Get list of categories with entry counts."""
        query = """
            SELECT 
                category,
                tier,
                COUNT(*) as count,
                AVG(avg_feedback_score) as avg_score
            FROM knowledge_base
            WHERE is_active = true
        """
        
        params = {}
        if tier:
            query += " AND tier = :tier"
            params["tier"] = tier.value
        
        query += " GROUP BY category, tier ORDER BY count DESC"
        
        result = await session.execute(text(query), params)
        rows = result.fetchall()
        
        return [
            {
                "category": row.category,
                "tier": row.tier,
                "count": row.count,
                "avg_score": float(row.avg_score) if row.avg_score else 0.0
            }
            for row in rows
        ]
    
    async def update_embeddings(
        self,
        session: AsyncSession,
        batch_size: int = 50
    ) -> int:
        """
        Update embeddings for entries that don't have them.
        
        Returns:
            Number of entries updated
        """
        # Find entries without embeddings
        result = await session.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.embedding.is_(None))
            .limit(batch_size)
        )
        entries = result.scalars().all()
        
        updated_count = 0
        for entry in entries:
            combined_text = f"{entry.title} {entry.content}"
            embedding = self._search.encode(combined_text)
            
            await session.execute(
                update(KnowledgeBase)
                .where(KnowledgeBase.id == entry.id)
                .values(embedding=embedding.tolist())
            )
            updated_count += 1
        
        return updated_count


# Global instance
knowledge_base_service = KnowledgeBaseService()
