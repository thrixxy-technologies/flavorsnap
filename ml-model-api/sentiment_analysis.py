from transformers import pipeline
from functools import lru_cache

# Lazy loaded pipeline
_sentiment_pipeline = None

def get_sentiment_pipeline():
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        _sentiment_pipeline = pipeline("sentiment-analysis")
    return _sentiment_pipeline

@lru_cache(maxsize=1000)
def analyze_sentiment(text: str):
    """
    Analyzes the sentiment of a given food description.
    Returns the label (e.g. POSITIVE/NEGATIVE) and confidence score.
    """
    if not text.strip():
        return {"label": "NEUTRAL", "score": 1.0}
    
    sentiment_model = get_sentiment_pipeline()
    result = sentiment_model(text)[0]
    
    return {
        "label": result['label'],
        "score": float(result['score'])
    }
