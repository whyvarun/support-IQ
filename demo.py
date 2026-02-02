#!/usr/bin/env python
"""
SupportIQ Demo Script
Demonstrates all core features of the IT Support Automation system.
"""

import asyncio
import sys
from datetime import datetime


def print_header(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def print_result(label: str, value):
    """Print formatted result."""
    print(f"  {label}: {value}")


async def demo_semantic_search():
    """Demonstrate MiniLM semantic search capabilities."""
    print_header("🔍 Semantic Search with MiniLM")
    
    from app.services.semantic_search import semantic_search_service
    
    # Test queries
    queries = [
        "I can't reset my password",
        "Email not syncing in Outlook",
        "VPN connection keeps dropping"
    ]
    
    print("Generating embeddings for test queries...\n")
    
    for query in queries:
        embedding = semantic_search_service.encode(query)
        print(f"  Query: \"{query}\"")
        print(f"  Embedding shape: {embedding.shape}")
        print(f"  First 5 values: {embedding[:5].round(4)}")
        print()
    
    # Test similarity
    print("Testing semantic similarity...")
    emb1 = semantic_search_service.encode("Cannot access my email account")
    emb2 = semantic_search_service.encode("Email login not working")
    emb3 = semantic_search_service.encode("How to cook pasta")
    
    sim_similar = semantic_search_service.similarity(emb1, emb2)
    sim_different = semantic_search_service.similarity(emb1, emb3)
    
    print(f"\n  'Email access' vs 'Email login': {sim_similar:.4f} (similar topics)")
    print(f"  'Email access' vs 'Cooking pasta': {sim_different:.4f} (different topics)")


async def demo_sentiment_analysis():
    """Demonstrate BERT sentiment analysis."""
    print_header("🎭 BERT Sentiment Analysis")
    
    from app.services.sentiment import sentiment_analyzer
    
    test_texts = [
        ("Frustrated user", "This is absolutely terrible! Nothing works and I've been waiting for hours!"),
        ("Neutral query", "I need to reset my password for the employee portal."),
        ("Happy user", "Thank you so much! The solution worked perfectly, I really appreciate the quick help!"),
        ("Urgent request", "URGENT: Payment system is down and customers can't checkout!")
    ]
    
    for label, text in test_texts:
        result = sentiment_analyzer.analyze(text)
        
        print(f"  [{label}]")
        print(f"  Text: \"{text[:60]}...\"" if len(text) > 60 else f"  Text: \"{text}\"")
        print(f"  Sentiment: {result['label']} (score: {result['score']:.2f})")
        print(f"  Confidence: {result['confidence']:.2%}")
        print()


async def demo_urgency_scoring():
    """Demonstrate dynamic urgency scoring."""
    print_header("⚡ Dynamic Urgency Scoring (1-10)")
    
    from app.services.urgency import urgency_calculator
    
    test_cases = [
        {
            "title": "Feature suggestion",
            "description": "It would be nice to have dark mode in the application."
        },
        {
            "title": "Outlook not syncing",
            "description": "My Outlook hasn't synced for a few hours. Can you help?"
        },
        {
            "title": "Cannot login to system",
            "description": "I'm locked out of my account and can't access any systems. This is urgent as I have a deadline!"
        },
        {
            "title": "CRITICAL: Payment processing failure",
            "description": "All payment transactions are failing! Customers cannot complete purchases. Major revenue impact!"
        },
        {
            "title": "Security breach suspected",
            "description": "We detected unusual login attempts from unknown IPs. Possible security incident in progress."
        }
    ]
    
    for case in test_cases:
        result = urgency_calculator.calculate(
            title=case["title"],
            description=case["description"]
        )
        
        # Create urgency bar visualization
        bar = "█" * result.score + "░" * (10 - result.score)
        
        print(f"  Title: {case['title']}")
        print(f"  Urgency: [{bar}] {result.score}/10")
        print(f"  Level: {result.level.value.upper()}")
        print(f"  Tier: {result.tier.value}")
        print(f"  Factors: {result.factors}")
        print()


async def demo_tiered_knowledge():
    """Demonstrate tiered knowledge base structure."""
    print_header("📚 Tiered Knowledge Base (L1/L2/L3)")
    
    from app.models.ticket import KnowledgeTier
    
    tier_info = {
        "L1": {
            "name": "FAQ / Common Issues",
            "description": "Self-service solutions for common problems",
            "examples": ["Password reset", "Email setup", "VPN installation"]
        },
        "L2": {
            "name": "Technical Guides",
            "description": "Moderate complexity requiring technical knowledge",
            "examples": ["Active Directory issues", "Network drive mapping", "SSL certificates"]
        },
        "L3": {
            "name": "Expert Solutions",
            "description": "Complex issues requiring specialist intervention",
            "examples": ["Kerberos authentication", "Payment processing", "Security incidents"]
        }
    }
    
    for tier, info in tier_info.items():
        print(f"  🏷️  {tier}: {info['name']}")
        print(f"      {info['description']}")
        print(f"      Examples: {', '.join(info['examples'])}")
        print()


async def demo_auto_promotion():
    """Demonstrate auto-promotion logic."""
    print_header("🔄 Auto-Promotion Engine")
    
    from app.config import get_settings
    settings = get_settings()
    
    print("  Auto-Promotion Rules:")
    print()
    print(f"  📈 L3 → L2 Promotion:")
    print(f"     • Usage count ≥ {settings.l3_to_l2_threshold}")
    print(f"     • Average feedback ≥ {settings.min_feedback_score}/5")
    print()
    print(f"  📈 L2 → L1 Promotion:")
    print(f"     • Usage count ≥ {settings.l2_to_l1_threshold}")
    print(f"     • Average feedback ≥ {settings.min_feedback_score}/5")
    print()
    print("  Benefits:")
    print("    • Frequently resolved L3 issues become available at L2")
    print("    • Common L2 solutions get promoted to L1 self-service")
    print("    • Knowledge base continuously improves")


async def demo_workflow():
    """Demonstrate complete ticket workflow."""
    print_header("🎫 Complete Ticket Workflow Demo")
    
    from app.services.sentiment import sentiment_analyzer
    from app.services.urgency import urgency_calculator
    from app.services.semantic_search import semantic_search_service
    
    # Simulated ticket
    ticket = {
        "title": "Email synchronization stopped working",
        "description": "Since yesterday morning, my Outlook email has stopped syncing. I've tried restarting but nothing works. I have important client emails that I need to access urgently."
    }
    
    print("  📝 New Ticket Submitted:")
    print(f"     Title: {ticket['title']}")
    print(f"     Description: {ticket['description'][:80]}...")
    print()
    
    # Step 1: Sentiment Analysis
    print("  Step 1: BERT Sentiment Analysis")
    sentiment = sentiment_analyzer.analyze(f"{ticket['title']} {ticket['description']}")
    print(f"     → Sentiment: {sentiment['label']} (score: {sentiment['score']:.2f})")
    print()
    
    # Step 2: Urgency Scoring
    print("  Step 2: Dynamic Urgency Calculation")
    urgency = urgency_calculator.calculate(ticket['title'], ticket['description'])
    bar = "█" * urgency.score + "░" * (10 - urgency.score)
    print(f"     → Urgency: [{bar}] {urgency.score}/10 ({urgency.level.value})")
    print(f"     → Assigned Tier: {urgency.tier.value}")
    print()
    
    # Step 3: Semantic Search
    print("  Step 3: MiniLM Semantic Search")
    embedding = semantic_search_service.encode(f"{ticket['title']} {ticket['description']}")
    print(f"     → Generated 384-dim embedding for hybrid search")
    print(f"     → Would search {urgency.tier.value} knowledge base first")
    print(f"     → Cascade to higher tiers if needed")
    print()
    
    # Step 4: Resolution
    print("  Step 4: Resolution & Feedback")
    print("     → Solution suggested from knowledge base")
    print("     → User feedback collected (1-5 rating)")
    print("     → Usage recorded for auto-promotion")
    print()
    
    print("  ✅ Workflow Complete!")


def main():
    """Run all demos."""
    print("\n" + "🔧" * 30)
    print("\n          SupportIQ - IT Support Automation Demo")
    print("     Tiered RAG | MiniLM Search | BERT Sentiment Analysis")
    print("\n" + "🔧" * 30)
    
    loop = asyncio.get_event_loop()
    
    try:
        # Run demos
        loop.run_until_complete(demo_semantic_search())
        loop.run_until_complete(demo_sentiment_analysis())
        loop.run_until_complete(demo_urgency_scoring())
        loop.run_until_complete(demo_tiered_knowledge())
        loop.run_until_complete(demo_auto_promotion())
        loop.run_until_complete(demo_workflow())
        
        print_header("✨ Demo Complete!")
        print("  To run the full API server:")
        print("  $ python -m uvicorn app.main:app --reload")
        print()
        print("  API Documentation: http://localhost:8000/docs")
        print()
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
