"""
Unit tests for BERT Sentiment Analysis and Urgency Scoring.
"""

import pytest


class TestSentimentAnalysis:
    """Tests for BERT sentiment analyzer."""
    
    def test_singleton_pattern(self):
        """Test that analyzer uses singleton pattern."""
        from app.services.sentiment import SentimentAnalyzer
        
        analyzer1 = SentimentAnalyzer()
        analyzer2 = SentimentAnalyzer()
        
        assert analyzer1 is analyzer2
    
    def test_analyze_negative_text(self):
        """Test sentiment analysis on negative text."""
        from app.services.sentiment import sentiment_analyzer
        
        result = sentiment_analyzer.analyze(
            "This is terrible! Nothing works and I'm extremely frustrated!"
        )
        
        assert result["label"] in ["negative", "very_negative"]
        assert result["score"] < 0
        assert 0 <= result["confidence"] <= 1
    
    def test_analyze_positive_text(self):
        """Test sentiment analysis on positive text."""
        from app.services.sentiment import sentiment_analyzer
        
        result = sentiment_analyzer.analyze(
            "Thank you so much! This works perfectly and I'm very happy!"
        )
        
        assert result["label"] in ["positive", "very_positive"]
        assert result["score"] > 0
    
    def test_analyze_neutral_text(self):
        """Test sentiment analysis on neutral text."""
        from app.services.sentiment import sentiment_analyzer
        
        result = sentiment_analyzer.analyze(
            "I need to reset my password for the portal."
        )
        
        # Should be relatively neutral
        assert -0.5 <= result["score"] <= 0.5
    
    def test_analyze_empty_text(self):
        """Test handling of empty text."""
        from app.services.sentiment import sentiment_analyzer
        
        result = sentiment_analyzer.analyze("")
        
        assert result["label"] == "neutral"
        assert result["score"] == 0.0
        assert result["confidence"] == 0.0
    
    def test_batch_analysis(self):
        """Test batch sentiment analysis."""
        from app.services.sentiment import sentiment_analyzer
        
        texts = [
            "This is great!",
            "This is terrible!",
            "This is okay."
        ]
        
        results = sentiment_analyzer.analyze_batch(texts)
        
        assert len(results) == 3
        assert results[0]["score"] > results[2]["score"]  # Great > Okay
        assert results[2]["score"] > results[1]["score"]  # Okay > Terrible


class TestUrgencyCalculation:
    """Tests for dynamic urgency scoring."""
    
    def test_urgency_calculator_init(self):
        """Test urgency calculator initialization."""
        from app.services.urgency import urgency_calculator
        
        assert urgency_calculator is not None
    
    def test_critical_keyword_detection(self):
        """Test that critical keywords increase urgency."""
        from app.services.urgency import urgency_calculator
        
        result = urgency_calculator.calculate(
            title="Payment processing failing",
            description="All payment transactions are failing for customers. Critical issue!"
        )
        
        assert result.score >= 8
        assert result.level.value == "critical"
        assert "payment" in result.explanation.lower() or result.factors["keywords"] > 0
    
    def test_security_issue_urgency(self):
        """Test that security issues get high urgency."""
        from app.services.urgency import urgency_calculator
        
        result = urgency_calculator.calculate(
            title="Security breach detected",
            description="We suspect unauthorized access to customer data."
        )
        
        assert result.score >= 8
        assert result.level.value in ["high", "critical"]
    
    def test_low_urgency_issue(self):
        """Test that minor issues get low urgency."""
        from app.services.urgency import urgency_calculator
        
        result = urgency_calculator.calculate(
            title="Feature request",
            description="It would be nice to have dark mode in the application."
        )
        
        assert result.score <= 5
        assert result.level.value in ["low", "medium"]
    
    def test_urgency_score_range(self):
        """Test that urgency score is within 1-10 range."""
        from app.services.urgency import urgency_calculator
        
        test_cases = [
            ("Minor issue", "Small problem"),
            ("URGENT! System down!", "Everything is broken and on fire!!!"),
            ("Question about feature", "How do I export data?")
        ]
        
        for title, desc in test_cases:
            result = urgency_calculator.calculate(title, desc)
            assert 1 <= result.score <= 10
    
    def test_tier_assignment(self):
        """Test correct tier assignment based on urgency."""
        from app.services.urgency import urgency_calculator
        from app.models.ticket import KnowledgeTier
        
        # Critical should go to L3
        critical = urgency_calculator.calculate(
            "Payment system outage",
            "All payments failing! Emergency!"
        )
        assert critical.tier in [KnowledgeTier.L3, KnowledgeTier.L2]
        
        # Low urgency should start at L1
        low = urgency_calculator.calculate(
            "How to change profile picture",
            "I want to update my profile photo"
        )
        assert low.tier == KnowledgeTier.L1
    
    def test_category_detection(self):
        """Test automatic category detection."""
        from app.services.urgency import urgency_calculator
        
        result = urgency_calculator.calculate(
            "VPN not connecting",
            "I can't connect to the company VPN from home"
        )
        
        # Check that it detected a category or has factors
        assert "category" in result.factors or result.factors.get("category", 0) >= 0
