import os
import logging
import pybreaker
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

logger = logging.getLogger(__name__)

# Circuit Breaker configuration
db_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    name="database_breaker"
)

model_breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=30,
    name="ml_model_breaker"
)

class ServiceMeshManager:
    """Manager for service mesh features within the application"""
    
    @staticmethod
    def setup_observability(app):
        """Setup OpenTelemetry for distributed tracing"""
        try:
            otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger-collector:4317")
            
            trace.set_tracer_provider(TracerProvider())
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            span_processor = BatchSpanProcessor(otlp_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            # Instrument Flask and Requests
            FlaskInstrumentor().instrument_app(app)
            RequestsInstrumentor().instrument()
            
            logger.info("Observability (OpenTelemetry) initialized")
        except Exception as e:
            logger.error(f"Failed to initialize observability: {e}")

    @staticmethod
    def get_service_discovery_config():
        """Get configuration for service discovery (e.g. Istio virtual service names)"""
        return {
            "gateway_url": os.environ.get("GATEWAY_SERVICE_URL", "http://api-gateway:8000"),
            "cache_url": os.environ.get("CACHE_SERVICE_URL", "http://distributed-cache:6379"),
            "queue_url": os.environ.get("QUEUE_SERVICE_URL", "http://message-queue:5672")
        }

def handle_circuit_breaker_failure(e):
    """Fallback logic when circuit is open"""
    logger.error(f"Circuit breaker triggered: {e}")
    return {"error": "Service temporarily unavailable", "status": "circuit_open"}, 503
