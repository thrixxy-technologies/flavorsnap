# Design Document: Advanced NLP

## Overview

The Advanced NLP system provides intelligent text processing capabilities for a food platform, exposing classification, sentiment analysis, content generation, language detection, and translation through a dedicated Python API service. A React/TypeScript frontend component gives users direct access to these features without requiring API knowledge.

The system is designed around a modular NLP pipeline: each capability is an independently invocable service backed by a dedicated model or model ensemble. A shared caching layer prevents redundant inference for identical inputs within a 60-second window. All endpoints are documented via an auto-generated OpenAPI 3.0 specification.

## Architecture

```mermaid
graph TD
    UI[NLP_Interface React Component] --> API[NLP_API FastAPI Service]
    API --> TA[Text_Analyzer]
    API --> CG[Content_Generator]
    API --> Cache[Inference Cache TTL=60s]
    TA --> ClassifyModel[Classification Model]
    TA --> SentimentModel[Sentiment Model]
    TA --> LangDetectModel[Language Detection Model]
    CG --> GenModel[Generation Model]
    API --> TranslationService[Translation Service]
    API --> Health[/health endpoint]
    API --> Docs[/docs OpenAPI 3.0]
    Cache --> TA
    Cache --> CG
    Cache --> TranslationService
```

The backend is a Python FastAPI service. FastAPI is chosen because it auto-generates OpenAPI 3.0 documentation from type annotations, satisfying Requirement 6 with no additional tooling. The frontend is a React/TypeScript component consuming the REST endpoints. Models are loaded in-process at startup.

## Components and Interfaces

### Text_Analyzer (`text_analysis.py`)

Handles classification, sentiment analysis, and language detection. Each method validates input length before invoking the model.

```python
class ClassificationResult:
    labels: list[tuple[str, float]]  # (label, confidence_score), top 3 descending
    processing_time_ms: float

class SentimentResult:
    score: float                     # [-1.0, 1.0]
    label: Literal["positive", "neutral", "negative"]
    aspects: list[AspectSentiment]   # up to 5 food attributes

class AspectSentiment:
    attribute: str                   # e.g. "taste", "texture"
    score: float                     # [-1.0, 1.0]
    label: Literal["positive", "neutral", "negative"]

class LanguageDetectionResult:
    language_code: str               # ISO 639-1
    confidence_score: float          # [0.0, 1.0]
    low_confidence: bool             # True if confidence_score < 0.6

class TextAnalyzer:
    def classify(self, text: str) -> ClassificationResult: ...
    def analyze_sentiment(self, text: str) -> SentimentResult: ...
    def detect_language(self, text: str) -> LanguageDetectionResult: ...
```

### Content_Generator (`content_generation.py`)

Generates food descriptions from structured input. Validates required fields and post-processes output to remove placeholder tokens, incomplete sentences, and repeated phrases.

```python
class GenerationRequest:
    food_name: str
    ingredients: list[str]           # at least one required
    cuisine_type: str | None
    tone: Literal["formal", "casual", "marketing"] = "casual"

class GenerationResult:
    description: str                 # 50–300 words
    confidence_score: float          # [0.0, 1.0] estimated quality
    word_count: int

class ContentGenerator:
    def generate(self, request: GenerationRequest) -> GenerationResult: ...
```

### NLP_API (`nlp_api.py`)

FastAPI application wiring all components together. Handles input validation, error responses, caching, and OpenAPI documentation.

```
POST /classify              → ClassificationResult
POST /sentiment             → SentimentResult
POST /generate              → GenerationResult
POST /detect-language       → LanguageDetectionResult
POST /translate             → TranslationResult
GET  /health                → HealthStatus
GET  /docs                  → OpenAPI 3.0 UI (auto-generated)
```

### Translation Service (within `nlp_api.py`)

Handles translation requests. Validates language pair support and identical source/target codes before invoking the translation model.

```python
class TranslationRequest:
    text: str
    source_language: str | None      # ISO 639-1; if None, auto-detected
    target_language: str             # ISO 639-1

class TranslationResult:
    translated_text: str
    source_language: str             # detected or provided
    target_language: str

SUPPORTED_LANGUAGE_PAIRS: set[tuple[str, str]]  # minimum 20 pairs
```

### Inference Cache

An in-process TTL cache (e.g., `cachetools.TTLCache`) keyed on `(endpoint, sha256(request_body))` with a 60-second TTL. Shared across all endpoints. Cache hits bypass model inference entirely.

### NLP_Interface (`NLPInterface.tsx`)

React component providing a tabbed UI for all NLP features. Each tab contains an input form, a submit button, a loading indicator, and a results panel. Copy-to-clipboard is available on generated/translated text outputs.

Key sub-components:
- `ClassificationTab` — text input, submit, label/confidence results
- `SentimentTab` — text input, submit, score/label/aspect results
- `GenerationTab` — structured form (name, ingredients, cuisine, tone), submit, description output with copy button
- `LanguageTab` — text input, submit, language code/confidence results
- `TranslationTab` — text input, source/target language selectors, submit, translated output with copy button
- `LoadingIndicator` — shown while request is in-flight; submit button disabled
- `ErrorBanner` — human-readable error message on API failure

## Data Models

```python
# Shared input validation constants
MAX_TEXT_LENGTH = 5000          # characters; 400 if exceeded
MIN_SENTIMENT_WORDS = 3         # words; 422 if below
MIN_LANGUAGE_CHARS = 10         # characters; 422 if below
MAX_TRANSLATION_WORDS = 500     # words
LOW_CONFIDENCE_THRESHOLD = 0.6

@dataclass
class ClassifyRequest:
    text: str                   # 1–5000 characters

@dataclass
class SentimentRequest:
    text: str                   # >= 3 words

@dataclass
class LanguageDetectRequest:
    text: str                   # >= 10 characters

@dataclass
class TranslationRequest:
    text: str                   # up to 500 words
    source_language: str | None
    target_language: str

@dataclass
class GenerationRequest:
    food_name: str
    ingredients: list[str]
    cuisine_type: str | None
    tone: Literal["formal", "casual", "marketing"] = "casual"

@dataclass
class HealthStatus:
    status: Literal["ok", "degraded", "unavailable"]
    models_loaded: dict[str, bool]
    timestamp: datetime

@dataclass
class ErrorResponse:
    error: str                  # machine-readable code
    message: str                # human-readable description
    missing_fields: list[str] | None  # populated for 400 on missing fields
```

All error responses use the structure `{ "error": "<code>", "message": "<human-readable>", ... }`.


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Classification output structure

*For any* non-empty text input up to 5000 characters, the classification endpoint shall return between 1 and 3 Classification_Labels, each with a Confidence_Score in [0.0, 1.0], and the labels shall be ordered by Confidence_Score in descending order.

**Validates: Requirements 1.1, 1.5**

---

### Property 2: Sentiment output validity

*For any* valid text input (at least 3 words), the sentiment analysis endpoint shall return a Sentiment_Score in the closed interval [-1.0, 1.0] and a categorical label that is exactly one of "positive", "neutral", or "negative".

**Validates: Requirements 2.1, 2.4**

---

### Property 3: Aspect sentiment count is bounded

*For any* valid food description submitted to the sentiment analysis endpoint, the returned aspects list shall have a length in [0, 5] — never more than 5 aspect-level sentiment entries.

**Validates: Requirements 2.5**

---

### Property 4: Generation output completeness

*For any* valid generation request (food_name present, at least one ingredient), the Content_Generator shall return a Food_Description whose word count is in [50, 300] and a Confidence_Score in [0.0, 1.0].

**Validates: Requirements 3.1, 3.5**

---

### Property 5: Generated description quality invariants

*For any* valid generation request, the returned Food_Description shall contain no placeholder tokens (e.g., `[MASK]`, `<UNK>`, `{placeholder}`), no incomplete sentences ending mid-word, and no phrase of more than 5 consecutive words that appears more than once in the output.

**Validates: Requirements 3.6**

---

### Property 6: Language detection output completeness and low-confidence flag

*For any* text input of at least 10 characters, the language detection endpoint shall return a Language_Code (ISO 639-1 format) and a Confidence_Score in [0.0, 1.0], and the `low_confidence` flag shall be `true` if and only if the Confidence_Score is below 0.6.

**Validates: Requirements 4.1, 4.4**

---

### Property 7: Translation response completeness

*For any* valid Translation_Request, the response shall include the translated text and a `target_language` matching the requested target; if `source_language` was not provided in the request, the response shall include a non-null detected `source_language`.

**Validates: Requirements 5.1, 5.6**

---

### Property 8: Cache hit returns identical result without re-invoking the model

*For any* request to any NLP endpoint, submitting the identical request a second time within 60 seconds shall return the same result as the first call, and the underlying model inference function shall be invoked exactly once across both calls.

**Validates: Requirements 7.2**

---

### Property 9: Model unavailability returns HTTP 503

*For any* NLP endpoint when the underlying model is unavailable or fails to load, the endpoint shall return an HTTP 503 response, and a log entry containing a timestamp and error details shall exist.

**Validates: Requirements 7.5**

---

### Property 10: API error response renders error banner in UI

*For any* NLP API error response (4xx or 5xx), the NLP_Interface shall render a human-readable error message visible to the user, and the previous results (if any) shall remain visible.

**Validates: Requirements 8.3**

---

### Property 11: In-flight request disables submit and shows loading indicator

*For any* NLP request that is in progress, the NLP_Interface shall display a loading indicator and the submit control shall be in a disabled state, preventing duplicate submissions.

**Validates: Requirements 8.4**

---

## Error Handling

| Scenario | HTTP Status | Behavior |
|---|---|---|
| Empty text input | 400 | Return descriptive error message |
| Text exceeds 5000 characters | 400 | Return descriptive error message |
| Sentiment input fewer than 3 words | 422 | Return insufficient input error |
| Language detection input fewer than 10 characters | 422 | Return insufficient input error |
| Generation request missing food_name or ingredients | 400 | Return error listing missing fields |
| Translation source == target language | 400 | Return "no translation needed" error |
| Unsupported language code in translation | 422 | Return error listing supported language codes |
| Model unavailable / fails to load | 503 | Return service unavailable; log timestamp and error details |
| Cache miss + model timeout | 504 | Return gateway timeout; log endpoint and elapsed time |
| Invalid tone parameter | 422 | Return error listing valid tone values |

All error responses use the structure: `{ "error": "<code>", "message": "<human-readable>", "missing_fields": [...] | null }`.

## Testing Strategy

### Unit Tests

Focus on specific examples, edge cases, and integration points:

- `TextAnalyzer.classify()` with boundary-length inputs (1 char, 5000 chars, 5001 chars)
- `TextAnalyzer.analyze_sentiment()` with exactly 2 words (should fail) and exactly 3 words (should succeed)
- `TextAnalyzer.detect_language()` with exactly 9 characters (should fail) and 10 characters (should succeed)
- `ContentGenerator.generate()` with missing `food_name` and with empty `ingredients` list
- `ContentGenerator.generate()` with each valid tone value ("formal", "casual", "marketing")
- Translation endpoint with `source_language == target_language`
- Translation endpoint with an unsupported language code
- `/health` endpoint returns HTTP 200 with `models_loaded` dict
- `/docs` endpoint returns HTTP 200 and response body contains `"openapi": "3.0`
- OpenAPI spec contains at least one example per endpoint path
- NLP_Interface renders error banner when API returns 4xx
- NLP_Interface submit button is disabled while request is in-flight
- NLP_Interface copy button triggers `navigator.clipboard.writeText`

### Property-Based Tests

Use [Hypothesis](https://hypothesis.readthedocs.io/) (Python) and [fast-check](https://fast-check.io/) (TypeScript). Each property test runs a minimum of 100 iterations.

Each test is tagged with a comment in the format:
`# Feature: advanced-nlp, Property <N>: <property_text>`

**Python property tests (`pytest` + `hypothesis`):**

- **Property 1**: Generate random strings of length 1–5000; assert result has 1–3 labels, each score in [0.0, 1.0], sorted descending.
  `# Feature: advanced-nlp, Property 1: classification output structure`

- **Property 2**: Generate random strings of at least 3 words; assert sentiment score ∈ [-1.0, 1.0] and label ∈ {"positive", "neutral", "negative"}.
  `# Feature: advanced-nlp, Property 2: sentiment output validity`

- **Property 3**: Generate random food descriptions; assert aspects list length ∈ [0, 5].
  `# Feature: advanced-nlp, Property 3: aspect sentiment count bounded`

- **Property 4**: Generate random valid GenerationRequests; assert word count ∈ [50, 300] and confidence_score ∈ [0.0, 1.0].
  `# Feature: advanced-nlp, Property 4: generation output completeness`

- **Property 5**: Generate random valid GenerationRequests; assert output contains no placeholder tokens and no phrase of >5 consecutive words repeated.
  `# Feature: advanced-nlp, Property 5: generated description quality invariants`

- **Property 6**: Generate random strings of length ≥ 10; assert language_code is a 2-letter string, confidence_score ∈ [0.0, 1.0], and low_confidence == (confidence_score < 0.6).
  `# Feature: advanced-nlp, Property 6: language detection output completeness and low-confidence flag`

- **Property 7**: Generate random valid TranslationRequests (with and without source_language); assert target_language matches request and source_language is non-null when not provided.
  `# Feature: advanced-nlp, Property 7: translation response completeness`

- **Property 8**: Generate random valid requests for each endpoint; call twice within TTL window with mocked model; assert model called exactly once and both responses are equal.
  `# Feature: advanced-nlp, Property 8: cache hit returns identical result without re-invoking model`

- **Property 9**: For each endpoint, simulate model unavailability; assert HTTP 503 and log entry with timestamp and error details.
  `# Feature: advanced-nlp, Property 9: model unavailability returns HTTP 503`

**TypeScript property tests (`vitest` + `fast-check`):**

- **Property 10**: Generate random API error responses (random 4xx/5xx status and message); render NLP_Interface with mocked fetch; assert error banner is visible.
  `// Feature: advanced-nlp, Property 10: API error response renders error banner`

- **Property 11**: Generate random NLP request states; set request in-flight; assert submit button has `disabled` attribute and loading indicator is present in DOM.
  `// Feature: advanced-nlp, Property 11: in-flight request disables submit and shows loading indicator`
