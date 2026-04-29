import time
import os
import logging
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import redis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api-gateway")

# Configuration
ML_MODEL_API_URL = os.environ.get("ML_MODEL_API_URL", "http://ml-model-api:5000")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
API_KEYS = os.environ.get("API_KEYS", "dev-key-1,dev-key-2").split(",")

# Metrics
REQUEST_COUNT = Counter("gateway_requests_total", "Total requests processed by gateway", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("gateway_request_latency_seconds", "Request latency", ["endpoint"])

# Initialize Redis for rate limiting
redis_client = redis.from_url(REDIS_URL)

# Initialize Limiter
limiter = Limiter(key_func=get_remote_address, storage_uri=REDIS_URL)
app = FastAPI(title="FlavorSnap API Gateway")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth Dependency
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if os.environ.get("ENV") == "development":
        return "dev-user"
    if not x_api_key or x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return x_api_key

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time()}

async def proxy_request(request: Request, path: str):
    url = f"{ML_MODEL_API_URL}/{path}"
    method = request.method
    headers = dict(request.headers)
    # Remove host header to let httpx set it correctly
    headers.pop("host", None)
    
    # Forward the request ID or generate one
    request_id = headers.get("x-request-id", f"gw_{int(time.time()*1000)}")
    headers["x-request-id"] = request_id
    
    body = await request.body()
    
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            proxy_resp = await client.request(
                method,
                url,
                headers=headers,
                params=request.query_params,
                content=body
            )
        
        latency = time.time() - start_time
        REQUEST_LATENCY.labels(endpoint=path).observe(latency)
        REQUEST_COUNT.labels(method=method, endpoint=path, status=proxy_resp.status_code).inc()
        
        return Response(
            content=proxy_resp.content,
            status_code=proxy_resp.status_code,
            headers=dict(proxy_resp.headers)
        )
    except httpx.RequestError as exc:
        logger.error(f"Error proxying request to {url}: {exc}")
        REQUEST_COUNT.labels(method=method, endpoint=path, status=502).inc()
        raise HTTPException(status_code=502, detail="Bad Gateway")

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
@limiter.limit("100/minute")
async def gateway_proxy(request: Request, path: str, api_key: str = Depends(verify_api_key)):
    logger.info(f"Proxying {request.method} request to {path}")
    return await proxy_request(request, path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
