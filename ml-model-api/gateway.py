import os
import logging
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)

class GatewayIntegration:
    """Utilities for integrating ML Model API with the Advanced API Gateway"""
    
    GATEWAY_HEADER = "X-From-Gateway"
    GATEWAY_SECRET = os.environ.get("GATEWAY_INTERNAL_SECRET", "dev-internal-secret")
    
    @staticmethod
    def require_gateway(f):
        """Decorator to ensure requests come through the API Gateway"""
        @wraps(f)
        def decorated(*args, **kwargs):
            # In development, skip this check
            if os.environ.get("FLASK_ENV") == "development":
                return f(*args, **kwargs)
                
            gateway_secret = request.headers.get(GatewayIntegration.GATEWAY_HEADER)
            if not gateway_secret or gateway_secret != GatewayIntegration.GATEWAY_SECRET:
                logger.warning(f"Unauthorized access attempt directly to backend from {request.remote_addr}")
                return jsonify({
                    "error": "Direct access forbidden", 
                    "message": "Requests must be routed through the API Gateway"
                }), 403
            return f(*args, **kwargs)
        return decorated

    @staticmethod
    def get_original_ip():
        """Get the original client IP from the gateway headers"""
        return request.headers.get("X-Forwarded-For", request.remote_addr)

    @staticmethod
    def get_request_id():
        """Get the unique request ID assigned by the gateway"""
        return request.headers.get("X-Request-ID", "internal-req")
