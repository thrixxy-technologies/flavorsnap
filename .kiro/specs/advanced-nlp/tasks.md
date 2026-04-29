# Implementation Plan: Advanced NLP

## Overview

Implement the NLP pipeline incrementally: data models and validation first, then each NLP capability (classification, sentiment, generation, language detection, translation), then the caching layer, API wiring, and finally the frontend component.

## Tasks

- [ ] 1. Define shared data models and input validation
  - Create Pydantic request/response models in `nlp_api.py`: `ClassifyRequest`, `SentimentRequest`, `LanguageDetectRequest`, `TranslationRequest`, `GenerationRequest`, `HealthStatus`, `ErrorResponse`
  - Implement shared validation constants: `MAX_TEXT_LENGTH`, `MIN_SENTIMENT_WORDS`, `MIN_LANGUAGE_CHARS`, `MAX_TRANSLATION_WORDS`, `LOW_CONFIDENCE_THRESHOLD`
  - _Requirements: 1.3, 2.3, 3.3, 4.5, 5.4, 5.5_

- [ ] 2. Implement Text_Analyzer — classification
  - Implement `TextAnalyzer.classify()` in `text_analysis.py` with a minimum of 20 food categories
  - Return top 3 `ClassificationResult` labels sorted by confidence descending
  - Raise validation error for empty or >5000 character inputs
  - _Requirements: 1.1, 1.3, 1.4, 1.5_

  - [ ]* 2.1 Write property test for classification output structure
    - **Property 1: Classification output structure**
    - **Validates: Requirements 1.1, 1.5**

- [ ] 3. Implement Text_Analyzer — sentiment analysis
  - Implement `TextAnalyzer.analyze_sentiment()` in `text_analysis.py`
  - Return `SentimentResult` with score in [-1.0, 1.0], categorical label, and up to 5 aspect sentiments
  - Raise validation error for inputs fewer than 3 words
  - _Requirements: 2.1, 2.3, 2.4, 2.5_

  - [ ]* 3.1 Write property test for sentiment output validity
    - **Property 2: Sentiment output validity**
    - **Validates: Requirements 2.1, 2.4**

  - [ ]* 3.2 Write property test for aspect sentiment count bound
    - **Property 3: Aspect sentiment count is bounded**
    - **Validates: Requirements 2.5**

- [ ] 4. Implement Text_Analyzer — language detection
  - Implement `TextAnalyzer.detect_language()` in `text_analysis.py` supporting ≥50 languages
  - Return `LanguageDetectionResult` with ISO 639-1 code, confidence score, and `low_confidence` flag when score < 0.6
  - Raise validation error for inputs fewer than 10 characters
  - _Requirements: 4.1, 4.3, 4.4, 4.5_

  - [ ]* 4.1 Write property test for language detection output completeness
    - **Property 6: Language detection output completeness and low-confidence flag**
    - **Validates: Requirements 4.1, 4.4**

- [ ] 5. Implement Content_Generator
  - Implement `ContentGenerator.generate()` in `content_generation.py`
  - Validate required fields (`food_name`, at least one ingredient); return HTTP 400 listing missing fields
  - Accept optional `tone` parameter ("formal", "casual", "marketing")
  - Post-process output to remove placeholder tokens, incomplete sentences, and repeated phrases >5 consecutive words
  - Return `GenerationResult` with description (50–300 words) and confidence score
  - _Requirements: 3.1, 3.3, 3.4, 3.5, 3.6_

  - [ ]* 5.1 Write property test for generation output completeness
    - **Property 4: Generation output completeness**
    - **Validates: Requirements 3.1, 3.5**

  - [ ]* 5.2 Write property test for generated description quality invariants
    - **Property 5: Generated description quality invariants**
    - **Validates: Requirements 3.6**

- [ ] 6. Checkpoint — Ensure all component-level tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement inference cache
  - Add `cachetools.TTLCache` keyed on `(endpoint, sha256(request_body))` with 60-second TTL in `nlp_api.py`
  - Wrap all endpoint handlers to check cache before invoking model; store result on miss
  - _Requirements: 7.2_

  - [ ]* 7.1 Write property test for cache hit behavior
    - **Property 8: Cache hit returns identical result without re-invoking the model**
    - **Validates: Requirements 7.2**

- [ ] 8. Implement NLP_API FastAPI application
  - Create FastAPI app in `nlp_api.py` with routes: `POST /classify`, `POST /sentiment`, `POST /generate`, `POST /detect-language`, `POST /translate`
  - Wire `TextAnalyzer` and `ContentGenerator` instances into route handlers
  - Implement translation route with `SUPPORTED_LANGUAGE_PAIRS` (≥20 pairs); validate identical source/target and unsupported codes
  - Map component validation errors to HTTP 400/422 responses using `ErrorResponse` schema
  - Handle model load failures with HTTP 503 and structured log entry (timestamp + error details)
  - _Requirements: 1.2, 2.2, 3.2, 4.2, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 7.1, 7.5_

  - [ ]* 8.1 Write property test for model unavailability returns HTTP 503
    - **Property 9: Model unavailability returns HTTP 503**
    - **Validates: Requirements 7.5**

  - [ ]* 8.2 Write property test for translation response completeness
    - **Property 7: Translation response completeness**
    - **Validates: Requirements 5.1, 5.6**

- [ ] 9. Implement `/health` endpoint and OpenAPI documentation
  - Add `GET /health` route returning `HealthStatus` (status, models_loaded dict, timestamp) within 100ms
  - Annotate all request/response models with field descriptions, constraints, and `openapi_examples` so FastAPI auto-generates a complete OpenAPI 3.0 spec at `/docs`
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.3_

  - [ ]* 9.1 Write unit tests for `/health` and `/docs` endpoints
    - Assert `/health` returns HTTP 200 with `models_loaded` dict
    - Assert `/docs` returns HTTP 200 and body contains `"openapi": "3.0`
    - Assert OpenAPI spec contains at least one example per endpoint path
    - _Requirements: 6.1, 6.3, 7.3_

- [ ] 10. Checkpoint — Ensure all API-level tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement NLPInterface React component
  - Create `NLPInterface.tsx` with tabbed layout: `ClassificationTab`, `SentimentTab`, `GenerationTab`, `LanguageTab`, `TranslationTab`
  - Each tab: input form, submit button, `LoadingIndicator` (disables submit while in-flight), results panel, `ErrorBanner` on API error
  - Add copy-to-clipboard button on `GenerationTab` and `TranslationTab` outputs
  - Display results without full page reload on completion
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 11.1 Write property test for API error renders error banner
    - **Property 10: API error response renders error banner in UI**
    - **Validates: Requirements 8.3**

  - [ ]* 11.2 Write property test for in-flight request disables submit
    - **Property 11: In-flight request disables submit and shows loading indicator**
    - **Validates: Requirements 8.4**

  - [ ]* 11.3 Write unit tests for NLPInterface
    - Test copy button triggers `navigator.clipboard.writeText`
    - _Requirements: 8.5_

- [ ] 12. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Property tests use `hypothesis` (Python) and `fast-check` (TypeScript), each running ≥100 iterations
- Each property test must include the tag comment: `# Feature: advanced-nlp, Property <N>: <title>`
- All error responses use the shape `{ "error": "<code>", "message": "<human-readable>", "missing_fields": [...] | null }`
