# FlavorSnap Advanced Recommendation System

## Overview

The FlavorSnap Advanced Recommendation System is a comprehensive, production-ready recommendation engine designed specifically for food recommendations. It implements multiple recommendation algorithms, real-time personalization, A/B testing capabilities, and comprehensive monitoring.

## Architecture

The system consists of several key components:

### Core Components

1. **User Profiling System** (`user_profiling.py`)
   - Tracks user preferences and interaction history
   - Maintains dietary restrictions and cuisine preferences
   - Calculates user similarity for collaborative filtering

2. **Collaborative Filtering Engine** (`collaborative_filtering.py`)
   - User-based collaborative filtering
   - Item-based collaborative filtering
   - Matrix factorization using SVD
   - Hybrid collaborative filtering approach

3. **Content-Based Filtering** (`content_based.py`)
   - Feature extraction from food items
   - Similarity calculation based on food characteristics
   - Dietary restriction filtering
   - Explanation generation

4. **Hybrid Recommendation Engine** (`recommendation_engine.py`)
   - Combines multiple recommendation approaches
   - Weight-based algorithm fusion
   - Diversity and novelty optimization
   - Real-time caching

5. **Real-time Recommendations** (`realtime_recommendations.py`)
   - Session-based personalization
   - Real-time event processing
   - Incremental model updates
   - Context-aware recommendations

6. **A/B Testing Framework** (`recommendation_ab_testing.py`)
   - Statistical testing of recommendation variants
   - Multiple hypothesis correction
   - Traffic allocation and user assignment
   - Performance analysis

7. **Performance Monitoring** (`recommendation_monitoring.py`)
   - Real-time metrics collection
   - Performance alerting
   - Historical analysis
   - System health monitoring

8. **REST API** (`recommendation_api.py`)
   - Complete REST interface
   - Rate limiting and security
   - Comprehensive endpoints
   - Error handling

## Features

### Recommendation Algorithms

- **Collaborative Filtering**: User-based and item-based approaches with matrix factorization
- **Content-Based Filtering**: Feature-based similarity matching with dietary considerations
- **Hybrid Approach**: Weighted combination of multiple algorithms
- **Real-time Personalization**: Session-aware and context-sensitive recommendations

### Advanced Capabilities

- **A/B Testing**: Statistical testing of algorithm variants with proper significance testing
- **Performance Monitoring**: Real-time metrics, alerting, and historical analysis
- **User Profiling**: Comprehensive preference tracking and similarity analysis
- **Diversity & Novelty**: Optimization for recommendation variety and discovery
- **Explainability**: Detailed explanations for recommendation decisions

### API Endpoints

#### Recommendations
- `GET /api/recommendations` - Get personalized recommendations
- `GET /api/recommendations/realtime` - Get real-time recommendations
- `GET /api/recommendations/similar/<item_id>` - Get similar items
- `GET /api/recommendations/search` - Search food items
- `GET /api/recommendations/items/<item_id>` - Get item details

#### User Management
- `GET /api/recommendations/users/<user_id>/profile` - Get user profile
- `GET /api/recommendations/users/<user_id>/history` - Get user history
- `POST /api/recommendations/feedback` - Record user feedback

#### A/B Testing
- `GET /api/ab-tests` - List all tests
- `GET /api/ab-tests/<test_id>` - Get test details
- `POST /api/ab-tests` - Create new test
- `POST /api/ab-tests/<test_id>/start` - Start test
- `POST /api/ab-tests/<test_id>/stop` - Stop test

#### Monitoring
- `GET /api/monitoring/performance` - Get performance summary
- `GET /api/monitoring/report` - Generate performance report
- `GET /api/monitoring/metrics/<metric_name>` - Get metric history
- `GET /api/monitoring/top-items` - Get top performing items

## Installation

### Dependencies

```bash
pip install flask flask-cors flask-limiter
pip install numpy pandas scipy scikit-learn
pip install psutil
pip install sqlite3
```

### Database Setup

The system uses SQLite for data persistence. Database tables are created automatically on first run.

### Configuration

```python
# Recommendation system configuration
config = RecommendationConfig(
    collaborative_weight=0.4,
    content_based_weight=0.3,
    user_profile_weight=0.2,
    popularity_weight=0.1,
    diversity_threshold=0.3,
    novelty_boost=0.1,
    max_recommendations=50
)
```

## Usage

### Basic Recommendations

```python
from recommendation_engine import HybridRecommendationEngine

# Initialize engine
engine = HybridRecommendationEngine()

# Get recommendations
result = engine.get_recommendations(
    user_id="user123",
    n_recommendations=10,
    context={"meal_type": "lunch", "location": "nigeria"}
)

# Process recommendations
for recommendation in result.recommendations:
    print(f"Item: {recommendation.item_id}, Score: {recommendation.score}")
    print(f"Explanation: {recommendation.explanation}")
```

### Real-time Recommendations

```python
from realtime_recommendations import RealtimeRecommendationSystem

# Initialize real-time system
realtime = RealtimeRecommendationSystem()

# Add user event
from realtime_recommendations import create_view_event
event = create_view_event("user123", "akara_001", "session456")
realtime.add_event(event)

# Get real-time recommendations
result = realtime.get_realtime_recommendations(
    user_id="user123",
    session_id="session456",
    context={"time_of_day": "afternoon"}
)
```

### A/B Testing

```python
from recommendation_ab_testing import ABTestingFramework, TestVariant, MetricType

# Initialize A/B testing framework
ab_testing = ABTestingFramework()

# Create test variants
variants = [
    TestVariant(
        variant_id="control",
        name="Control Algorithm",
        description="Current recommendation algorithm",
        configuration={"algorithm": "hybrid"},
        traffic_allocation=0.5,
        is_control=True
    ),
    TestVariant(
        variant_id="variant1",
        name="Enhanced Algorithm",
        description="Enhanced recommendation with more diversity",
        configuration={"algorithm": "hybrid", "diversity_threshold": 0.5},
        traffic_allocation=0.5
    )
]

# Create test
test_id = ab_testing.create_test(
    name="Diversity Enhancement Test",
    description="Test impact of increased diversity on user engagement",
    hypothesis="Increased diversity will improve user satisfaction",
    variants=variants,
    target_metrics=[MetricType.USER_SATISFACTION, MetricType.CLICK_THROUGH_RATE]
)

# Start test
ab_testing.start_test(test_id)

# Get user assignment
variant_id = ab_testing.assign_user_to_variant(test_id, "user123")
```

### Performance Monitoring

```python
from recommendation_monitoring import RecommendationMonitoring

# Initialize monitoring
monitoring = RecommendationMonitoring()

# Record metrics
monitoring.record_request(
    response_time_ms=150,
    success=True,
    cache_hit=False,
    user_id="user123",
    recommendation_count=10
)

# Get performance summary
summary = monitoring.get_performance_summary(hours=24)
print(f"Average response time: {summary['recommendation_metrics']['avg_response_time_ms']}ms")
print(f"Cache hit rate: {summary['recommendation_metrics']['cache_hit_rate']:.2%}")
```

## API Usage

### Get Recommendations

```bash
curl "http://localhost:5001/api/recommendations?user_id=user123&n=10&meal_type=lunch"
```

### Record Feedback

```bash
curl -X POST "http://localhost:5001/api/recommendations/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "item_id": "akara_001",
    "feedback_type": "rating",
    "rating": 4.5
  }'
```

### Get Performance Report

```bash
curl "http://localhost:5001/api/monitoring/report?hours=24"
```

## Configuration Options

### Recommendation Engine Configuration

```python
@dataclass
class RecommendationConfig:
    collaborative_weight: float = 0.4      # Weight for collaborative filtering
    content_based_weight: float = 0.3     # Weight for content-based filtering
    user_profile_weight: float = 0.2      # Weight for user profile preferences
    popularity_weight: float = 0.1         # Weight for popularity-based recommendations
    diversity_threshold: float = 0.3       # Minimum diversity threshold
    novelty_boost: float = 0.1             # Novelty boost factor
    max_recommendations: int = 50           # Maximum recommendations to generate
    cache_duration_minutes: int = 30       # Cache duration in minutes
```

### Real-time Configuration

```python
@dataclass
class RealtimeConfig:
    batch_size: int = 100                  # Event processing batch size
    update_interval_seconds: int = 30       # Model update interval
    realtime_weight: float = 0.3            # Weight for real-time adjustments
    session_timeout_minutes: int = 30       # Session timeout duration
    enable_async_processing: bool = True    # Enable async processing
```

### A/B Testing Configuration

```python
@dataclass
class ABTestConfig:
    max_concurrent_tests: int = 10          # Maximum concurrent tests
    default_test_duration_days: int = 14    # Default test duration
    minimum_sample_size: int = 1000         # Minimum sample size for significance
    confidence_level: float = 0.95          # Statistical confidence level
    multiple_testing_correction: str = "bonferroni"  # Multiple testing correction method
```

### Monitoring Configuration

```python
@dataclass
class MonitoringConfig:
    collection_interval_seconds: int = 60   # Metrics collection interval
    metrics_retention_days: int = 30       # Metrics retention period
    response_time_threshold_ms: float = 500  # Response time alert threshold
    error_rate_threshold: float = 0.05      # Error rate alert threshold
    enable_alerts: bool = True              # Enable alerting
```

## Performance Considerations

### Caching Strategy

- **Recommendation Caching**: Cache recommendations for 30 minutes by default
- **User Profile Caching**: Cache user profiles to reduce database queries
- **Similarity Matrix Caching**: Cache pre-computed similarity matrices
- **Real-time Event Caching**: Batch process events for efficiency

### Scalability

- **Database Optimization**: Use appropriate indexes for frequent queries
- **Batch Processing**: Process events and updates in batches
- **Async Processing**: Use background threads for non-critical operations
- **Memory Management**: Limit in-memory data structures with appropriate sizing

### Monitoring

- **Response Time**: Track average and percentile response times
- **Error Rate**: Monitor system error rates and alert on thresholds
- **Cache Performance**: Track cache hit rates and optimize accordingly
- **Resource Usage**: Monitor CPU, memory, and disk usage

## Testing

### Unit Tests

```python
# Test user profiling
def test_user_profiling():
    profiling = UserProfilingSystem()
    profile = profiling.create_user_profile("test_user")
    assert profile.user_id == "test_user"
    assert len(profile.preferences) == 0

# Test collaborative filtering
def test_collaborative_filtering():
    cf = CollaborativeFilteringEngine()
    cf.build_user_item_matrix()
    assert cf.user_item_matrix is not None

# Test content-based filtering
def test_content_based():
    cb = ContentBasedEngine()
    cb.build_feature_matrix()
    assert cb.feature_matrix is not None
```

### Integration Tests

```python
# Test recommendation pipeline
def test_recommendation_pipeline():
    engine = HybridRecommendationEngine()
    result = engine.get_recommendations("test_user", 5)
    assert len(result.recommendations) == 5
    assert result.processing_time_ms > 0

# Test API endpoints
def test_api_endpoints():
    app = create_recommendation_app()
    client = app.test_client()
    
    response = client.get('/api/recommendations?user_id=test_user')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'recommendations' in data
```

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5001

CMD ["python", "recommendation_api.py"]
```

### Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///recommendations.db

# API Configuration
FLASK_ENV=production
SECRET_KEY=your-secret-key

# Recommendation System
RECOMMENDATION_CACHE_DURATION=30
REALTIME_UPDATE_INTERVAL=30
MONITORING_COLLECTION_INTERVAL=60
```

### Production Considerations

- **Load Balancing**: Use load balancer for API endpoints
- **Database Scaling**: Consider PostgreSQL for production workloads
- **Monitoring**: Set up comprehensive monitoring and alerting
- **Security**: Implement proper authentication and authorization
- **Backup**: Regular database backups and configuration backups

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the API examples

## Changelog

### Version 1.0.0
- Initial release of the advanced recommendation system
- Complete implementation of all core components
- REST API with comprehensive endpoints
- A/B testing framework
- Performance monitoring system
- Real-time recommendation capabilities
