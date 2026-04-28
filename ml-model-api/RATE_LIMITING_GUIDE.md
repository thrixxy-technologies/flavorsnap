# Advanced API Rate Limiting Guide for FlavorSnap

This guide provides comprehensive documentation for the advanced rate limiting system implemented in FlavorSnap ML API.

## Overview

The advanced rate limiting system provides sophisticated API rate limiting with the following features:

- **User-based rate limiting** with different tiers (Free, Basic, Premium, Enterprise, Admin)
- **Burst capacity handling** for traffic spikes
- **Rate limit analytics** and monitoring
- **Dynamic limit adjustment** based on system load
- **Premium user bypass** functionality
- **Rate limit monitoring** with alerts
- **Graceful degradation** under high load

## Architecture

### Core Components

1. **security_config.py** - Main rate limiting framework
2. **api_endpoints.py** - Rate-limited API endpoints
3. **cache_manager.py** - Rate limit state caching
4. **monitoring.py** - Rate limit monitoring integration

### Rate Limiting Strategies

The system supports multiple rate limiting strategies:

- **Token Bucket** (default) - Allows bursts up to capacity
- **Sliding Window** - Fixed time window with sliding counts
- **Fixed Window** - Fixed time window with reset
- **Leaky Bucket** - Smooths out request rate

## User Types and Limits

### Default Limits

| User Type | Requests/Minute | Requests/Hour | Requests/Day | Burst Capacity | Bypass Allowed |
|-----------|-----------------|---------------|--------------|----------------|----------------|
| Free      | 10              | 100           | 500          | 5              | No             |
| Basic     | 30              | 500           | 2,000        | 10             | No             |
| Premium   | 100             | 2,000         | 10,000       | 20             | Yes            |
| Enterprise| 500             | 10,000        | 100,000      | 50             | Yes            |
| Admin     | 1,000           | 50,000        | 1,000,000    | 100            | Yes            |

### Endpoint-Specific Limits

Different endpoints have their own rate limits:

- **Predict API** - Stricter limits for ML processing
- **Batch API** - Moderate limits for batch operations
- **Analytics API** - Higher limits for monitoring
- **Queue Status** - Highest limits for operational needs

## API Usage

### User Identification

The system identifies users through several methods:

#### Headers

```http
X-User-ID: user123
X-User-Type: premium
X-API-Key: premium_abcdef123456789
X-Rate-Limit-Bypass: true
```

#### API Key Prefixes

- `ent_*` - Enterprise users
- `premium_*` - Premium users  
- `basic_*` - Basic users

#### IP-based Identification

If no user ID is provided, the system falls back to IP-based rate limiting.

### Rate Limit Response Headers

All API responses include rate limit information:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 2023-12-01T12:00:00Z
X-User-Type: premium
X-RateLimit-Allowed: true
```

### Error Responses

When rate limits are exceeded:

```json
{
  "error": "Rate limit exceeded",
  "message": "Rate limit for predict exceeded. Try again in 60 seconds.",
  "endpoint": "predict",
  "retry_after": 60,
  "limit": 100,
  "remaining": 0,
  "user_type": "premium",
  "reset_time": "2023-12-01T12:00:00Z"
}
```

## Configuration

### Basic Configuration

```yaml
rate_limiting:
  enabled: true
  default_strategy: "token_bucket"
  cleanup_interval: 300
  max_events: 100000
```

### User Type Configuration

```yaml
rate_limiting:
  user_types:
    premium:
      requests_per_minute: 100
      requests_per_hour: 2000
      requests_per_day: 10000
      burst_capacity: 20
      strategy: "token_bucket"
      bypass_allowed: true
      priority_weight: 1.5
```

### Dynamic Adjustment

```yaml
rate_limiting:
  dynamic_adjustment:
    enabled: true
    load_threshold_high: 0.8
    load_threshold_low: 0.3
    adjustment_factor_high: 0.95
    adjustment_factor_low: 1.05
    min_load_factor: 0.5
    max_load_factor: 2.0
```

## Advanced Features

### Dynamic Limit Adjustment

The system automatically adjusts rate limits based on system load:

- **High Load (>80%)** - Gradually reduces limits
- **Low Load (<30%)** - Gradually increases limits
- **Adjustment Range** - 50% to 200% of base limits

### Burst Capacity

Users can exceed their normal rate limits temporarily using burst capacity:

- Burst tokens refill at the normal rate
- Burst capacity is per user, not shared
- Premium users have higher burst capacity

### Premium Bypass

Premium and Enterprise users can bypass rate limits:

```http
X-Rate-Limit-Bypass: true
X-API-Key: premium_abcdef123456789
```

### Graceful Degradation

Under high system load, the system provides graceful degradation:

- **Critical Load (>95%)** - Service unavailable with fallback response
- **High Load (>85%)** - Reduced functionality with degradation headers
- **Normal Load** - Full functionality

```http
X-System-Load: 0.87
X-Service-Degraded: true
```

## Monitoring and Analytics

### Rate Limit Analytics

Get comprehensive analytics:

```bash
GET /api/v1/analytics/rate-limits?hours=24
```

Response:

```json
{
  "rate_limit_analytics": {
    "period_hours": 24,
    "total_requests": 10000,
    "blocked_requests": 150,
    "block_rate": 1.5,
    "unique_users": 500,
    "unique_ips": 450,
    "top_endpoints": [
      {"endpoint": "predict", "count": 8000},
      {"endpoint": "queue_status", "count": 1500}
    ],
    "user_type_distribution": {
      "free": 2000,
      "basic": 3000,
      "premium": 4000,
      "enterprise": 1000
    }
  },
  "dynamic_adjustments": {
    "premium": {
      "current_load_factor": 0.95,
      "last_adjustment": "2023-12-01T11:30:00Z"
    }
  },
  "active_clients": 450,
  "blocked_clients": 25
}
```

### User-Specific Analytics

```bash
GET /api/v1/analytics/user/user123?hours=24
```

### Monitoring Integration

Rate limiting metrics are automatically integrated with the monitoring system:

- Rate limit violation alerts
- Blocked user alerts
- Bypass usage monitoring
- Dynamic adjustment tracking

## API Endpoints

### Rate-Limited Endpoints

#### Predict API
```bash
POST /api/v1/predict
Content-Type: multipart/form-data
X-User-Type: premium
X-API-Key: premium_abcdef123456789

# Image file upload
```

#### Batch API
```bash
POST /api/v1/batch
Content-Type: multipart/form-data
X-User-Type: enterprise

# Multiple image files
```

#### Analytics API
```bash
GET /api/v1/analytics/rate-limits
GET /api/v1/analytics/user/{user_id}
```

#### Queue Status API
```bash
GET /api/v1/queue/status
GET /api/v1/task/{task_id}
```

### Admin Endpoints

#### Unblock User
```bash
POST /api/v1/admin/unblock-user/{user_id}
X-User-Type: admin
```

#### Enhanced Health Check
```bash
GET /api/v1/health/enhanced
```

## Implementation Details

### Token Bucket Algorithm

The token bucket implementation works as follows:

1. **Bucket Capacity** - Maximum tokens (burst capacity)
2. **Refill Rate** - Tokens added per second
3. **Token Consumption** - One token per request
4. **Burst Handling** - Allow consumption up to capacity

### State Management

Rate limit state is managed through:

- **In-memory state** for active users
- **Cache integration** for persistence
- **Background cleanup** for expired states
- **Distributed support** via Redis

### Performance Considerations

- **Lock-free operations** where possible
- **Efficient data structures** (deques, dicts)
- **Background cleanup** to prevent memory leaks
- **Cache integration** for performance

## Security Considerations

### IP-based Limitations

- **IP spoofing protection** via trusted proxies
- **IP whitelisting** for bypassing
- **IP blacklisting** for malicious actors
- **Geographic considerations** if needed

### API Key Security

- **Key rotation** support
- **Key prefixing** for user type identification
- **Key revocation** capabilities
- **Secure storage** recommendations

### Bypass Protection

- **Audit logging** for bypass usage
- **Rate limit monitoring** for abuse
- **Admin oversight** for bypass permissions
- **Automatic blocking** for excessive violations

## Troubleshooting

### Common Issues

#### Rate Limit Not Working

1. Check if rate limiting is enabled in configuration
2. Verify user identification headers
3. Check API key prefixes
4. Review monitoring logs

#### High False Positives

1. Adjust burst capacity
2. Review dynamic adjustment settings
3. Check system load metrics
4. Verify user type detection

#### Performance Issues

1. Monitor cleanup interval
2. Check cache performance
3. Review analytics retention
4. Optimize configuration

### Debug Mode

Enable debug logging:

```yaml
logging:
  log_rate_limit_events: true
  log_violations: true
  log_bypass_usage: true
  log_dynamic_adjustments: true
  log_level: "DEBUG"
```

## Best Practices

### Configuration

1. **Start conservative** with rate limits
2. **Monitor usage patterns** before increasing
3. **Use burst capacity** for traffic spikes
4. **Enable dynamic adjustment** for scalability

### User Management

1. **Implement proper user authentication**
2. **Use API keys** for programmatic access
3. **Monitor bypass usage** for abuse
4. **Regularly review user analytics**

### Monitoring

1. **Set up alerts** for high violation rates
2. **Monitor system load** continuously
3. **Track user growth** and adjust limits
4. **Review analytics** regularly

## Migration Guide

### From Simple Rate Limiting

1. **Install dependencies** (psutil, etc.)
2. **Update configuration** with new settings
3. **Deploy security_config.py**
4. **Update API endpoints** with decorators
5. **Monitor and adjust** limits

### Configuration Migration

```yaml
# Old configuration
rate_limit:
  requests_per_minute: 100

# New configuration
rate_limiting:
  user_types:
    basic:
      requests_per_minute: 100
      burst_capacity: 10
      strategy: "token_bucket"
```

## API Reference

### Rate Limit Decorators

```python
from security_config import rate_limit, endpoint_rate_limit

# Basic rate limiting
@app.route('/endpoint')
@rate_limit()
def endpoint():
    return jsonify({'message': 'OK'})

# Endpoint-specific rate limiting
@app.route('/predict')
@endpoint_rate_limit('predict')
def predict():
    return jsonify({'result': 'success'})
```

### Graceful Degradation

```python
from api_endpoints import graceful_degradation

@app.route('/endpoint')
@graceful_degradation(
    fallback_response={'message': 'Service busy'},
    fallback_status=503
)
def endpoint():
    return jsonify({'result': 'success'})
```

### Rate Limiter Access

```python
from security_config import get_rate_limiter

# Get rate limiter instance
limiter = get_rate_limiter()

# Check rate limit manually
allowed, info = limiter.check_rate_limit(request, 'endpoint')

# Get analytics
analytics = limiter.get_analytics(hours=24)

# Unblock user
success = limiter.unblock_user('user123')
```

## Testing

### Unit Testing

```python
import pytest
from security_config import AdvancedRateLimiter

def test_rate_limiting():
    limiter = AdvancedRateLimiter()
    
    # Mock request
    class MockRequest:
        def __init__(self):
            self.headers = {'X-User-Type': 'premium'}
            self.remote_addr = '127.0.0.1'
    
    request = MockRequest()
    
    # Test rate limiting
    allowed, info = limiter.check_rate_limit(request, 'predict')
    assert allowed == True
    assert 'remaining' in info
```

### Load Testing

```python
import asyncio
import aiohttp

async def test_rate_limits():
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(150):  # Exceed rate limit
            task = session.post('/api/v1/predict', data=image_data)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check that some requests are blocked
        blocked_count = sum(1 for r in responses if getattr(r, 'status', 200) == 429)
        assert blocked_count > 0
```

## Support

For issues with the rate limiting system:

1. **Check logs** for error messages
2. **Review configuration** for typos
3. **Monitor system metrics** for performance issues
4. **Consult this guide** for common solutions

## Version History

- **v1.0** - Initial implementation with basic rate limiting
- **v2.0** - Advanced features: dynamic adjustment, analytics, monitoring
- **v2.1** - Enhanced graceful degradation and bypass functionality
- **v2.2** - Performance optimizations and cache integration
