#!/usr/bin/env python3
"""
Advanced Health Checker for Load Balancer
Implements comprehensive health checking with multiple protocols and custom checks
"""

import asyncio
import aiohttp
import socket
import ssl
import time
import json
import logging
import subprocess
import psutil
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import xml.etree.ElementTree as ET
import dns.resolver
import redis
import pymongo
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthCheckType(Enum):
    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"
    PING = "ping"
    CUSTOM = "custom"
    DATABASE = "database"
    CACHE = "cache"
    DNS = "dns"

class HealthStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    WARNING = "warning"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    status: HealthStatus
    response_time: float
    message: str
    timestamp: float
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

@dataclass
class HealthCheckConfig:
    name: str
    type: HealthCheckType
    target: str
    port: Optional[int] = None
    path: str = "/health"
    method: str = "GET"
    headers: Dict[str, str] = None
    body: str = None
    timeout: int = 5
    interval: int = 30
    retries: int = 3
    expected_status: int = 200
    expected_content: str = None
    ssl_verify: bool = True
    custom_check: Optional[Callable] = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}

class AdvancedHealthChecker:
    """Advanced health checker with multiple protocol support"""
    
    def __init__(self):
        self.checks: Dict[str, HealthCheckConfig] = {}
        self.results: Dict[str, List[HealthCheckResult]] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
    
    async def start(self):
        """Start the health checker"""
        if self.running:
            return
        
        self.running = True
        self.session = aiohttp.ClientSession()
        
        # Start all health check tasks
        for name, config in self.checks.items():
            self.tasks[name] = asyncio.create_task(self._health_check_loop(name, config))
        
        logger.info("Health checker started")
    
    async def stop(self):
        """Stop the health checker"""
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        
        # Close session
        if self.session:
            await self.session.close()
        
        logger.info("Health checker stopped")
    
    def add_check(self, config: HealthCheckConfig):
        """Add a health check"""
        self.checks[config.name] = config
        self.results[config.name] = []
        
        # Start task if already running
        if self.running:
            self.tasks[config.name] = asyncio.create_task(self._health_check_loop(config.name, config))
    
    def remove_check(self, name: str):
        """Remove a health check"""
        if name in self.checks:
            del self.checks[name]
        
        if name in self.results:
            del self.results[name]
        
        if name in self.tasks:
            self.tasks[name].cancel()
            del self.tasks[name]
    
    async def _health_check_loop(self, name: str, config: HealthCheckConfig):
        """Health check loop for a specific check"""
        while self.running:
            try:
                result = await self._perform_health_check(config)
                self.results[name].append(result)
                
                # Keep only last 100 results
                if len(self.results[name]) > 100:
                    self.results[name] = self.results[name][-100:]
                
                # Log status changes
                if len(self.results[name]) > 1:
                    prev_status = self.results[name][-2].status
                    if prev_status != result.status:
                        logger.info(f"Health check {name} status changed: {prev_status.value} -> {result.status.value}")
                
                await asyncio.sleep(config.interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check {name} error: {e}")
                await asyncio.sleep(5)
    
    async def _perform_health_check(self, config: HealthCheckConfig) -> HealthCheckResult:
        """Perform a single health check"""
        start_time = time.time()
        
        for attempt in range(config.retries):
            try:
                if config.type == HealthCheckType.HTTP or config.type == HealthCheckType.HTTPS:
                    result = await self._check_http(config)
                elif config.type == HealthCheckType.TCP:
                    result = await self._check_tcp(config)
                elif config.type == HealthCheckType.PING:
                    result = await self._check_ping(config)
                elif config.type == HealthCheckType.CUSTOM:
                    result = await self._check_custom(config)
                elif config.type == HealthCheckType.DATABASE:
                    result = await self._check_database(config)
                elif config.type == HealthCheckType.CACHE:
                    result = await self._check_cache(config)
                elif config.type == HealthCheckType.DNS:
                    result = await self._check_dns(config)
                else:
                    result = HealthCheckResult(
                        status=HealthStatus.UNKNOWN,
                        response_time=0,
                        message=f"Unsupported check type: {config.type}",
                        timestamp=time.time()
                    )
                
                result.response_time = time.time() - start_time
                return result
                
            except Exception as e:
                if attempt == config.retries - 1:
                    return HealthCheckResult(
                        status=HealthStatus.UNHEALTHY,
                        response_time=time.time() - start_time,
                        message=f"Health check failed after {config.retries} attempts: {str(e)}",
                        timestamp=time.time()
                    )
                await asyncio.sleep(1)
        
        return HealthCheckResult(
            status=HealthStatus.UNKNOWN,
            response_time=time.time() - start_time,
            message="Unknown error",
            timestamp=time.time()
        )
    
    async def _check_http(self, config: HealthCheckConfig) -> HealthCheckResult:
        """Perform HTTP/HTTPS health check"""
        protocol = "https" if config.type == HealthCheckType.HTTPS else "http"
        url = f"{protocol}://{config.target}:{config.port}{config.path}"
        
        timeout = aiohttp.ClientTimeout(total=config.timeout)
        ssl_context = None if config.ssl_verify else False
        
        async with self.session.request(
            method=config.method,
            url=url,
            headers=config.headers,
            data=config.body,
            timeout=timeout,
            ssl=ssl_context
        ) as response:
            content = await response.text()
            
            # Check status code
            if response.status != config.expected_status:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    response_time=0,
                    message=f"Unexpected status code: {response.status}, expected: {config.expected_status}",
                    timestamp=time.time(),
                    details={"status_code": response.status, "content": content[:500]}
                )
            
            # Check content if specified
            if config.expected_content and config.expected_content not in content:
                return HealthCheckResult(
                    status=HealthStatus.WARNING,
                    response_time=0,
                    message=f"Expected content not found: {config.expected_content}",
                    timestamp=time.time(),
                    details={"content": content[:500]}
                )
            
            # Check response headers for health indicators
            health_headers = ['x-health-status', 'x-status', 'health']
            for header in health_headers:
                if header in response.headers:
                    header_value = response.headers[header].lower()
                    if 'unhealthy' in header_value or 'error' in header_value:
                        return HealthCheckResult(
                            status=HealthStatus.WARNING,
                            response_time=0,
                            message=f"Health header indicates issue: {header_value}",
                            timestamp=time.time(),
                            details={"headers": dict(response.headers)}
                        )
            
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                response_time=0,
                message="HTTP check passed",
                timestamp=time.time(),
                details={"status_code": response.status, "content_length": len(content)}
            )
    
    async def _check_tcp(self, config: HealthCheckConfig) -> HealthCheckResult:
        """Perform TCP health check"""
        try:
            future = asyncio.open_connection(config.target, config.port)
            reader, writer = await asyncio.wait_for(future, timeout=config.timeout)
            
            writer.close()
            await writer.wait_closed()
            
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                response_time=0,
                message="TCP connection successful",
                timestamp=time.time()
            )
            
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"TCP connection failed: {str(e)}",
                timestamp=time.time()
            )
    
    async def _check_ping(self, config: HealthCheckConfig) -> HealthCheckResult:
        """Perform ping health check"""
        try:
            # Use system ping command
            cmd = ['ping', '-c', '1', '-W', str(config.timeout), config.target]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    response_time=0,
                    message="Ping successful",
                    timestamp=time.time(),
                    details={"output": stdout.decode()}
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    response_time=0,
                    message=f"Ping failed: {stderr.decode()}",
                    timestamp=time.time()
                )
                
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"Ping error: {str(e)}",
                timestamp=time.time()
            )
    
    async def _check_custom(self, config: HealthCheckConfig) -> HealthCheckResult:
        """Perform custom health check"""
        if not config.custom_check:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                response_time=0,
                message="No custom check function provided",
                timestamp=time.time()
            )
        
        try:
            result = await config.custom_check(config)
            if isinstance(result, HealthCheckResult):
                return result
            else:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    response_time=0,
                    message="Custom check passed" if result else "Custom check failed",
                    timestamp=time.time()
                )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"Custom check error: {str(e)}",
                timestamp=time.time()
            )
    
    async def _check_database(self, config: HealthCheckConfig) -> HealthCheckResult:
        """Perform database health check"""
        try:
            # Parse database URL
            parsed = urlparse(config.target)
            
            if parsed.scheme in ['postgresql', 'postgres']:
                return await self._check_postgresql(parsed, config)
            elif parsed.scheme == 'mysql':
                return await self._check_mysql(parsed, config)
            elif parsed.scheme == 'mongodb':
                return await self._check_mongodb(parsed, config)
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNKNOWN,
                    response_time=0,
                    message=f"Unsupported database type: {parsed.scheme}",
                    timestamp=time.time()
                )
                
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"Database check error: {str(e)}",
                timestamp=time.time()
            )
    
    async def _check_postgresql(self, parsed: urlparse, config: HealthCheckConfig) -> HealthCheckResult:
        """Check PostgreSQL health"""
        try:
            import asyncpg
            
            conn = await asyncpg.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/'),
                timeout=config.timeout
            )
            
            # Simple query
            result = await conn.fetchval('SELECT 1')
            await conn.close()
            
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                response_time=0,
                message="PostgreSQL connection successful",
                timestamp=time.time()
            )
            
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"PostgreSQL check failed: {str(e)}",
                timestamp=time.time()
            )
    
    async def _check_mysql(self, parsed: urlparse, config: HealthCheckConfig) -> HealthCheckResult:
        """Check MySQL health"""
        try:
            import aiomysql
            
            conn = await aiomysql.connect(
                host=parsed.hostname,
                port=parsed.port or 3306,
                user=parsed.username,
                password=parsed.password,
                db=parsed.path.lstrip('/'),
                connect_timeout=config.timeout
            )
            
            async with conn.cursor() as cursor:
                await cursor.execute('SELECT 1')
                result = await cursor.fetchone()
            
            conn.close()
            
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                response_time=0,
                message="MySQL connection successful",
                timestamp=time.time()
            )
            
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"MySQL check failed: {str(e)}",
                timestamp=time.time()
            )
    
    async def _check_mongodb(self, parsed: urlparse, config: HealthCheckConfig) -> HealthCheckResult:
        """Check MongoDB health"""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            
            client = AsyncIOMotorClient(
                config.target,
                serverSelectionTimeoutMS=config.timeout * 1000
            )
            
            # Test connection
            await client.admin.command('ping')
            client.close()
            
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                response_time=0,
                message="MongoDB connection successful",
                timestamp=time.time()
            )
            
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"MongoDB check failed: {str(e)}",
                timestamp=time.time()
            )
    
    async def _check_cache(self, config: HealthCheckConfig) -> HealthCheckResult:
        """Check cache (Redis/Memcached) health"""
        try:
            # Parse cache URL
            parsed = urlparse(config.target)
            
            if parsed.scheme == 'redis':
                return await self._check_redis(parsed, config)
            elif parsed.scheme == 'memcached':
                return await self._check_memcached(parsed, config)
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNKNOWN,
                    response_time=0,
                    message=f"Unsupported cache type: {parsed.scheme}",
                    timestamp=time.time()
                )
                
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"Cache check error: {str(e)}",
                timestamp=time.time()
            )
    
    async def _check_redis(self, parsed: urlparse, config: HealthCheckConfig) -> HealthCheckResult:
        """Check Redis health"""
        try:
            import aioredis
            
            redis_client = await aioredis.from_url(
                config.target,
                socket_timeout=config.timeout
            )
            
            # Test Redis
            result = await redis_client.ping()
            await redis_client.close()
            
            if result:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    response_time=0,
                    message="Redis connection successful",
                    timestamp=time.time()
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    response_time=0,
                    message="Redis ping failed",
                    timestamp=time.time()
                )
                
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"Redis check failed: {str(e)}",
                timestamp=time.time()
            )
    
    async def _check_memcached(self, parsed: urlparse, config: HealthCheckConfig) -> HealthCheckResult:
        """Check Memcached health"""
        try:
            import aiomcache
            
            client = aiomcache.Client(
                parsed.hostname,
                parsed.port or 11211,
                timeout=config.timeout
            )
            
            # Test Memcached
            await client.set(b'health_check', b'ok')
            result = await client.get(b'health_check')
            client.close()
            
            if result == b'ok':
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    response_time=0,
                    message="Memcached connection successful",
                    timestamp=time.time()
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    response_time=0,
                    message="Memcached test failed",
                    timestamp=time.time()
                )
                
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"Memcached check failed: {str(e)}",
                timestamp=time.time()
            )
    
    async def _check_dns(self, config: HealthCheckConfig) -> HealthCheckResult:
        """Check DNS health"""
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = config.timeout
            
            # Resolve domain
            answers = resolver.resolve(config.target, 'A')
            
            if answers:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    response_time=0,
                    message=f"DNS resolution successful: {[str(answer) for answer in answers]}",
                    timestamp=time.time(),
                    details={"ips": [str(answer) for answer in answers]}
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    response_time=0,
                    message="No DNS records found",
                    timestamp=time.time()
                )
                
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"DNS check failed: {str(e)}",
                timestamp=time.time()
            )
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        status = {
            "overall": HealthStatus.HEALTHY,
            "checks": {},
            "timestamp": time.time()
        }
        
        for name, results in self.results.items():
            if not results:
                status["checks"][name] = {
                    "status": HealthStatus.UNKNOWN.value,
                    "last_check": None,
                    "response_time": 0,
                    "message": "No checks performed"
                }
                continue
            
            latest = results[-1]
            status["checks"][name] = {
                "status": latest.status.value,
                "last_check": latest.timestamp,
                "response_time": latest.response_time,
                "message": latest.message,
                "details": latest.details
            }
            
            # Update overall status
            if latest.status == HealthStatus.UNHEALTHY:
                status["overall"] = HealthStatus.UNHEALTHY
            elif latest.status == HealthStatus.WARNING and status["overall"] == HealthStatus.HEALTHY:
                status["overall"] = HealthStatus.WARNING
        
        return status
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get health check metrics"""
        metrics = {
            "total_checks": len(self.checks),
            "healthy_checks": 0,
            "unhealthy_checks": 0,
            "warning_checks": 0,
            "unknown_checks": 0,
            "avg_response_time": 0,
            "checks": {}
        }
        
        total_response_time = 0
        response_time_count = 0
        
        for name, results in self.results.items():
            if not results:
                metrics["unknown_checks"] += 1
                continue
            
            latest = results[-1]
            
            if latest.status == HealthStatus.HEALTHY:
                metrics["healthy_checks"] += 1
            elif latest.status == HealthStatus.UNHEALTHY:
                metrics["unhealthy_checks"] += 1
            elif latest.status == HealthStatus.WARNING:
                metrics["warning_checks"] += 1
            else:
                metrics["unknown_checks"] += 1
            
            if latest.response_time > 0:
                total_response_time += latest.response_time
                response_time_count += 1
            
            metrics["checks"][name] = {
                "status": latest.status.value,
                "response_time": latest.response_time,
                "total_checks": len(results),
                "consecutive_failures": self._get_consecutive_failures(results)
            }
        
        if response_time_count > 0:
            metrics["avg_response_time"] = total_response_time / response_time_count
        
        return metrics
    
    def _get_consecutive_failures(self, results: List[HealthCheckResult]) -> int:
        """Get consecutive failures for a check"""
        consecutive = 0
        for result in reversed(results):
            if result.status == HealthStatus.UNHEALTHY:
                consecutive += 1
            else:
                break
        return consecutive

# Example usage
if __name__ == "__main__":
    async def main():
        checker = AdvancedHealthChecker()
        
        # Add various health checks
        checker.add_check(HealthCheckConfig(
            name="api_server",
            type=HealthCheckType.HTTP,
            target="localhost",
            port=5000,
            path="/health",
            timeout=5
        ))
        
        checker.add_check(HealthCheckConfig(
            name="database",
            type=HealthCheckType.DATABASE,
            target="postgresql://user:pass@localhost:5432/flavorsnap",
            timeout=5
        ))
        
        checker.add_check(HealthCheckConfig(
            name="redis",
            type=HealthCheckType.CACHE,
            target="redis://localhost:6379",
            timeout=5
        ))
        
        await checker.start()
        
        # Run for a while
        await asyncio.sleep(60)
        
        # Get status
        status = checker.get_status()
        print(json.dumps(status, indent=2, default=str))
        
        await checker.stop()
    
    asyncio.run(main())
