# Security Implementation Guide

## Overview
This document outlines the comprehensive security measures implemented in the FlavorSnap backend API to protect against common web vulnerabilities and attacks.

## Implemented Security Features

### 1. Rate Limiting
- **General API**: 100 requests per minute per IP
- **Authentication endpoints**: 5 requests per 15 minutes per IP
- **Health checks**: Excluded from rate limiting
- **Headers**: Includes `RateLimit-*` headers for client-side handling

### 2. Input Validation and Sanitization
- **XSS Prevention**: DOMPurify sanitization for all string inputs
- **SQL Injection Prevention**: Parameterized queries and input sanitization
- **Validation Rules**: Comprehensive validation using express-validator
- **File Upload Validation**: MIME type, size, and format restrictions

### 3. Enhanced Security Headers
- **Content Security Policy**: Restricts resource loading sources
- **HSTS**: HTTP Strict Transport Security with preload
- **X-Frame-Options**: Prevents clickjacking attacks
- **X-Content-Type-Options**: Prevents MIME sniffing
- **Referrer Policy**: Controls referrer information leakage
- **X-XSS-Protection**: Enables browser XSS filtering

### 4. CORS Configuration
- **Origin Validation**: Whitelist-based origin checking
- **Environment-specific**: Different configurations for dev/prod
- **Credential Support**: Secure cookie handling
- **Preflight Caching**: 24-hour cache for OPTIONS requests

### 5. API Key Authentication (Production)
- **Production Only**: API key validation in production environment
- **Header-based**: Uses `X-API-Key` header
- **Secure Storage**: Environment variable configuration

### 6. JWT Authentication
- **Secure Tokens**: HMAC-SHA256 signing
- **Expiration**: 7-day token lifetime
- **User Context**: Request object augmentation
- **Error Handling**: Comprehensive token validation

## Configuration

### Environment Variables

```bash
# Security Configuration
API_KEY=your-production-api-key-change-this-in-production
PRODUCTION_FRONTEND_URLS=https://yourdomain.com,https://www.yourdomain.com
RATE_LIMIT_WINDOW_MS=60000
RATE_LIMIT_MAX_REQUESTS=100
AUTH_RATE_LIMIT_WINDOW_MS=900000
AUTH_RATE_LIMIT_MAX_REQUESTS=5

# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
JWT_EXPIRES_IN=7d
```

## Usage Examples

### API Key Usage (Production)
```bash
curl -X GET "https://api.flavorsnap.com/api/health" \
  -H "X-API-Key: your-production-api-key"
```

### JWT Authentication
```bash
# Login
curl -X POST "https://api.flavorsnap.com/api/users/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Use token
curl -X GET "https://api.flavorsnap.com/api/users/profile" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Security Best Practices

### Development
1. Never commit sensitive data to version control
2. Use strong, unique secrets for JWT and API keys
3. Regularly update dependencies
4. Enable security monitoring and logging

### Production
1. Use HTTPS exclusively
2. Implement proper secret management
3. Enable security headers
4. Monitor rate limiting and authentication failures
5. Regular security audits and penetration testing

### Monitoring
- Authentication failures
- Rate limiting violations
- Suspicious request patterns
- API key misuse
- Input validation failures

## Testing Security

### Rate Limiting Test
```bash
# Test rate limiting (should fail after 100 requests)
for i in {1..101}; do
  curl -X GET "http://localhost:5000/api/health"
done
```

### Input Validation Test
```bash
# Test XSS prevention
curl -X POST "http://localhost:5000/api/users/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"test<script>alert(1)</script>","password":"ValidPass123!"}'
```

### CORS Test
```bash
# Test CORS with invalid origin
curl -X GET "http://localhost:5000/api/health" \
  -H "Origin: https://malicious-site.com"
```

## Security Dependencies

- `helmet`: Security headers middleware
- `express-rate-limit`: Rate limiting implementation
- `express-validator`: Input validation
- `isomorphic-dompurify`: XSS prevention
- `bcryptjs`: Password hashing
- `jsonwebtoken`: JWT implementation
- `cors`: CORS configuration

## Vulnerability Mitigation

| Vulnerability | Mitigation |
|---------------|------------|
| XSS Attacks | DOMPurify sanitization, CSP headers |
| SQL Injection | Parameterized queries, input sanitization |
| CSRF Attacks | CORS configuration, same-site cookies |
| Rate Limiting Bypass | IP-based limiting, authentication-specific limits |
| Authentication Bypass | Secure JWT implementation, API key validation |
| Data Exposure | Security headers, referrer policy |
| Clickjacking | X-Frame-Options, CSP frame-ancestors |

## Compliance

- **OWASP Top 10**: Addresses major web security risks
- **GDPR**: Data protection through secure handling
- **SOC 2**: Security controls implementation
- **PCI DSS**: Payment card security (if applicable)

## Maintenance

1. **Regular Updates**: Keep security dependencies updated
2. **Audit Logs**: Monitor security events
3. **Penetration Testing**: Regular security assessments
4. **Code Reviews**: Security-focused code reviews
5. **Dependency Scanning**: Automated vulnerability scanning

## Incident Response

1. **Detection**: Monitor security alerts and anomalies
2. **Containment**: Isolate affected systems
3. **Investigation**: Analyze security breach
4. **Remediation**: Patch vulnerabilities
5. **Prevention**: Implement measures to prevent recurrence

For security issues or concerns, please contact the security team at security@flavorsnap.com.
