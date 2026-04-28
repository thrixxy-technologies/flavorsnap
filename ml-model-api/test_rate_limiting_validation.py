#!/usr/bin/env python3
"""
Simple test script to validate the comprehensive rate limiting implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from security_config import SecurityConfig, RateLimitManager, APIKeyManager

def test_tiered_api_keys():
    """Test tiered API key generation"""
    print("=== Testing Tiered API Key Generation ===")
    
    # Generate keys for each tier
    free_key = APIKeyManager.generate_tiered_api_key('free')
    premium_key = APIKeyManager.generate_tiered_api_key('premium')
    enterprise_key = APIKeyManager.generate_tiered_api_key('enterprise')
    
    print(f"Free key: {free_key['api_key'][:20]}...")
    print(f"Premium key: {premium_key['api_key'][:20]}...")
    print(f"Enterprise key: {enterprise_key['api_key'][:20]}...")
    
    # Verify key prefixes
    assert free_key['api_key'].startswith('free_'), "Free key should start with 'free_'"
    assert premium_key['api_key'].startswith('prem_'), "Premium key should start with 'prem_'"
    assert enterprise_key['api_key'].startswith('ent_'), "Enterprise key should start with 'ent_'"
    
    print("API key generation working correctly")

def test_tier_detection():
    """Test API key tier detection"""
    print("\n=== Testing Tier Detection ===")
    
    # Test valid keys
    free_key = 'free_test1234567890123456789012345678'
    premium_key = 'prem_test1234567890123456789012345678'
    enterprise_key = 'ent_test1234567890123456789012345678'
    invalid_key = 'invalid_key1234567890123456789012345678'
    
    assert RateLimitManager.get_api_key_tier(free_key) == 'free', "Should detect free tier"
    assert RateLimitManager.get_api_key_tier(premium_key) == 'premium', "Should detect premium tier"
    assert RateLimitManager.get_api_key_tier(enterprise_key) == 'enterprise', "Should detect enterprise tier"
    assert RateLimitManager.get_api_key_tier(invalid_key) == 'free', "Invalid key should default to free"
    assert RateLimitManager.get_api_key_tier(None) == 'default', "No key should default to default"
    
    print("Tier detection working correctly")

def test_rate_limit_retrieval():
    """Test rate limit retrieval for different tiers and endpoints"""
    print("\n=== Testing Rate Limit Retrieval ===")
    
    free_key = 'free_test1234567890123456789012345678'
    premium_key = 'prem_test1234567890123456789012345678'
    enterprise_key = 'ent_test1234567890123456789012345678'
    
    # Test predict endpoint limits
    free_predict_limit = RateLimitManager.get_rate_limit_for_endpoint('predict', free_key)
    premium_predict_limit = RateLimitManager.get_rate_limit_for_endpoint('predict', premium_key)
    enterprise_predict_limit = RateLimitManager.get_rate_limit_for_endpoint('predict', enterprise_key)
    
    assert free_predict_limit == '10 per minute', f"Free predict limit should be '10 per minute', got '{free_predict_limit}'"
    assert premium_predict_limit == '100 per minute', f"Premium predict limit should be '100 per minute', got '{premium_predict_limit}'"
    assert enterprise_predict_limit == '500 per minute', f"Enterprise predict limit should be '500 per minute', got '{enterprise_predict_limit}'"
    
    # Test dashboard endpoint limits
    free_dashboard_limit = RateLimitManager.get_rate_limit_for_endpoint('performance_dashboard', free_key)
    premium_dashboard_limit = RateLimitManager.get_rate_limit_for_endpoint('performance_dashboard', premium_key)
    
    assert free_dashboard_limit == '20 per minute', f"Free dashboard limit should be '20 per minute', got '{free_dashboard_limit}'"
    assert premium_dashboard_limit == '100 per minute', f"Premium dashboard limit should be '100 per minute', got '{premium_dashboard_limit}'"
    
    # Test fixed limits (not tier-based)
    api_info_limit = RateLimitManager.get_rate_limit_for_endpoint('api_info', free_key)
    health_limit = RateLimitManager.get_rate_limit_for_endpoint('health_check', free_key)
    
    assert api_info_limit == '30 per minute', f"API info limit should be '30 per minute', got '{api_info_limit}'"
    assert health_limit == '1000 per hour', f"Health limit should be '1000 per hour', got '{health_limit}'"
    
    print("Rate limit retrieval working correctly")

def test_security_config():
    """Test security configuration"""
    print("\n=== Testing Security Configuration ===")
    
    # Test rate limit configurations
    rate_limits = SecurityConfig.RATE_LIMITS
    
    # Verify all required limits exist
    required_limits = [
        'default', 'health', 'api_info',
        'free_predict', 'free_upload', 'free_admin', 'free_dashboard',
        'premium_predict', 'premium_upload', 'premium_admin', 'premium_dashboard',
        'enterprise_predict', 'enterprise_upload', 'enterprise_admin', 'enterprise_dashboard'
    ]
    
    for limit in required_limits:
        assert limit in rate_limits, f"Missing rate limit configuration: {limit}"
    
    # Test API key tier configurations
    api_key_tiers = SecurityConfig.API_KEY_TIERS
    assert 'free' in api_key_tiers, "Missing free tier configuration"
    assert 'premium' in api_key_tiers, "Missing premium tier configuration"
    assert 'enterprise' in api_key_tiers, "Missing enterprise tier configuration"
    
    assert api_key_tiers['free']['prefix'] == 'free_', "Free tier prefix should be 'free_'"
    assert api_key_tiers['premium']['prefix'] == 'prem_', "Premium tier prefix should be 'prem_'"
    assert api_key_tiers['enterprise']['prefix'] == 'ent_', "Enterprise tier prefix should be 'ent_'"
    
    print("Security configuration working correctly")

def main():
    """Run all tests"""
    print("Testing Comprehensive Rate Limiting Implementation")
    print("=" * 50)
    
    try:
        test_tiered_api_keys()
        test_tier_detection()
        test_rate_limit_retrieval()
        test_security_config()
        
        print("\n" + "=" * 50)
        print("All tests passed!")
        print("\nRate Limiting Implementation Summary:")
        print("- Tier-based API keys with prefixes (free_, prem_, ent_)")
        print("- Different rate limits per tier:")
        print("  * Free: 10 requests/min for predict")
        print("  * Premium: 100 requests/min for predict")
        print("  * Enterprise: 500 requests/min for predict")
        print("- Fixed limits for public endpoints:")
        print("  * API info: 30 requests/min")
        print("  * Health check: 1000 requests/hour")
        print("- Comprehensive error handling with tier information")
        
        return 0
        
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
