from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional, List

class DetectionSchema(BaseModel):
    label: str
    confidence: float
    box_2d: Optional[list] = None
    class Config:
        from_attributes = True

class ClassificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    label: str
    confidence: float
    timestamp: datetime
    image_url: Optional[str] = None
    processing_time_ms: int
    detections: List[DetectionSchema] = [] # Data rich buat laporan

    class Config:
        from_attributes = True

class BatchClassificationResponse(BaseModel):
    total_count: int
    processing_time_ms: int
    results: List[ClassificationResponse]