"""
Ticket-related SQLAlchemy models.
Includes Ticket, TicketEmbedding, and Resolution tables.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    ForeignKey, DateTime, Enum as SQLEnum, ARRAY
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import enum

from app.database.connection import Base


class TicketStatus(str, enum.Enum):
    """Ticket status enumeration."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class UrgencyLevel(str, enum.Enum):
    """Urgency level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class KnowledgeTier(str, enum.Enum):
    """Knowledge base tier enumeration."""
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class Ticket(Base):
    """Support ticket model."""
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(
        SQLEnum(TicketStatus, name="ticket_status", create_type=False),
        default=TicketStatus.OPEN
    )
    urgency_score = Column(Integer)  # 1-10 dynamic score
    urgency_level = Column(
        SQLEnum(UrgencyLevel, name="urgency_level", create_type=False),
        default=UrgencyLevel.MEDIUM
    )
    sentiment_score = Column(Float)  # -1.0 to 1.0
    sentiment_label = Column(String(50))  # very_negative, negative, neutral, positive, very_positive
    category = Column(String(100))
    assigned_tier = Column(
        SQLEnum(KnowledgeTier, name="knowledge_tier", create_type=False),
        default=KnowledgeTier.L1
    )
    user_email = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    embedding = relationship("TicketEmbedding", back_populates="ticket", uselist=False, cascade="all, delete-orphan")
    resolutions = relationship("Resolution", back_populates="ticket", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Ticket(id={self.id}, title='{self.title[:30]}...', status={self.status})>"


class TicketEmbedding(Base):
    """Vector embedding for ticket semantic search."""
    __tablename__ = "ticket_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), unique=True)
    embedding = Column(Vector(384))  # MiniLM-L6 produces 384-dim embeddings
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    ticket = relationship("Ticket", back_populates="embedding")
    
    def __repr__(self):
        return f"<TicketEmbedding(ticket_id={self.ticket_id})>"


class Resolution(Base):
    """Resolution and feedback for tickets."""
    __tablename__ = "resolutions"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"))
    solution = Column(Text, nullable=False)
    resolution_source = Column(String(100))  # 'L1_KB', 'L2_KB', 'L3_KB', 'manual'
    resolution_time_minutes = Column(Integer)
    feedback_score = Column(Integer)  # 1-5 rating
    feedback_comment = Column(Text)
    resolved_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    ticket = relationship("Ticket", back_populates="resolutions")
    
    def __repr__(self):
        return f"<Resolution(id={self.id}, ticket_id={self.ticket_id}, score={self.feedback_score})>"
