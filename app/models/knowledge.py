"""
Knowledge base SQLAlchemy models.
Includes KnowledgeBase and PromotionHistory tables.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    ForeignKey, DateTime, Enum as SQLEnum, ARRAY
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.database.connection import Base
from app.models.ticket import KnowledgeTier


class KnowledgeBase(Base):
    """Tiered knowledge base for IT support solutions."""
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    tier = Column(
        SQLEnum(KnowledgeTier, name="knowledge_tier", create_type=False),
        nullable=False
    )
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    keywords = Column(ARRAY(Text))
    category = Column(String(100))
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    avg_feedback_score = Column(Float, default=0.0)
    embedding = Column(Vector(384))  # MiniLM-L6 embeddings
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    promotions = relationship("PromotionHistory", back_populates="knowledge", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<KnowledgeBase(id={self.id}, tier={self.tier}, title='{self.title[:30]}...')>"


class PromotionHistory(Base):
    """Tracks automatic promotion of knowledge items between tiers."""
    __tablename__ = "promotion_history"
    
    id = Column(Integer, primary_key=True, index=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge_base.id", ondelete="CASCADE"))
    from_tier = Column(
        SQLEnum(KnowledgeTier, name="knowledge_tier", create_type=False),
        nullable=False
    )
    to_tier = Column(
        SQLEnum(KnowledgeTier, name="knowledge_tier", create_type=False),
        nullable=False
    )
    reason = Column(Text)
    usage_count_at_promotion = Column(Integer)
    avg_feedback_at_promotion = Column(Float)
    promoted_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    knowledge = relationship("KnowledgeBase", back_populates="promotions")
    
    def __repr__(self):
        return f"<PromotionHistory(kb_id={self.knowledge_id}, {self.from_tier} -> {self.to_tier})>"
