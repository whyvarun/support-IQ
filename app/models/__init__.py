"""Models package initialization."""

from app.models.ticket import Ticket, TicketEmbedding, Resolution
from app.models.knowledge import KnowledgeBase, PromotionHistory

__all__ = [
    "Ticket",
    "TicketEmbedding", 
    "Resolution",
    "KnowledgeBase",
    "PromotionHistory"
]
