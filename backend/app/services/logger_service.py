import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import Request, Response
from prometheus_client import Counter, Histogram

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

MODEL_INFERENCE_TIME = Histogram(
    'model_inference_duration_seconds',
    'Model inference duration',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

class LoggerService:
    def __init__(self):
        self.logger = logging.getLogger("waste_classifier")
        self.request_id = 0
    
    def get_request_id(self) -> str:
        self.request_id += 1
        return f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self.request_id}"
    
    def log_request(self, request: Request, response: Response, duration: float, user_id: Optional[str] = None):
        REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
        REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(duration)
        
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": self.get_request_id(),
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "user_id": user_id,
            "ip": request.client.host
        }
        self.logger.info(f"Request: {json.dumps(log_data)}")
    
    def log_error(self, error: Exception, request: Optional[Request] = None, user_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        error_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": self.get_request_id(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "user_id": user_id,
        }
        
        if request:
            error_data.update({"method": request.method, "path": str(request.url.path), "ip": request.client.host})
        
        if context:
            error_data["context"] = context
        
        self.logger.error(f"Error: {json.dumps(error_data)}")
    
    def log_model_inference(self, processing_time: float, success: bool, error: Optional[str] = None):
        MODEL_INFERENCE_TIME.observe(processing_time)
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time_ms": round(processing_time * 1000, 2),
            "success": success
        }
        if error:
            log_data["error"] = error
        self.logger.info(f"Inference: {json.dumps(log_data)}")

logger_service = LoggerService()