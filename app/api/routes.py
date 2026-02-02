"""
FastAPI REST API routes for SupportIQ.
Provides endpoints for ticket management, search, and analytics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, update
from typing import List, Optional
from datetime import datetime

from app.database.connection import get_async_session
from app.models.ticket import Ticket, TicketEmbedding, Resolution, TicketStatus, KnowledgeTier, UrgencyLevel
from app.models.knowledge import KnowledgeBase
from app.services import (
    SemanticSearchService, semantic_search_service,
    SentimentAnalyzer, sentiment_analyzer,
    UrgencyCalculator, urgency_calculator,
    KnowledgeBaseService, knowledge_base_service,
    AutoPromotionService, auto_promotion_service
)
from app.api.schemas import (
    TicketCreate, TicketResolve, SearchQuery, KnowledgeCreate, PromoteRequest,
    TicketResponse, TicketCreateResponse, SearchResponse, SearchResult,
    KnowledgeResponse, PromotionResponse, PromotionCandidates, AnalyticsResponse,
    HealthResponse, UrgencyAnalysis, SentimentAnalysis
)
from app import __version__

router = APIRouter()


# ============== Health Check ==============

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check system health and model status."""
    return HealthResponse(
        status="healthy",
        database="connected",
        models_loaded={
            "minilm_semantic": semantic_search_service._initialized,
            "bert_sentiment": sentiment_analyzer._initialized
        },
        version=__version__
    )


# ============== Ticket Endpoints ==============

@router.post("/tickets", response_model=TicketCreateResponse, tags=["Tickets"])
async def create_ticket(
    ticket_data: TicketCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Create a new support ticket with automatic analysis.
    
    Performs:
    - BERT sentiment analysis
    - Dynamic urgency scoring (1-10)
    - Tier assignment based on urgency
    - Semantic search for suggested solutions
    """
    # Combine title and description for analysis
    combined_text = f"{ticket_data.title} {ticket_data.description}"
    
    # Sentiment Analysis
    sentiment_result = sentiment_analyzer.analyze(combined_text)
    
    # Urgency Calculation
    urgency_result = urgency_calculator.calculate(
        title=ticket_data.title,
        description=ticket_data.description,
        category=ticket_data.category,
        user_tier=ticket_data.user_tier
    )
    
    # Create ticket record
    ticket = Ticket(
        title=ticket_data.title,
        description=ticket_data.description,
        user_email=ticket_data.user_email,
        category=ticket_data.category or urgency_result.factors.get("detected_category"),
        urgency_score=urgency_result.score,
        urgency_level=urgency_result.level,
        sentiment_score=sentiment_result["score"],
        sentiment_label=sentiment_result["label"],
        assigned_tier=urgency_result.tier,
        status=TicketStatus.OPEN
    )
    
    session.add(ticket)
    await session.flush()
    
    # Generate and store embedding
    embedding = semantic_search_service.encode(combined_text)
    ticket_embedding = TicketEmbedding(
        ticket_id=ticket.id,
        embedding=embedding.tolist()
    )
    session.add(ticket_embedding)
    
    # Search for suggested solutions
    search_results = await knowledge_base_service.search_tiered(
        session=session,
        query=combined_text,
        start_tier=urgency_result.tier,
        cascade=True
    )
    
    await session.commit()
    await session.refresh(ticket)
    
    return TicketCreateResponse(
        ticket=TicketResponse(
            id=ticket.id,
            title=ticket.title,
            description=ticket.description,
            status=ticket.status,
            urgency_score=ticket.urgency_score,
            urgency_level=ticket.urgency_level,
            sentiment_score=ticket.sentiment_score,
            sentiment_label=ticket.sentiment_label,
            category=ticket.category,
            assigned_tier=ticket.assigned_tier,
            user_email=ticket.user_email,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            resolved_at=ticket.resolved_at
        ),
        urgency_analysis=UrgencyAnalysis(
            score=urgency_result.score,
            level=urgency_result.level,
            assigned_tier=urgency_result.tier,
            factors=urgency_result.factors,
            explanation=urgency_result.explanation
        ),
        sentiment_analysis=SentimentAnalysis(
            label=sentiment_result["label"],
            score=sentiment_result["score"],
            confidence=sentiment_result["confidence"]
        ),
        suggested_solutions=search_results["results"][:5],
        message=f"Ticket created with urgency score {urgency_result.score}/10 ({urgency_result.level.value})"
    )


@router.get("/tickets/{ticket_id}", response_model=TicketResponse, tags=["Tickets"])
async def get_ticket(
    ticket_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """Get ticket details by ID."""
    result = await session.execute(
        select(Ticket).where(Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return TicketResponse(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        urgency_score=ticket.urgency_score,
        urgency_level=ticket.urgency_level,
        sentiment_score=ticket.sentiment_score,
        sentiment_label=ticket.sentiment_label,
        category=ticket.category,
        assigned_tier=ticket.assigned_tier,
        user_email=ticket.user_email,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at
    )


@router.get("/tickets", tags=["Tickets"])
async def list_tickets(
    status: Optional[str] = Query(None, description="Filter by status"),
    urgency_level: Optional[str] = Query(None, description="Filter by urgency"),
    tier: Optional[str] = Query(None, description="Filter by assigned tier"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session)
):
    """List tickets with optional filters."""
    query = select(Ticket)
    
    if status:
        query = query.where(Ticket.status == status)
    if urgency_level:
        query = query.where(Ticket.urgency_level == urgency_level)
    if tier:
        query = query.where(Ticket.assigned_tier == tier)
    
    query = query.order_by(Ticket.urgency_score.desc(), Ticket.created_at.desc())
    query = query.limit(limit).offset(offset)
    
    result = await session.execute(query)
    tickets = result.scalars().all()
    
    return {
        "tickets": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status.value if t.status else None,
                "urgency_score": t.urgency_score,
                "urgency_level": t.urgency_level.value if t.urgency_level else None,
                "assigned_tier": t.assigned_tier.value if t.assigned_tier else None,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in tickets
        ],
        "count": len(tickets)
    }


@router.post("/tickets/{ticket_id}/resolve", tags=["Tickets"])
async def resolve_ticket(
    ticket_id: int,
    resolution: TicketResolve,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Mark a ticket as resolved and record resolution details.
    Also triggers knowledge base usage tracking and auto-promotion check.
    """
    result = await session.execute(
        select(Ticket).where(Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Calculate resolution time
    resolution_time = None
    if ticket.created_at:
        delta = datetime.now(ticket.created_at.tzinfo) - ticket.created_at
        resolution_time = int(delta.total_seconds() / 60)
    
    # Create resolution record
    res = Resolution(
        ticket_id=ticket_id,
        solution=resolution.solution,
        resolution_source=resolution.resolution_source,
        resolution_time_minutes=resolution_time,
        feedback_score=resolution.feedback_score,
        feedback_comment=resolution.feedback_comment,
        resolved_by=resolution.resolved_by
    )
    session.add(res)
    
    # Update ticket status
    await session.execute(
        update(Ticket)
        .where(Ticket.id == ticket_id)
        .values(
            status=TicketStatus.RESOLVED,
            resolved_at=datetime.utcnow()
        )
    )
    
    # Record knowledge base usage if applicable
    if resolution.knowledge_id:
        await knowledge_base_service.record_usage(
            session=session,
            kb_id=resolution.knowledge_id,
            feedback_score=resolution.feedback_score,
            was_successful=True
        )
    
    await session.commit()
    
    # Check for auto-promotions
    promotions = await auto_promotion_service.check_and_promote(session)
    
    return {
        "message": "Ticket resolved successfully",
        "ticket_id": ticket_id,
        "resolution_time_minutes": resolution_time,
        "auto_promotions": promotions
    }


# ============== Search Endpoints ==============

@router.post("/search", response_model=SearchResponse, tags=["Search"])
async def search_knowledge_base(
    query: SearchQuery,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Semantic search across knowledge base with hybrid scoring.
    Combines MiniLM semantic similarity and keyword matching.
    """
    tier = None
    if query.tier:
        tier = KnowledgeTier(query.tier.value)
    
    if query.cascade:
        results = await knowledge_base_service.search_tiered(
            session=session,
            query=query.query,
            start_tier=tier or KnowledgeTier.L1,
            cascade=True
        )
    else:
        results = await semantic_search_service.hybrid_search(
            session=session,
            query=query.query,
            tier=tier,
            top_k=query.top_k
        )
        results = {
            "results": results,
            "searched_tiers": [tier.value] if tier else ["L1", "L2", "L3"],
            "total_found": len(results),
            "query": query.query
        }
    
    return SearchResponse(
        results=[
            SearchResult(**r) for r in results["results"]
        ],
        searched_tiers=results["searched_tiers"],
        total_found=results["total_found"],
        query=results["query"]
    )


@router.get("/search/similar/{ticket_id}", tags=["Search"])
async def find_similar_tickets(
    ticket_id: int,
    limit: int = Query(5, ge=1, le=20),
    session: AsyncSession = Depends(get_async_session)
):
    """Find similar past tickets based on embedding similarity."""
    # Get ticket embedding
    result = await session.execute(
        select(TicketEmbedding).where(TicketEmbedding.ticket_id == ticket_id)
    )
    embedding_record = result.scalar_one_or_none()
    
    if not embedding_record:
        raise HTTPException(status_code=404, detail="Ticket embedding not found")
    
    import numpy as np
    query_embedding = np.array(embedding_record.embedding)
    
    similar = await semantic_search_service.find_similar_tickets(
        session=session,
        query_embedding=query_embedding,
        limit=limit
    )
    
    return {"similar_tickets": similar}


# ============== Knowledge Base Endpoints ==============

@router.get("/knowledge", tags=["Knowledge Base"])
async def list_knowledge_base(
    tier: Optional[str] = Query(None, description="Filter by tier (L1/L2/L3)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session)
):
    """List knowledge base entries."""
    tier_enum = KnowledgeTier(tier) if tier else None
    
    if tier_enum:
        results = await knowledge_base_service.get_by_tier(
            session=session,
            tier=tier_enum,
            category=category,
            limit=limit
        )
    else:
        # Get all tiers
        results = []
        for t in [KnowledgeTier.L1, KnowledgeTier.L2, KnowledgeTier.L3]:
            tier_results = await knowledge_base_service.get_by_tier(
                session=session,
                tier=t,
                category=category,
                limit=limit // 3
            )
            results.extend(tier_results)
    
    return {"knowledge_base": results, "count": len(results)}


@router.get("/knowledge/{kb_id}", response_model=KnowledgeResponse, tags=["Knowledge Base"])
async def get_knowledge_entry(
    kb_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """Get a specific knowledge base entry."""
    result = await knowledge_base_service.get_by_id(session, kb_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Knowledge base entry not found")
    
    return KnowledgeResponse(**result)


@router.post("/knowledge", tags=["Knowledge Base"])
async def create_knowledge_entry(
    entry: KnowledgeCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new knowledge base entry with auto-generated embedding."""
    tier = KnowledgeTier(entry.tier.value)
    
    result = await knowledge_base_service.create_entry(
        session=session,
        tier=tier,
        title=entry.title,
        content=entry.content,
        keywords=entry.keywords,
        category=entry.category
    )
    
    await session.commit()
    return result


@router.get("/knowledge/categories", tags=["Knowledge Base"])
async def get_categories(
    tier: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_async_session)
):
    """Get list of categories with entry counts."""
    tier_enum = KnowledgeTier(tier) if tier else None
    categories = await knowledge_base_service.get_categories(session, tier_enum)
    return {"categories": categories}


# ============== Auto-Promotion Endpoints ==============

@router.get("/promotions/candidates", response_model=PromotionCandidates, tags=["Auto-Promotion"])
async def get_promotion_candidates(
    session: AsyncSession = Depends(get_async_session)
):
    """Get knowledge base entries approaching promotion thresholds."""
    candidates = await auto_promotion_service.get_promotion_candidates(session)
    return PromotionCandidates(**candidates)


@router.post("/promotions/run", tags=["Auto-Promotion"])
async def run_auto_promotion(
    session: AsyncSession = Depends(get_async_session)
):
    """Manually trigger auto-promotion check."""
    promotions = await auto_promotion_service.check_and_promote(session)
    await session.commit()
    
    return {
        "promotions": promotions,
        "count": len(promotions),
        "message": f"Auto-promotion completed. {len(promotions)} entries promoted."
    }


@router.post("/knowledge/{kb_id}/promote", tags=["Auto-Promotion"])
async def manual_promote(
    kb_id: int,
    request: PromoteRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Manually promote a knowledge base entry to a specific tier."""
    to_tier = KnowledgeTier(request.to_tier.value)
    
    result = await auto_promotion_service.force_promote(
        session=session,
        kb_id=kb_id,
        to_tier=to_tier,
        reason=request.reason
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Knowledge base entry not found")
    
    await session.commit()
    return PromotionResponse(**result)


@router.get("/promotions/history", tags=["Auto-Promotion"])
async def get_promotion_history(
    kb_id: Optional[int] = Query(None, description="Filter by knowledge base ID"),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session)
):
    """Get promotion history records."""
    history = await auto_promotion_service.get_promotion_history(
        session=session,
        kb_id=kb_id,
        limit=limit
    )
    return {"history": history, "count": len(history)}


# ============== Analytics Endpoints ==============

@router.get("/analytics", response_model=AnalyticsResponse, tags=["Analytics"])
async def get_analytics(
    session: AsyncSession = Depends(get_async_session)
):
    """Get dashboard analytics for tickets and knowledge base."""
    
    # Ticket statistics
    total_result = await session.execute(select(func.count(Ticket.id)))
    total_tickets = total_result.scalar() or 0
    
    open_result = await session.execute(
        select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.OPEN)
    )
    open_tickets = open_result.scalar() or 0
    
    resolved_result = await session.execute(
        select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.RESOLVED)
    )
    resolved_tickets = resolved_result.scalar() or 0
    
    # Average resolution time
    avg_time_result = await session.execute(
        select(func.avg(Resolution.resolution_time_minutes))
    )
    avg_resolution_time = avg_time_result.scalar()
    
    # Urgency distribution
    urgency_query = await session.execute(
        select(Ticket.urgency_level, func.count(Ticket.id))
        .group_by(Ticket.urgency_level)
    )
    urgency_dist = {
        row[0].value if row[0] else "unknown": row[1] 
        for row in urgency_query.fetchall()
    }
    
    # Tier distribution
    tier_query = await session.execute(
        select(Ticket.assigned_tier, func.count(Ticket.id))
        .group_by(Ticket.assigned_tier)
    )
    tier_dist = {
        row[0].value if row[0] else "unknown": row[1] 
        for row in tier_query.fetchall()
    }
    
    # Category distribution
    category_query = await session.execute(
        select(Ticket.category, func.count(Ticket.id))
        .where(Ticket.category.isnot(None))
        .group_by(Ticket.category)
    )
    category_dist = {row[0]: row[1] for row in category_query.fetchall()}
    
    # Average feedback score
    avg_feedback_result = await session.execute(
        select(func.avg(Resolution.feedback_score))
        .where(Resolution.feedback_score.isnot(None))
    )
    avg_feedback = avg_feedback_result.scalar()
    
    # Knowledge base statistics
    kb_stats_query = await session.execute(
        select(
            KnowledgeBase.tier,
            func.count(KnowledgeBase.id),
            func.avg(KnowledgeBase.usage_count),
            func.avg(KnowledgeBase.avg_feedback_score)
        )
        .where(KnowledgeBase.is_active == True)
        .group_by(KnowledgeBase.tier)
    )
    
    kb_stats = {}
    for row in kb_stats_query.fetchall():
        tier_name = row[0].value if row[0] else "unknown"
        kb_stats[tier_name] = {
            "count": row[1],
            "avg_usage": float(row[2]) if row[2] else 0,
            "avg_feedback": float(row[3]) if row[3] else 0
        }
    
    return AnalyticsResponse(
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        resolved_tickets=resolved_tickets,
        avg_resolution_time_minutes=float(avg_resolution_time) if avg_resolution_time else None,
        urgency_distribution=urgency_dist,
        tier_distribution=tier_dist,
        category_distribution=category_dist,
        avg_feedback_score=float(avg_feedback) if avg_feedback else None,
        knowledge_base_stats=kb_stats
    )


# ============== Utility Endpoints ==============

@router.post("/analyze", tags=["Utilities"])
async def analyze_text(
    title: str = Query(..., description="Text title"),
    description: str = Query(..., description="Text description")
):
    """
    Analyze text for sentiment and urgency without creating a ticket.
    Useful for testing and preview.
    """
    combined_text = f"{title} {description}"
    
    sentiment_result = sentiment_analyzer.analyze(combined_text)
    urgency_result = urgency_calculator.calculate(
        title=title,
        description=description
    )
    
    return {
        "sentiment": {
            "label": sentiment_result["label"],
            "score": sentiment_result["score"],
            "confidence": sentiment_result["confidence"]
        },
        "urgency": {
            "score": urgency_result.score,
            "level": urgency_result.level.value,
            "tier": urgency_result.tier.value,
            "factors": urgency_result.factors,
            "explanation": urgency_result.explanation
        }
    }
