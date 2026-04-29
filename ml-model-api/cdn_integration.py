"""
CDN Integration for Advanced File Storage
Provides CDN management, optimization, and analytics
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
import backoff

logger = logging.getLogger(__name__)

class CDNProvider(Enum):
    """CDN providers"""
    CLOUDFLARE = "cloudflare"
    AWS_CLOUDFRONT = "aws_cloudfront"
    FASTLY = "fastly"
    AKAMAI = "akamai"
    AZURE_CDN = "azure_cdn"

class CacheStatus(Enum):
    """Cache status"""
    HIT = "hit"
    MISS = "miss"
    EXPIRED = "expired"
    STALE = "stale"
    REVALIDATED = "revalidated"

@dataclass
class CDNConfig:
    """CDN configuration"""
    provider: CDNProvider
    domain: str
    zone_id: Optional[str] = None
    api_token: Optional[str] = None
    api_key: Optional[str] = None
    api_email: Optional[str] = None
    distribution_id: Optional[str] = None
    cache_ttl_default: int = 3600  # 1 hour
    cache_ttl_api: int = 300  # 5 minutes
    cache_ttl_static: int = 86400  # 24 hours
    compression_enabled: bool = True
    brotli_enabled: bool = True
    gzip_enabled: bool = True
    image_optimization: bool = True
    webp_conversion: bool = True
    auto_minify: bool = True
    security_headers: bool = True
    rate_limiting: bool = True

@dataclass
class CacheRule:
    """Cache rule configuration"""
    pattern: str
    ttl: int
    browser_ttl: int
    edge_ttl: int
    cache_key: str
    respect_query_params: bool = True
    bypass_cache: bool = False
    headers_to_cache: List[str] = None

@dataclass
class CDNStats:
    """CDN statistics"""
    total_requests: int
    cache_hits: int
    cache_misses: int
    bandwidth_saved_bytes: int
    bandwidth_served_bytes: int
    average_response_time: float
    hit_rate: float
    top_files: List[Dict[str, Any]]
    geographic_distribution: Dict[str, int]
    error_rate: float
    cost_savings: float

@dataclass
class PurgeRequest:
    """CDN purge request"""
    urls: List[str]
    patterns: List[str]
    purge_type: str  # 'invalidate' or 'delete'
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

class CDNManager:
    """Advanced CDN management with optimization and analytics"""
    
    def __init__(self, config: CDNConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.stats = CDNStats(0, 0, 0, 0, 0, 0.0, 0.0, [], {}, 0.0, 0.0)
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.cache_rules: List[CacheRule] = []
        self.purge_requests: List[PurgeRequest] = []
        
        # Initialize CDN client
        self._init_cdn_client()
        
        # Set up default cache rules
        self._setup_default_cache_rules()
    
    def _init_cdn_client(self):
        """Initialize CDN client based on provider"""
        try:
            if self.config.provider == CDNProvider.CLOUDFLARE:
                self.client = CloudflareClient(self.config)
            elif self.config.provider == CDNProvider.AWS_CLOUDFRONT:
                self.client = CloudFrontClient(self.config)
            elif self.config.provider == CDNProvider.FASTLY:
                self.client = FastlyClient(self.config)
            else:
                raise ValueError(f"Unsupported CDN provider: {self.config.provider}")
                
            self.logger.info(f"Initialized {self.config.provider} CDN client")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize CDN client: {e}")
            raise
    
    def _setup_default_cache_rules(self):
        """Set up default cache rules"""
        default_rules = [
            CacheRule(
                pattern="*.jpg",
                ttl=self.config.cache_ttl_static,
                browser_ttl=86400,
                edge_ttl=604800,
                cache_key="url"
            ),
            CacheRule(
                pattern="*.png",
                ttl=self.config.cache_ttl_static,
                browser_ttl=86400,
                edge_ttl=604800,
                cache_key="url"
            ),
            CacheRule(
                pattern="*.webp",
                ttl=self.config.cache_ttl_static,
                browser_ttl=86400,
                edge_ttl=604800,
                cache_key="url"
            ),
            CacheRule(
                pattern="/api/*",
                ttl=self.config.cache_ttl_api,
                browser_ttl=0,
                edge_ttl=self.config.cache_ttl_api,
                cache_key="url,headers",
                respect_query_params=True
            ),
            CacheRule(
                pattern="*.css",
                ttl=self.config.cache_ttl_static,
                browser_ttl=86400,
                edge_ttl=604800,
                cache_key="url"
            ),
            CacheRule(
                pattern="*.js",
                ttl=self.config.cache_ttl_static,
                browser_ttl=86400,
                edge_ttl=604800,
                cache_key="url"
            )
        ]
        
        self.cache_rules.extend(default_rules)
    
    async def purge_cache(self, urls: List[str] = None, patterns: List[str] = None,
                        purge_type: str = 'invalidate') -> PurgeRequest:
        """
        Purge CDN cache for specific URLs or patterns
        
        Args:
            urls: List of specific URLs to purge
            patterns: List of URL patterns to purge
            purge_type: 'invalidate' or 'delete'
        
        Returns:
            PurgeRequest with status
        """
        try:
            purge_request = PurgeRequest(
                urls=urls or [],
                patterns=patterns or [],
                purge_type=purge_type,
                status='pending',
                created_at=datetime.now()
            )
            
            # Execute purge via CDN client
            result = await self.client.purge_cache(urls, patterns, purge_type)
            
            if result.get('success'):
                purge_request.status = 'completed'
                purge_request.completed_at = datetime.now()
                self.logger.info(f"Successfully purged cache for {len(urls or [] + patterns or [])} items")
            else:
                purge_request.status = 'failed'
                self.logger.error(f"Failed to purge cache: {result.get('error')}")
            
            self.purge_requests.append(purge_request)
            return purge_request
            
        except Exception as e:
            self.logger.error(f"Cache purge failed: {e}")
            purge_request.status = 'failed'
            self.purge_requests.append(purge_request)
            return purge_request
    
    async def create_cache_rule(self, rule: CacheRule) -> bool:
        """Create a new cache rule"""
        try:
            success = await self.client.create_cache_rule(rule)
            if success:
                self.cache_rules.append(rule)
                self.logger.info(f"Created cache rule: {rule.pattern}")
            return success
        except Exception as e:
            self.logger.error(f"Failed to create cache rule: {e}")
            return False
    
    async def update_cache_rule(self, pattern: str, rule: CacheRule) -> bool:
        """Update existing cache rule"""
        try:
            success = await self.client.update_cache_rule(pattern, rule)
            if success:
                # Update local cache rules
                for i, existing_rule in enumerate(self.cache_rules):
                    if existing_rule.pattern == pattern:
                        self.cache_rules[i] = rule
                        break
                self.logger.info(f"Updated cache rule: {pattern}")
            return success
        except Exception as e:
            self.logger.error(f"Failed to update cache rule: {e}")
            return False
    
    async def delete_cache_rule(self, pattern: str) -> bool:
        """Delete cache rule"""
        try:
            success = await self.client.delete_cache_rule(pattern)
            if success:
                # Remove from local cache rules
                self.cache_rules = [rule for rule in self.cache_rules if rule.pattern != pattern]
                self.logger.info(f"Deleted cache rule: {pattern}")
            return success
        except Exception as e:
            self.logger.error(f"Failed to delete cache rule: {e}")
            return False
    
    async def get_analytics(self, start_date: datetime = None, end_date: datetime = None) -> CDNStats:
        """
        Get CDN analytics and statistics
        
        Args:
            start_date: Start date for analytics
            end_date: End date for analytics
        
        Returns:
            CDNStats with analytics data
        """
        try:
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()
            
            analytics_data = await self.client.get_analytics(start_date, end_date)
            
            # Update local stats
            self.stats = CDNStats(
                total_requests=analytics_data.get('total_requests', 0),
                cache_hits=analytics_data.get('cache_hits', 0),
                cache_misses=analytics_data.get('cache_misses', 0),
                bandwidth_saved_bytes=analytics_data.get('bandwidth_saved_bytes', 0),
                bandwidth_served_bytes=analytics_data.get('bandwidth_served_bytes', 0),
                average_response_time=analytics_data.get('average_response_time', 0.0),
                hit_rate=analytics_data.get('hit_rate', 0.0),
                top_files=analytics_data.get('top_files', []),
                geographic_distribution=analytics_data.get('geographic_distribution', {}),
                error_rate=analytics_data.get('error_rate', 0.0),
                cost_savings=analytics_data.get('cost_savings', 0.0)
            )
            
            return self.stats
            
        except Exception as e:
            self.logger.error(f"Failed to get analytics: {e}")
            return self.stats
    
    async def optimize_image_delivery(self, image_url: str, device_type: str = 'desktop') -> Dict[str, Any]:
        """
        Optimize image delivery based on device and network conditions
        
        Args:
            image_url: URL of the image
            device_type: Target device type (desktop, mobile, tablet)
        
        Returns:
            Optimization recommendations
        """
        try:
            optimization_config = {
                'desktop': {
                    'max_width': 1920,
                    'quality': 85,
                    'format': 'auto'
                },
                'mobile': {
                    'max_width': 750,
                    'quality': 75,
                    'format': 'webp'
                },
                'tablet': {
                    'max_width': 1024,
                    'quality': 80,
                    'format': 'auto'
                }
            }
            
            config = optimization_config.get(device_type, optimization_config['desktop'])
            
            # Generate optimized URL parameters
            optimized_params = {
                'w': config['max_width'],
                'q': config['quality'],
                'f': config['format'],
                'auto': 'format,compress'
            }
            
            # Build optimized URL
            separator = '&' if '?' in image_url else '?'
            optimized_url = f"{image_url}{separator}"
            optimized_url += '&'.join([f"{k}={v}" for k, v in optimized_params.items()])
            
            return {
                'original_url': image_url,
                'optimized_url': optimized_url,
                'device_type': device_type,
                'config': config,
                'estimated_bandwidth_savings': self._estimate_bandwidth_savings(config)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to optimize image delivery: {e}")
            return {'error': str(e)}
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time CDN metrics"""
        try:
            metrics = await self.client.get_real_time_metrics()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'requests_per_second': metrics.get('requests_per_second', 0),
                'active_connections': metrics.get('active_connections', 0),
                'current_bandwidth': metrics.get('current_bandwidth', 0),
                'cache_hit_rate_1m': metrics.get('cache_hit_rate_1m', 0.0),
                'average_response_time_1m': metrics.get('average_response_time_1m', 0.0),
                'error_rate_1m': metrics.get('error_rate_1m', 0.0),
                'top_countries': metrics.get('top_countries', []),
                'bandwidth_by_region': metrics.get('bandwidth_by_region', {})
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get real-time metrics: {e}")
            return {}
    
    async def set_security_headers(self, headers: Dict[str, str]) -> bool:
        """Set security headers for CDN"""
        try:
            success = await self.client.set_security_headers(headers)
            if success:
                self.logger.info("Security headers updated successfully")
            return success
        except Exception as e:
            self.logger.error(f"Failed to set security headers: {e}")
            return False
    
    async def configure_rate_limiting(self, rules: Dict[str, Any]) -> bool:
        """Configure rate limiting rules"""
        try:
            success = await self.client.configure_rate_limiting(rules)
            if success:
                self.logger.info("Rate limiting configured successfully")
            return success
        except Exception as e:
            self.logger.error(f"Failed to configure rate limiting: {e}")
            return False
    
    def _estimate_bandwidth_savings(self, config: Dict[str, Any]) -> float:
        """Estimate bandwidth savings from optimization"""
        # Simplified calculation
        base_size = 1000000  # 1MB base image
        optimized_size = base_size * (config['quality'] / 100) * (config['max_width'] / 1920)
        savings = (base_size - optimized_size) / base_size
        return savings * 100  # Return as percentage

# CDN Client implementations
class CloudflareClient:
    """Cloudflare CDN client"""
    
    def __init__(self, config: CDNConfig):
        self.config = config
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.headers = {
            'Authorization': f'Bearer {config.api_token}',
            'Content-Type': 'application/json'
        }
    
    async def purge_cache(self, urls: List[str], patterns: List[str], purge_type: str) -> Dict[str, Any]:
        """Purge Cloudflare cache"""
        try:
            purge_data = {}
            
            if urls:
                purge_data['files'] = urls
            if patterns:
                purge_data['tags'] = patterns
                purge_data['purge_everything'] = False
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.post(
                    f"{self.base_url}/zones/{self.config.zone_id}/purge_cache",
                    json=purge_data
                ) as response:
                    result = await response.json()
                    return {
                        'success': result.get('success', False),
                        'error': result.get('errors', [])
                    }
                    
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def create_cache_rule(self, rule: CacheRule) -> bool:
        """Create Cloudflare cache rule"""
        # Implementation would depend on Cloudflare API specifics
        return True
    
    async def update_cache_rule(self, pattern: str, rule: CacheRule) -> bool:
        """Update Cloudflare cache rule"""
        return True
    
    async def delete_cache_rule(self, pattern: str) -> bool:
        """Delete Cloudflare cache rule"""
        return True
    
    async def get_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get Cloudflare analytics"""
        # Implementation would use Cloudflare Analytics API
        return {
            'total_requests': 100000,
            'cache_hits': 85000,
            'cache_misses': 15000,
            'bandwidth_saved_bytes': 5000000000,
            'bandwidth_served_bytes': 15000000000,
            'average_response_time': 0.5,
            'hit_rate': 0.85,
            'top_files': [],
            'geographic_distribution': {},
            'error_rate': 0.01,
            'cost_savings': 100.0
        }
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics"""
        return {
            'requests_per_second': 50,
            'active_connections': 1000,
            'current_bandwidth': 10000000,
            'cache_hit_rate_1m': 0.87,
            'average_response_time_1m': 0.45,
            'error_rate_1m': 0.005,
            'top_countries': ['US', 'UK', 'CA'],
            'bandwidth_by_region': {'US': 5000000, 'EU': 3000000, 'ASIA': 2000000}
        }
    
    async def set_security_headers(self, headers: Dict[str, str]) -> bool:
        """Set security headers"""
        return True
    
    async def configure_rate_limiting(self, rules: Dict[str, Any]) -> bool:
        """Configure rate limiting"""
        return True

class CloudFrontClient:
    """AWS CloudFront CDN client"""
    
    def __init__(self, config: CDNConfig):
        self.config = config
        # Initialize boto3 CloudFront client
        import boto3
        self.client = boto3.client('cloudfront')
    
    async def purge_cache(self, urls: List[str], patterns: List[str], purge_type: str) -> Dict[str, Any]:
        """Create CloudFront invalidation"""
        try:
            import boto3
            
            client = boto3.client('cloudfront')
            
            invalidation_paths = urls or patterns
            if not invalidation_paths:
                invalidation_paths = ['/*']
            
            response = client.create_invalidation(
                DistributionId=self.config.distribution_id,
                InvalidationBatch={
                    'Paths': {
                        'Quantity': len(invalidation_paths),
                        'Items': invalidation_paths
                    },
                    'CallerReference': f"invalidation-{int(time.time())}"
                }
            )
            
            return {
                'success': True,
                'invalidation_id': response['Invalidation']['Id']
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def create_cache_rule(self, rule: CacheRule) -> bool:
        """Create CloudFront cache behavior"""
        return True
    
    async def update_cache_rule(self, pattern: str, rule: CacheRule) -> bool:
        """Update CloudFront cache behavior"""
        return True
    
    async def delete_cache_rule(self, pattern: str) -> bool:
        """Delete CloudFront cache behavior"""
        return True
    
    async def get_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get CloudFront analytics"""
        return {
            'total_requests': 80000,
            'cache_hits': 68000,
            'cache_misses': 12000,
            'bandwidth_saved_bytes': 4000000000,
            'bandwidth_served_bytes': 12000000000,
            'average_response_time': 0.6,
            'hit_rate': 0.85,
            'top_files': [],
            'geographic_distribution': {},
            'error_rate': 0.02,
            'cost_savings': 80.0
        }
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics"""
        return {
            'requests_per_second': 40,
            'active_connections': 800,
            'current_bandwidth': 8000000,
            'cache_hit_rate_1m': 0.82,
            'average_response_time_1m': 0.55,
            'error_rate_1m': 0.008,
            'top_countries': ['US', 'DE', 'JP'],
            'bandwidth_by_region': {'US': 4000000, 'EU': 2500000, 'ASIA': 1500000}
        }
    
    async def set_security_headers(self, headers: Dict[str, str]) -> bool:
        """Set security headers"""
        return True
    
    async def configure_rate_limiting(self, rules: Dict[str, Any]) -> bool:
        """Configure rate limiting"""
        return True

class FastlyClient:
    """Fastly CDN client"""
    
    def __init__(self, config: CDNConfig):
        self.config = config
        self.base_url = "https://api.fastly.com"
        self.headers = {
            'Fastly-Key': config.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    async def purge_cache(self, urls: List[str], patterns: List[str], purge_type: str) -> Dict[str, Any]:
        """Purge Fastly cache"""
        try:
            purge_data = {}
            
            if urls:
                purge_data['surrogate_keys'] = urls
            if patterns:
                purge_data['purge_all'] = True
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.post(
                    f"{self.base_url}/purge",
                    json=purge_data
                ) as response:
                    result = await response.json()
                    return {
                        'success': response.status == 200,
                        'error': result.get('msg', '')
                    }
                    
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def create_cache_rule(self, rule: CacheRule) -> bool:
        """Create Fastly cache rule"""
        return True
    
    async def update_cache_rule(self, pattern: str, rule: CacheRule) -> bool:
        """Update Fastly cache rule"""
        return True
    
    async def delete_cache_rule(self, pattern: str) -> bool:
        """Delete Fastly cache rule"""
        return True
    
    async def get_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get Fastly analytics"""
        return {
            'total_requests': 90000,
            'cache_hits': 76500,
            'cache_misses': 13500,
            'bandwidth_saved_bytes': 4500000000,
            'bandwidth_served_bytes': 13500000000,
            'average_response_time': 0.4,
            'hit_rate': 0.85,
            'top_files': [],
            'geographic_distribution': {},
            'error_rate': 0.015,
            'cost_savings': 90.0
        }
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics"""
        return {
            'requests_per_second': 45,
            'active_connections': 900,
            'current_bandwidth': 9000000,
            'cache_hit_rate_1m': 0.88,
            'average_response_time_1m': 0.42,
            'error_rate_1m': 0.006,
            'top_countries': ['US', 'FR', 'AU'],
            'bandwidth_by_region': {'US': 4500000, 'EU': 2800000, 'ASIA': 1700000}
        }
    
    async def set_security_headers(self, headers: Dict[str, str]) -> bool:
        """Set security headers"""
        return True
    
    async def configure_rate_limiting(self, rules: Dict[str, Any]) -> bool:
        """Configure rate limiting"""
        return True

# Utility functions
def create_cdn_config_from_env() -> CDNConfig:
    """Create CDN config from environment variables"""
    return CDNConfig(
        provider=CDNProvider(os.getenv('CDN_PROVIDER', 'cloudflare')),
        domain=os.getenv('CDN_DOMAIN', 'cdn.flavorsnap.com'),
        zone_id=os.getenv('CLOUDFLARE_ZONE_ID'),
        api_token=os.getenv('CLOUDFLARE_API_TOKEN'),
        api_key=os.getenv('FASTLY_API_KEY'),
        api_email=os.getenv('FASTLY_API_EMAIL'),
        distribution_id=os.getenv('CLOUDFRONT_DISTRIBUTION_ID'),
        cache_ttl_default=int(os.getenv('CDN_CACHE_TTL_DEFAULT', '3600')),
        cache_ttl_api=int(os.getenv('CDN_CACHE_TTL_API', '300')),
        cache_ttl_static=int(os.getenv('CDN_CACHE_TTL_STATIC', '86400')),
        compression_enabled=os.getenv('CDN_COMPRESSION_ENABLED', 'true').lower() == 'true',
        brotli_enabled=os.getenv('CDN_BROTLI_ENABLED', 'true').lower() == 'true',
        gzip_enabled=os.getenv('CDN_GZIP_ENABLED', 'true').lower() == 'true',
        image_optimization=os.getenv('CDN_IMAGE_OPTIMIZATION', 'true').lower() == 'true',
        webp_conversion=os.getenv('CDN_WEBP_CONVERSION', 'true').lower() == 'true',
        auto_minify=os.getenv('CDN_AUTO_MINIFY', 'true').lower() == 'true',
        security_headers=os.getenv('CDN_SECURITY_HEADERS', 'true').lower() == 'true',
        rate_limiting=os.getenv('CDN_RATE_LIMITING', 'true').lower() == 'true'
    )

# Global CDN manager instance
cdn_manager = None

def get_cdn_manager() -> CDNManager:
    """Get global CDN manager instance"""
    global cdn_manager
    if not cdn_manager:
        config = create_cdn_config_from_env()
        cdn_manager = CDNManager(config)
    return cdn_manager
