"""
Auto-Promotion Service.
Automatically promotes frequently resolved queries between tiers.
L3 -> L2 when resolved >10 times with high feedback
L2 -> L1 when resolved >25 times with high feedback
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from datetime import datetime

from app.models.knowledge import KnowledgeBase, PromotionHistory
from app.models.ticket import KnowledgeTier
from app.config import get_settings

settings = get_settings()


class AutoPromotionService:
    """
    Automatic promotion of knowledge base entries between tiers.
    
    Promotion Rules:
    - L3 -> L2: usage_count >= 10, avg_feedback >= 4.0
    - L2 -> L1: usage_count >= 25, avg_feedback >= 4.0
    """
    
    def __init__(self):
        """Initialize promotion thresholds from settings."""
        self.l3_to_l2_threshold = settings.l3_to_l2_threshold
        self.l2_to_l1_threshold = settings.l2_to_l1_threshold
        self.min_feedback_score = settings.min_feedback_score
    
    async def check_and_promote(
        self,
        session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Check all entries for promotion eligibility and promote if qualified.
        
        Returns:
            List of promoted entries with details
        """
        promotions = []
        
        # Check L3 -> L2 promotions
        l3_promotions = await self._check_tier_promotions(
            session=session,
            from_tier=KnowledgeTier.L3,
            to_tier=KnowledgeTier.L2,
            usage_threshold=self.l3_to_l2_threshold
        )
        promotions.extend(l3_promotions)
        
        # Check L2 -> L1 promotions
        l2_promotions = await self._check_tier_promotions(
            session=session,
            from_tier=KnowledgeTier.L2,
            to_tier=KnowledgeTier.L1,
            usage_threshold=self.l2_to_l1_threshold
        )
        promotions.extend(l2_promotions)
        
        return promotions
    
    async def _check_tier_promotions(
        self,
        session: AsyncSession,
        from_tier: KnowledgeTier,
        to_tier: KnowledgeTier,
        usage_threshold: int
    ) -> List[Dict[str, Any]]:
        """
        Check and execute promotions for a specific tier transition.
        
        Args:
            session: Database session
            from_tier: Source tier
            to_tier: Target tier
            usage_threshold: Minimum usage count for promotion
            
        Returns:
            List of promoted entries
        """
        # Find entries eligible for promotion
        result = await session.execute(
            select(KnowledgeBase).where(
                and_(
                    KnowledgeBase.tier == from_tier,
                    KnowledgeBase.is_active == True,
                    KnowledgeBase.usage_count >= usage_threshold,
                    KnowledgeBase.avg_feedback_score >= self.min_feedback_score
                )
            )
        )
        eligible_entries = result.scalars().all()
        
        promotions = []
        for entry in eligible_entries:
            # Check if already promoted (avoid duplicate promotions)
            existing_promotion = await session.execute(
                select(PromotionHistory).where(
                    and_(
                        PromotionHistory.knowledge_id == entry.id,
                        PromotionHistory.from_tier == from_tier,
                        PromotionHistory.to_tier == to_tier
                    )
                )
            )
            
            if existing_promotion.scalar_one_or_none():
                continue  # Already promoted
            
            # Execute promotion
            await self._promote_entry(
                session=session,
                entry=entry,
                from_tier=from_tier,
                to_tier=to_tier
            )
            
            promotions.append({
                "id": entry.id,
                "title": entry.title,
                "from_tier": from_tier.value,
                "to_tier": to_tier.value,
                "usage_count": entry.usage_count,
                "avg_feedback": entry.avg_feedback_score,
                "promoted_at": datetime.now().isoformat()
            })
        
        return promotions
    
    async def _promote_entry(
        self,
        session: AsyncSession,
        entry: KnowledgeBase,
        from_tier: KnowledgeTier,
        to_tier: KnowledgeTier
    ) -> None:
        """
        Promote a single entry and record in history.
        
        Args:
            session: Database session
            entry: Knowledge base entry to promote
            from_tier: Source tier
            to_tier: Target tier
        """
        reason = (
            f"Auto-promoted: usage_count={entry.usage_count} >= threshold, "
            f"avg_feedback={entry.avg_feedback_score:.2f} >= {self.min_feedback_score}"
        )
        
        # Update entry tier
        await session.execute(
            update(KnowledgeBase)
            .where(KnowledgeBase.id == entry.id)
            .values(tier=to_tier)
        )
        
        # Record promotion history
        history = PromotionHistory(
            knowledge_id=entry.id,
            from_tier=from_tier,
            to_tier=to_tier,
            reason=reason,
            usage_count_at_promotion=entry.usage_count,
            avg_feedback_at_promotion=entry.avg_feedback_score
        )
        session.add(history)
    
    async def force_promote(
        self,
        session: AsyncSession,
        kb_id: int,
        to_tier: KnowledgeTier,
        reason: str = "Manual promotion"
    ) -> Optional[Dict[str, Any]]:
        """
        Manually promote an entry to a specific tier.
        
        Args:
            session: Database session
            kb_id: Knowledge base entry ID
            to_tier: Target tier
            reason: Reason for promotion
            
        Returns:
            Promotion details or None if entry not found
        """
        result = await session.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        entry = result.scalar_one_or_none()
        
        if not entry:
            return None
        
        from_tier = entry.tier
        
        # Update entry
        await session.execute(
            update(KnowledgeBase)
            .where(KnowledgeBase.id == kb_id)
            .values(tier=to_tier)
        )
        
        # Record history
        history = PromotionHistory(
            knowledge_id=kb_id,
            from_tier=from_tier,
            to_tier=to_tier,
            reason=reason,
            usage_count_at_promotion=entry.usage_count,
            avg_feedback_at_promotion=entry.avg_feedback_score
        )
        session.add(history)
        
        return {
            "id": kb_id,
            "title": entry.title,
            "from_tier": from_tier.value,
            "to_tier": to_tier.value,
            "reason": reason
        }
    
    async def get_promotion_history(
        self,
        session: AsyncSession,
        kb_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get promotion history, optionally filtered by entry ID.
        
        Args:
            session: Database session
            kb_id: Optional knowledge base ID filter
            limit: Maximum results
            
        Returns:
            List of promotion history records
        """
        query = select(PromotionHistory).order_by(
            PromotionHistory.promoted_at.desc()
        )
        
        if kb_id:
            query = query.where(PromotionHistory.knowledge_id == kb_id)
        
        query = query.limit(limit)
        
        result = await session.execute(query)
        records = result.scalars().all()
        
        return [
            {
                "id": record.id,
                "knowledge_id": record.knowledge_id,
                "from_tier": record.from_tier.value,
                "to_tier": record.to_tier.value,
                "reason": record.reason,
                "usage_count": record.usage_count_at_promotion,
                "avg_feedback": record.avg_feedback_at_promotion,
                "promoted_at": record.promoted_at.isoformat() if record.promoted_at else None
            }
            for record in records
        ]
    
    async def get_promotion_candidates(
        self,
        session: AsyncSession
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get entries that are close to meeting promotion criteria.
        
        Returns:
            Dictionary with L3_to_L2 and L2_to_L1 candidates
        """
        candidates = {
            "L3_to_L2": [],
            "L2_to_L1": []
        }
        
        # L3 entries approaching promotion
        l3_result = await session.execute(
            select(KnowledgeBase).where(
                and_(
                    KnowledgeBase.tier == KnowledgeTier.L3,
                    KnowledgeBase.is_active == True,
                    KnowledgeBase.usage_count >= self.l3_to_l2_threshold * 0.7  # 70% threshold
                )
            ).order_by(KnowledgeBase.usage_count.desc())
        )
        
        for entry in l3_result.scalars().all():
            progress = min(100, (entry.usage_count / self.l3_to_l2_threshold) * 100)
            feedback_ok = entry.avg_feedback_score >= self.min_feedback_score
            
            candidates["L3_to_L2"].append({
                "id": entry.id,
                "title": entry.title,
                "usage_count": entry.usage_count,
                "threshold": self.l3_to_l2_threshold,
                "progress_percent": round(progress, 1),
                "avg_feedback": entry.avg_feedback_score,
                "feedback_qualified": feedback_ok
            })
        
        # L2 entries approaching promotion
        l2_result = await session.execute(
            select(KnowledgeBase).where(
                and_(
                    KnowledgeBase.tier == KnowledgeTier.L2,
                    KnowledgeBase.is_active == True,
                    KnowledgeBase.usage_count >= self.l2_to_l1_threshold * 0.7
                )
            ).order_by(KnowledgeBase.usage_count.desc())
        )
        
        for entry in l2_result.scalars().all():
            progress = min(100, (entry.usage_count / self.l2_to_l1_threshold) * 100)
            feedback_ok = entry.avg_feedback_score >= self.min_feedback_score
            
            candidates["L2_to_L1"].append({
                "id": entry.id,
                "title": entry.title,
                "usage_count": entry.usage_count,
                "threshold": self.l2_to_l1_threshold,
                "progress_percent": round(progress, 1),
                "avg_feedback": entry.avg_feedback_score,
                "feedback_qualified": feedback_ok
            })
        
        return candidates


# Global instance
auto_promotion_service = AutoPromotionService()
