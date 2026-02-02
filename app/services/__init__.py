"""Services package initialization."""

# Use lazy imports to avoid circular dependency issues
# The ML models are heavy and have complex import chains

__all__ = [
    "SemanticSearchService",
    "semantic_search_service",
    "SentimentAnalyzer",
    "sentiment_analyzer",
    "UrgencyCalculator",
    "urgency_calculator",
    "KnowledgeBaseService",
    "knowledge_base_service",
    "AutoPromotionService",
    "auto_promotion_service"
]

# Lazy attribute access
def __getattr__(name):
    if name == "SemanticSearchService":
        from app.services.semantic_search import SemanticSearchService
        return SemanticSearchService
    elif name == "semantic_search_service":
        from app.services.semantic_search import semantic_search_service
        return semantic_search_service
    elif name == "SentimentAnalyzer":
        from app.services.sentiment import SentimentAnalyzer
        return SentimentAnalyzer
    elif name == "sentiment_analyzer":
        from app.services.sentiment import sentiment_analyzer
        return sentiment_analyzer
    elif name == "UrgencyCalculator":
        from app.services.urgency import UrgencyCalculator
        return UrgencyCalculator
    elif name == "urgency_calculator":
        from app.services.urgency import urgency_calculator
        return urgency_calculator
    elif name == "KnowledgeBaseService":
        from app.services.knowledge_base import KnowledgeBaseService
        return KnowledgeBaseService
    elif name == "knowledge_base_service":
        from app.services.knowledge_base import knowledge_base_service
        return knowledge_base_service
    elif name == "AutoPromotionService":
        from app.services.auto_promote import AutoPromotionService
        return AutoPromotionService
    elif name == "auto_promotion_service":
        from app.services.auto_promote import auto_promotion_service
        return auto_promotion_service
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
