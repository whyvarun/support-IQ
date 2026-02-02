"""
Pydantic schemas for API request/response validation.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


# Enums
class TicketStatusEnum(str, Enum):
    """Ticket status options."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class UrgencyLevelEnum(str, Enum):
    """Urgency level options."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class KnowledgeTierEnum(str, Enum):
    """Knowledge tier options."""
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


# Request Schemas
class TicketCreate(BaseModel):
    """Schema for creating a new ticket."""
    title: str = Field(..., min_length=5, max_length=500, description="Ticket title")
    description: str = Field(..., min_length=10, description="Detailed description")
    user_email: Optional[EmailStr] = Field(None, description="User email address")
    category: Optional[str] = Field(None, description="Optional category")
    user_tier: Optional[str] = Field(None, description="User subscription tier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Cannot access email - Outlook not syncing",
                "description": "I have been unable to access my email since this morning. Outlook shows 'disconnected' and won't sync. I've tried restarting but the issue persists. This is urgent as I have important client emails.",
                "user_email": "john.doe@company.com",
                "category": "email"
            }
        }


class TicketResolve(BaseModel):
    """Schema for resolving a ticket."""
    solution: str = Field(..., min_length=10, description="Resolution description")
    resolution_source: Optional[str] = Field(
        None, 
        description="Source of resolution (L1_KB, L2_KB, L3_KB, manual)"
    )
    knowledge_id: Optional[int] = Field(None, description="Knowledge base entry used")
    feedback_score: Optional[int] = Field(
        None, ge=1, le=5, 
        description="User satisfaction (1-5)"
    )
    feedback_comment: Optional[str] = Field(None, description="Optional feedback comment")
    resolved_by: Optional[str] = Field(None, description="Resolver name/email")
    
    class Config:
        json_schema_extra = {
            "example": {
                "solution": "Reset Outlook profile and reconfigured email account. Issue was caused by corrupted cache.",
                "resolution_source": "L2_KB",
                "knowledge_id": 7,
                "feedback_score": 5,
                "resolved_by": "support@company.com"
            }
        }


class SearchQuery(BaseModel):
    """Schema for search requests."""
    query: str = Field(..., min_length=3, description="Search query")
    tier: Optional[KnowledgeTierEnum] = Field(None, description="Filter by tier")
    category: Optional[str] = Field(None, description="Filter by category")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Number of results")
    cascade: Optional[bool] = Field(True, description="Enable cascading search")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "outlook email not syncing disconnected",
                "tier": None,
                "top_k": 5
            }
        }


class KnowledgeCreate(BaseModel):
    """Schema for creating knowledge base entry."""
    tier: KnowledgeTierEnum
    title: str = Field(..., min_length=5, max_length=500)
    content: str = Field(..., min_length=20)
    keywords: Optional[List[str]] = Field(None)
    category: Optional[str] = Field(None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "tier": "L1",
                "title": "How to Clear Browser Cache",
                "content": "To clear browser cache: 1. Open browser settings 2. Navigate to Privacy 3. Click 'Clear browsing data' 4. Select 'Cached images and files' 5. Click Clear",
                "keywords": ["cache", "browser", "clear", "cookies"],
                "category": "software"
            }
        }


class PromoteRequest(BaseModel):
    """Schema for manual promotion request."""
    to_tier: KnowledgeTierEnum
    reason: Optional[str] = Field("Manual promotion", description="Reason for promotion")


# Response Schemas
class UrgencyAnalysis(BaseModel):
    """Urgency analysis result."""
    score: int = Field(..., ge=1, le=10)
    level: UrgencyLevelEnum
    assigned_tier: KnowledgeTierEnum
    factors: Dict[str, float]
    explanation: str


class SentimentAnalysis(BaseModel):
    """Sentiment analysis result."""
    label: str
    score: float
    confidence: float


class TicketResponse(BaseModel):
    """Full ticket response."""
    id: int
    title: str
    description: str
    status: TicketStatusEnum
    urgency_score: Optional[int]
    urgency_level: Optional[UrgencyLevelEnum]
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]
    category: Optional[str]
    assigned_tier: Optional[KnowledgeTierEnum]
    user_email: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    resolved_at: Optional[datetime]


class TicketCreateResponse(BaseModel):
    """Response after creating a ticket."""
    ticket: TicketResponse
    urgency_analysis: UrgencyAnalysis
    sentiment_analysis: SentimentAnalysis
    suggested_solutions: List[Dict[str, Any]]
    message: str


class SearchResult(BaseModel):
    """Single search result."""
    id: int
    tier: str
    title: str
    content: str
    keywords: Optional[List[str]]
    category: Optional[str]
    usage_count: int
    avg_feedback_score: float
    semantic_score: float
    keyword_score: float
    hybrid_score: float


class SearchResponse(BaseModel):
    """Search response with results."""
    results: List[SearchResult]
    searched_tiers: List[str]
    total_found: int
    query: str


class KnowledgeResponse(BaseModel):
    """Knowledge base entry response."""
    id: int
    tier: str
    title: str
    content: str
    keywords: Optional[List[str]]
    category: Optional[str]
    usage_count: int
    avg_feedback_score: float
    success_rate: Optional[float]
    created_at: Optional[str]


class PromotionResponse(BaseModel):
    """Promotion result response."""
    id: int
    title: str
    from_tier: str
    to_tier: str
    reason: Optional[str]
    promoted_at: Optional[str]


class PromotionCandidates(BaseModel):
    """Promotion candidates response."""
    L3_to_L2: List[Dict[str, Any]]
    L2_to_L1: List[Dict[str, Any]]


class AnalyticsResponse(BaseModel):
    """Analytics dashboard response."""
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    avg_resolution_time_minutes: Optional[float]
    urgency_distribution: Dict[str, int]
    tier_distribution: Dict[str, int]
    category_distribution: Dict[str, int]
    avg_feedback_score: Optional[float]
    knowledge_base_stats: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    models_loaded: Dict[str, bool]
    version: str
