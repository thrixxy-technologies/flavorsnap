from flask import Blueprint, request, jsonify
from text_analysis import preprocess_text, detect_language, extract_entities, summarize_text
from sentiment_analysis import analyze_sentiment
from text_classification import classify_text
import logging

logger = logging.getLogger(__name__)

nlp_bp = Blueprint('nlp', __name__, url_prefix='/nlp')

@nlp_bp.route('/preprocess', methods=['POST'])
def preprocess_endpoint():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Missing 'text' parameter"}), 400
    
    text = data['text']
    cleaned_text = preprocess_text(text)
    return jsonify({"original": text, "preprocessed": cleaned_text})

@nlp_bp.route('/language', methods=['POST'])
def language_endpoint():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Missing 'text' parameter"}), 400
    
    text = data['text']
    language = detect_language(text)
    return jsonify({"text": text, "language": language})

@nlp_bp.route('/ner', methods=['POST'])
def ner_endpoint():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Missing 'text' parameter"}), 400
    
    text = data['text']
    try:
        entities = extract_entities(text)
        return jsonify({"text": text, "entities": entities})
    except Exception as e:
        logger.error(f"NER error: {e}")
        return jsonify({"error": "Failed to extract entities"}), 500

@nlp_bp.route('/summarize', methods=['POST'])
def summarize_endpoint():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Missing 'text' parameter"}), 400
    
    text = data['text']
    try:
        summary = summarize_text(text)
        return jsonify({"original": text, "summary": summary})
    except Exception as e:
        logger.error(f"Summarize error: {e}")
        return jsonify({"error": "Failed to summarize text"}), 500

@nlp_bp.route('/sentiment', methods=['POST'])
def sentiment_endpoint():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Missing 'text' parameter"}), 400
    
    text = data['text']
    try:
        sentiment = analyze_sentiment(text)
        return jsonify({"text": text, "sentiment": sentiment})
    except Exception as e:
        logger.error(f"Sentiment error: {e}")
        return jsonify({"error": "Failed to analyze sentiment"}), 500

@nlp_bp.route('/classify', methods=['POST'])
def classify_endpoint():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Missing 'text' parameter"}), 400
    
    text = data['text']
    categories = data.get('categories')
    
    try:
        cat_tuple = tuple(categories) if categories else None
        classification = classify_text(text, cat_tuple)
        return jsonify({"text": text, "classification": classification})
    except Exception as e:
        logger.error(f"Classify error: {e}")
        return jsonify({"error": "Failed to classify text"}), 500

def register_nlp_endpoints(app):
    app.register_blueprint(nlp_bp)
