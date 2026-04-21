# API Documentation

## Authentication

### Register New User
```http
POST /auth/register
Content-Type: application/json

{
    "username": "user123",
    "email": "user@example.com",
    "password": "securepass123",
    "role": "operator"
}
```

Response:
```json
{
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "user123",
    "email": "user@example.com",
    "role": "operator"
}
```

### Login
```http
POST /auth/login
Content-Type: application/json

{
    "username": "user123",
    "password": "securepass123"
}
```

Response:
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer"
}
```

## Classification

### Classify Single Image
```http
POST /api/classify
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <image_file>
```

Response:
```json
{
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "label": "recyclable",
    "confidence": 0.95,
    "timestamp": "2025-11-05T10:00:00Z",
    "image_url": "http://minio:9000/classifications/image.jpg",
    "processing_time_ms": 150
}
```

### Batch Classification
```http
POST /api/classify/batch
Authorization: Bearer <token>
Content-Type: multipart/form-data

files: [<image_file1>, <image_file2>, ...]
```

Response:
```json
{
    "total_count": 2,
    "processing_time_ms": 320,
    "results": [
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "label": "recyclable",
            "confidence": 0.95,
            "timestamp": "2025-11-05T10:00:00Z",
            "processing_time_ms": 150
        },
        {
            "id": "123e4567-e89b-12d3-a456-426614174001",
            "label": "non-recyclable",
            "confidence": 0.88,
            "timestamp": "2025-11-05T10:00:01Z",
            "processing_time_ms": 170
        }
    ]
}
```

## History and Stats

### Get Classification History
```http
GET /api/history?page=1&per_page=10
Authorization: Bearer <token>
```

Response:
```json
{
    "total": 100,
    "page": 1,
    "per_page": 10,
    "items": [
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "label": "recyclable",
            "confidence": 0.95,
            "timestamp": "2025-11-05T10:00:00Z",
            "processing_time_ms": 150
        }
    ]
}
```

### Get User Stats
```http
GET /api/stats/me
Authorization: Bearer <token>
```

Response:
```json
{
    "total_classifications": 100,
    "recyclable_count": 75,
    "non_recyclable_count": 25,
    "avg_confidence": 0.92,
    "avg_processing_time": 180.5
}
```

### Get Global Stats (Admin/Supervisor)
```http
GET /api/stats/global
Authorization: Bearer <token>
```

Response:
```json
{
    "total_users": 50,
    "total_classifications": 1000,
    "recyclable_percentage": 70.5,
    "non_recyclable_percentage": 29.5,
    "avg_confidence": 0.91,
    "avg_processing_time": 175.3,
    "daily_stats": [
        {
            "date": "2025-11-05",
            "total_classifications": 150,
            "recyclable_count": 100,
            "non_recyclable_count": 50,
            "avg_confidence": 0.93
        }
    ]
}
```

## Monitoring

### Health Check
```http
GET /health
```

Response:
```json
{
    "status": "healthy",
    "timestamp": "2025-11-05T10:00:00Z",
    "components": {
        "model": {
            "status": "healthy",
            "info": {
                "version": "1.0.0",
                "device": "cuda"
            }
        },
        "database": {
            "status": "healthy"
        },
        "redis": {
            "status": "healthy"
        },
        "minio": {
            "status": "healthy"
        }
    }
}
```

### Prometheus Metrics
```http
GET /metrics
```

Response:
```text
# HELP http_requests_total Total HTTP requests count
# TYPE http_requests_total counter
http_requests_total{method="POST",endpoint="/api/classify",status="200"} 1000

# HELP model_inference_duration_seconds Model inference duration
# TYPE model_inference_duration_seconds histogram
model_inference_duration_seconds_bucket{le="0.1"} 100
model_inference_duration_seconds_bucket{le="0.5"} 800
model_inference_duration_seconds_bucket{le="1.0"} 950
model_inference_duration_seconds_bucket{le="2.0"} 1000
```