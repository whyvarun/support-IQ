"""
Dynamic Urgency Scoring Service.
Calculates urgency scores (1-10) based on sentiment, keywords, and issue type.
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.config import get_settings
from app.services.sentiment import SentimentAnalyzer, sentiment_analyzer
from app.models.ticket import UrgencyLevel, KnowledgeTier

settings = get_settings()


@dataclass
class UrgencyResult:
    """Result of urgency calculation."""
    score: int  # 1-10
    level: UrgencyLevel
    tier: KnowledgeTier
    factors: Dict[str, float]
    explanation: str


class UrgencyCalculator:
    """
    Dynamic urgency scoring based on multiple factors:
    - Sentiment analysis (negative = higher urgency)
    - Critical keywords (payment, security, outage)
    - Issue type classification
    - Business context
    """
    
    # Category to base urgency mapping
    CATEGORY_URGENCY = {
        "payment": 8,
        "security": 9,
        "outage": 10,
        "authentication": 6,
        "email": 4,
        "network": 5,
        "hardware": 3,
        "software": 4,
        "database": 7,
        "performance": 5,
        "general": 3
    }
    
    # Urgency level thresholds
    URGENCY_THRESHOLDS = {
        UrgencyLevel.CRITICAL: 8,  # 8-10
        UrgencyLevel.HIGH: 6,       # 6-7
        UrgencyLevel.MEDIUM: 4,     # 4-5
        UrgencyLevel.LOW: 1         # 1-3
    }
    
    # Tier assignment based on urgency
    TIER_THRESHOLDS = {
        KnowledgeTier.L3: 8,  # Critical issues go to L3
        KnowledgeTier.L2: 5,  # Medium-high go to L2
        KnowledgeTier.L1: 1   # Low issues start at L1
    }
    
    def __init__(self, sentiment_service: SentimentAnalyzer = None):
        """Initialize with sentiment analyzer."""
        self._sentiment = sentiment_service or sentiment_analyzer
        self._critical_keywords = settings.critical_keywords_list
        self._high_keywords = settings.high_urgency_keywords_list
    
    def calculate(
        self,
        title: str,
        description: str,
        category: Optional[str] = None,
        user_tier: Optional[str] = None
    ) -> UrgencyResult:
        """
        Calculate dynamic urgency score for a ticket.
        
        Args:
            title: Ticket title
            description: Ticket description
            category: Optional category classification
            user_tier: Optional user subscription tier (premium, standard, basic)
            
        Returns:
            UrgencyResult with score, level, tier, factors, and explanation
        """
        combined_text = f"{title} {description}".lower()
        factors = {}
        
        # 1. Sentiment Analysis Factor (0-3 points)
        sentiment_result = self._sentiment.analyze(combined_text)
        sentiment_score = sentiment_result["score"]  # -1 to 1
        
        # Invert and scale: very negative (-1) -> 3 points, positive (1) -> 0 points
        sentiment_factor = max(0, (1 - sentiment_score) * 1.5)  # 0-3 range
        factors["sentiment"] = round(sentiment_factor, 2)
        
        # 2. Critical Keywords Factor (0-4 points)
        keyword_factor = 0.0
        matched_keywords = []
        
        for keyword in self._critical_keywords:
            if keyword in combined_text:
                keyword_factor = 4.0  # Critical keyword found
                matched_keywords.append(keyword)
                break
        
        if keyword_factor == 0:
            for keyword in self._high_keywords:
                if keyword in combined_text:
                    keyword_factor = 2.5  # High urgency keyword
                    matched_keywords.append(keyword)
                    break
        
        factors["keywords"] = keyword_factor
        
        # 3. Category Factor (0-2 points)
        detected_category = category or self._detect_category(combined_text)
        category_base = self.CATEGORY_URGENCY.get(detected_category, 3)
        category_factor = (category_base / 10) * 2  # Scale to 0-2
        factors["category"] = round(category_factor, 2)
        
        # 4. User Tier Factor (0-1 points)
        user_factor = 0.0
        if user_tier == "premium":
            user_factor = 1.0
        elif user_tier == "standard":
            user_factor = 0.5
        factors["user_tier"] = user_factor
        
        # 5. Text Indicators Factor (0-1 points)
        indicator_factor = 0.0
        urgent_patterns = [
            r'\b(asap|immediately|urgent|emergency)\b',
            r'\b(not working|broken|down|failed)\b',
            r'\b(cannot|can\'t|unable to)\s+(access|login|connect)',
            r'\b(blocked|stuck|frozen)\b',
            r'!!!+|\?\?\?+',  # Multiple punctuation
        ]
        
        for pattern in urgent_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                indicator_factor += 0.25
        
        indicator_factor = min(indicator_factor, 1.0)
        factors["text_indicators"] = round(indicator_factor, 2)
        
        # Calculate total score (1-10)
        raw_score = sum(factors.values())
        final_score = max(1, min(10, round(raw_score)))
        
        # Determine urgency level
        urgency_level = self._get_urgency_level(final_score)
        
        # Determine initial tier assignment
        assigned_tier = self._get_tier_assignment(final_score)
        
        # Build explanation
        explanation = self._build_explanation(
            final_score, urgency_level, factors, matched_keywords, detected_category
        )
        
        return UrgencyResult(
            score=final_score,
            level=urgency_level,
            tier=assigned_tier,
            factors=factors,
            explanation=explanation
        )
    
    def _detect_category(self, text: str) -> str:
        """Detect ticket category from text content."""
        category_keywords = {
            "payment": ["payment", "billing", "invoice", "charge", "refund", "transaction"],
            "security": ["security", "breach", "hack", "virus", "malware", "phishing", "vulnerability"],
            "outage": ["outage", "down", "offline", "unavailable", "503", "500 error"],
            "authentication": ["login", "password", "auth", "sso", "mfa", "2fa", "locked out"],
            "email": ["email", "outlook", "inbox", "smtp", "mail"],
            "network": ["vpn", "network", "wifi", "internet", "connection", "dns"],
            "hardware": ["printer", "laptop", "monitor", "keyboard", "mouse", "hardware"],
            "database": ["database", "sql", "query", "replication", "backup"],
            "performance": ["slow", "performance", "lag", "timeout", "memory"],
        }
        
        text_lower = text.lower()
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return category
        
        return "general"
    
    def _get_urgency_level(self, score: int) -> UrgencyLevel:
        """Map score to urgency level."""
        if score >= self.URGENCY_THRESHOLDS[UrgencyLevel.CRITICAL]:
            return UrgencyLevel.CRITICAL
        elif score >= self.URGENCY_THRESHOLDS[UrgencyLevel.HIGH]:
            return UrgencyLevel.HIGH
        elif score >= self.URGENCY_THRESHOLDS[UrgencyLevel.MEDIUM]:
            return UrgencyLevel.MEDIUM
        else:
            return UrgencyLevel.LOW
    
    def _get_tier_assignment(self, score: int) -> KnowledgeTier:
        """Assign initial tier based on urgency score."""
        if score >= self.TIER_THRESHOLDS[KnowledgeTier.L3]:
            return KnowledgeTier.L3
        elif score >= self.TIER_THRESHOLDS[KnowledgeTier.L2]:
            return KnowledgeTier.L2
        else:
            return KnowledgeTier.L1
    
    def _build_explanation(
        self,
        score: int,
        level: UrgencyLevel,
        factors: Dict[str, float],
        keywords: List[str],
        category: str
    ) -> str:
        """Build human-readable explanation of urgency calculation."""
        parts = [f"Urgency Score: {score}/10 ({level.value.upper()})"]
        
        if keywords:
            parts.append(f"Critical keywords detected: {', '.join(keywords)}")
        
        if factors["sentiment"] > 1.5:
            parts.append("Negative sentiment detected in message")
        
        if category != "general":
            parts.append(f"Category: {category}")
        
        if factors["text_indicators"] > 0:
            parts.append("Urgent language patterns detected")
        
        return " | ".join(parts)


# Global instance
urgency_calculator = UrgencyCalculator()
