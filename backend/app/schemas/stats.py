from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from .classification import ClassificationResponse

class HistoryParams(BaseModel):
    """Parameter untuk filtering dan pagination history"""
    page: int = 1
    per_page: int = 10
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    label: Optional[str] = None
    min_confidence: Optional[float] = None

class PaginatedHistory(BaseModel):
    """Response untuk history dengan pagination"""
    total: int
    page: int
    per_page: int
    items: List[ClassificationResponse]

class UserStats(BaseModel):
    """Statistik per user"""
    total_classifications: int
    recyclable_count: int
    non_recyclable_count: int
    avg_confidence: float
    avg_processing_time: float

class DailyStats(BaseModel):
    """Statistik harian"""
    date: datetime
    total_classifications: int
    recyclable_count: int
    non_recyclable_count: int
    avg_confidence: float

class GlobalStats(BaseModel):
    """Statistik global sistem"""
    total_users: int
    total_classifications: int
    recyclable_percentage: float
    non_recyclable_percentage: float
    avg_confidence: float
    avg_processing_time: float
    daily_stats: List[DailyStats]