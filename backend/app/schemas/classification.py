from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional

class ClassificationCreate(BaseModel):
    """Skema untuk request klasifikasi"""
    pass  # Tidak perlu fields karena menggunakan form data untuk upload file

class ClassificationResponse(BaseModel):
    """Skema untuk response hasil klasifikasi"""
    id: UUID
    user_id: UUID
    label: str
    confidence: float
    timestamp: datetime
    image_url: Optional[str] = None
    processing_time_ms: int

    class Config:
        from_attributes = True

class BatchClassificationResponse(BaseModel):
    """Skema untuk response multiple klasifikasi"""
    total_count: int
    processing_time_ms: int
    results: list[ClassificationResponse]