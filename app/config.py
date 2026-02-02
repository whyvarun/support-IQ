"""
Configuration management for SupportIQ application.
Uses pydantic-settings for environment variable loading.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://supportiq:supportiq_pass@localhost:5432/supportiq_db",
        alias="DATABASE_URL"
    )
    database_url_sync: str = Field(
        default="postgresql://supportiq:supportiq_pass@localhost:5432/supportiq_db",
        alias="DATABASE_URL_SYNC"
    )
    
    # Application
    app_name: str = Field(default="SupportIQ", alias="APP_NAME")
    debug: bool = Field(default=True, alias="DEBUG")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    
    # ML Models
    minilm_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="MINILM_MODEL"
    )
    bert_sentiment_model: str = Field(
        default="nlptown/bert-base-multilingual-uncased-sentiment",
        alias="BERT_SENTIMENT_MODEL"
    )
    
    # Search Configuration
    semantic_weight: float = Field(default=0.7, alias="SEMANTIC_WEIGHT")
    keyword_weight: float = Field(default=0.3, alias="KEYWORD_WEIGHT")
    top_k_results: int = Field(default=5, alias="TOP_K_RESULTS")
    
    # Auto-Promotion Thresholds
    l3_to_l2_threshold: int = Field(default=10, alias="L3_TO_L2_THRESHOLD")
    l2_to_l1_threshold: int = Field(default=25, alias="L2_TO_L1_THRESHOLD")
    min_feedback_score: float = Field(default=4.0, alias="MIN_FEEDBACK_SCORE")
    
    # Urgency Keywords (comma-separated in env)
    critical_keywords: str = Field(
        default="payment,security,breach,outage,down,emergency,critical",
        alias="CRITICAL_KEYWORDS"
    )
    high_urgency_keywords: str = Field(
        default="error,failed,broken,urgent,asap",
        alias="HIGH_URGENCY_KEYWORDS"
    )
    
    @property
    def critical_keywords_list(self) -> List[str]:
        """Parse critical keywords into list."""
        return [k.strip().lower() for k in self.critical_keywords.split(",")]
    
    @property
    def high_urgency_keywords_list(self) -> List[str]:
        """Parse high urgency keywords into list."""
        return [k.strip().lower() for k in self.high_urgency_keywords.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
