"""
BERT Sentiment Analysis Service.
Uses a pre-trained BERT model for multilingual sentiment classification.
"""

from typing import Dict, Any, Tuple, List
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
import torch

from app.config import get_settings

settings = get_settings()


class SentimentAnalyzer:
    """
    Sentiment analysis using BERT-based model.
    Classifies text into 5 sentiment levels (1-5 stars).
    """
    
    _instance = None
    _pipeline = None
    
    def __new__(cls):
        """Singleton pattern to avoid loading model multiple times."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the BERT sentiment pipeline."""
        if self._initialized:
            return
        
        print(f"Loading BERT sentiment model: {settings.bert_sentiment_model}")
        
        # Use GPU if available
        device = 0 if torch.cuda.is_available() else -1
        
        self._pipeline = pipeline(
            "sentiment-analysis",
            model=settings.bert_sentiment_model,
            device=device,
            truncation=True,
            max_length=512
        )
        
        self._initialized = True
        print("BERT sentiment model loaded successfully!")
    
    # Mapping from star ratings to sentiment labels
    SENTIMENT_LABELS = {
        "1 star": "very_negative",
        "2 stars": "negative", 
        "3 stars": "neutral",
        "4 stars": "positive",
        "5 stars": "very_positive"
    }
    
    # Sentiment to score mapping (-1 to 1)
    SENTIMENT_SCORES = {
        "very_negative": -1.0,
        "negative": -0.5,
        "neutral": 0.0,
        "positive": 0.5,
        "very_positive": 1.0
    }
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of the given text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary containing:
                - label: Sentiment label (very_negative to very_positive)
                - score: Sentiment score (-1.0 to 1.0)
                - confidence: Model confidence (0.0 to 1.0)
                - raw_label: Original model output label
        """
        if not text or not text.strip():
            return {
                "label": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "raw_label": None
            }
        
        # Truncate very long text
        text = text[:5000] if len(text) > 5000 else text
        
        # Get prediction from BERT model
        result = self._pipeline(text)[0]
        raw_label = result["label"]
        confidence = result["score"]
        
        # Map to our sentiment labels
        sentiment_label = self.SENTIMENT_LABELS.get(raw_label, "neutral")
        sentiment_score = self.SENTIMENT_SCORES.get(sentiment_label, 0.0)
        
        return {
            "label": sentiment_label,
            "score": sentiment_score,
            "confidence": confidence,
            "raw_label": raw_label
        }
    
    def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze sentiment of multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of sentiment analysis results
        """
        if not texts:
            return []
        
        # Truncate long texts
        processed_texts = [t[:5000] if len(t) > 5000 else t for t in texts]
        
        results = self._pipeline(processed_texts)
        
        return [
            {
                "label": self.SENTIMENT_LABELS.get(r["label"], "neutral"),
                "score": self.SENTIMENT_SCORES.get(
                    self.SENTIMENT_LABELS.get(r["label"], "neutral"), 0.0
                ),
                "confidence": r["score"],
                "raw_label": r["label"]
            }
            for r in results
        ]
    
    def get_sentiment_category(self, score: float) -> str:
        """
        Get sentiment category from numeric score.
        
        Args:
            score: Sentiment score (-1.0 to 1.0)
            
        Returns:
            Sentiment category label
        """
        if score <= -0.75:
            return "very_negative"
        elif score <= -0.25:
            return "negative"
        elif score <= 0.25:
            return "neutral"
        elif score <= 0.75:
            return "positive"
        else:
            return "very_positive"
    
    def is_negative(self, text: str) -> bool:
        """Check if text has negative sentiment."""
        result = self.analyze(text)
        return result["score"] < -0.25
    
    def is_positive(self, text: str) -> bool:
        """Check if text has positive sentiment."""
        result = self.analyze(text)
        return result["score"] > 0.25


# Global instance
sentiment_analyzer = SentimentAnalyzer()
