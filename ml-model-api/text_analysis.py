import re
from langdetect import detect, DetectorFactory
from transformers import pipeline
from functools import lru_cache
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Set seed for langdetect for deterministic results
DetectorFactory.seed = 0

# Ensure nltk data is downloaded
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
    nltk.data.find('corpora/stopwords')
except LookupError:
    import ssl
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context
    nltk.download('punkt')
    nltk.download('punkt_tab')
    nltk.download('stopwords')

# Lazy loaded pipelines
_ner_pipeline = None
_summarization_pipeline = None

def get_ner_pipeline():
    global _ner_pipeline
    if _ner_pipeline is None:
        _ner_pipeline = pipeline("ner", aggregation_strategy="simple")
    return _ner_pipeline

def get_summarization_pipeline():
    global _summarization_pipeline
    if _summarization_pipeline is None:
        # Use a smaller model for summarization to save memory
        _summarization_pipeline = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
    return _summarization_pipeline

@lru_cache(maxsize=1000)
def preprocess_text(text: str) -> str:
    """Cleans and standardizes the input text."""
    if not text:
        return ""
    # Lowercase
    text = text.lower()
    # Remove special characters
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    # Tokenize
    tokens = word_tokenize(text)
    # Remove stopwords
    stop_words = set(stopwords.words('english'))
    filtered_tokens = [w for w in tokens if not w in stop_words]
    return " ".join(filtered_tokens)

@lru_cache(maxsize=1000)
def detect_language(text: str) -> str:
    """Detects the language of the text."""
    try:
        return detect(text)
    except:
        return "unknown"

@lru_cache(maxsize=100)
def extract_entities(text: str):
    """Extracts named entities from the text."""
    ner = get_ner_pipeline()
    entities = ner(text)
    # Convert numpy types to standard python types for JSON serialization
    results = []
    for ent in entities:
        results.append({
            "entity_group": ent.get("entity_group", ent.get("entity", "UNKNOWN")),
            "score": float(ent["score"]),
            "word": ent["word"],
            "start": int(ent["start"]),
            "end": int(ent["end"])
        })
    return results

@lru_cache(maxsize=100)
def summarize_text(text: str):
    """Summarizes the text if it's long enough."""
    if len(text.split()) < 20:
        return text  # Too short to summarize
    summarizer = get_summarization_pipeline()
    # Use max_length safely
    input_length = len(text.split())
    max_length = min(130, input_length - 1)
    min_length = min(30, max_length - 1)
    
    summary = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
    return summary[0]['summary_text']
