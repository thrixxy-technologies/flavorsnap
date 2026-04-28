import sys
import os

try:
    from text_analysis import preprocess_text, detect_language, extract_entities, summarize_text
    from sentiment_analysis import analyze_sentiment
    from text_classification import classify_text

    print("--- Testing Preprocessing ---")
    print("Preprocess:", preprocess_text("This is a VERY spicy food!"))
    
    print("--- Testing Language Detection ---")
    print("Language:", detect_language("This is a VERY spicy food!"))
    
    print("--- Testing Sentiment Analysis ---")
    print("Sentiment:", analyze_sentiment("I absolutely love this delicious Jollof rice!"))
    
    print("--- Testing Named Entity Recognition ---")
    print("NER:", extract_entities("I bought some Amala from a restaurant in Lagos."))
    
    print("--- Testing Text Classification ---")
    print("Classify:", classify_text("This cake is very sweet and has chocolate.", ("Sweet", "Spicy", "Dessert")))
    
    print("--- Testing Text Summarization ---")
    long_text = "Jollof rice, or jollof, also known as benachin in Wolof, is a rice dish from West Africa. The dish is typically made with long-grain rice, tomatoes, onions, spices, vegetables and meat in a single pot, although its ingredients and preparation methods vary across different regions. Jollof rice is one of the most common dishes in West Africa."
    print("Summarize:", summarize_text(long_text))
    
    print("\nALL TESTS PASSED SUCCESSFULLY.")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
