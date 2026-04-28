from transformers import pipeline
from functools import lru_cache

_zero_shot_pipeline = None

# Default categories relevant to food descriptions
DEFAULT_FOOD_CATEGORIES = [
    "Spicy", "Sweet", "Savory", "Healthy", "Vegan", 
    "Vegetarian", "Dessert", "Breakfast", "Fast Food", "Beverage"
]

def get_classification_pipeline():
    global _zero_shot_pipeline
    if _zero_shot_pipeline is None:
        _zero_shot_pipeline = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    return _zero_shot_pipeline

@lru_cache(maxsize=500)
def classify_text(text: str, categories_tuple: tuple = None):
    """
    Classifies the text into predefined food categories using zero-shot classification.
    Uses a tuple for categories to support LRU caching.
    """
    if not text.strip():
        return {"labels": [], "scores": []}
    
    categories = list(categories_tuple) if categories_tuple else DEFAULT_FOOD_CATEGORIES
    
    classifier = get_classification_pipeline()
    result = classifier(text, candidate_labels=categories, multi_label=True)
    
    # Filter out low-confidence scores
    threshold = 0.3
    filtered_labels = []
    filtered_scores = []
    
    for label, score in zip(result['labels'], result['scores']):
        if score > threshold:
            filtered_labels.append(label)
            filtered_scores.append(float(score))
            
    return {
        "labels": filtered_labels,
        "scores": filtered_scores
    }
