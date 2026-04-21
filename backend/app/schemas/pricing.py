from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional
from decimal import Decimal


class WasteTypeCreate(BaseModel):
    """Skema untuk create waste type (hanya admin)"""
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., pattern="^(recyclable|non-recyclable)$")
    unit: str = Field(default="kg", max_length=20)
    current_price: Optional[Decimal] = None
    currency: str = Field(default="IDR", max_length=3)


class WasteTypeUpdate(BaseModel):
    """Skema untuk update waste type"""
    name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    current_price: Optional[Decimal] = None


class WasteTypePriceUpdate(BaseModel):
    """Skema untuk update harga (operator only)"""
    new_price: Optional[Decimal] = None
    reason: Optional[str] = Field(None, max_length=255)


class WasteTypeResponse(BaseModel):
    """Skema response waste type"""
    id: UUID
    name: str
    category: str
    unit: str
    current_price: Optional[Decimal]
    currency: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PriceHistoryResponse(BaseModel):
    """Skema response price history"""
    id: UUID
    waste_type_id: UUID
    waste_type_name: str
    old_price: Optional[Decimal]
    new_price: Optional[Decimal]
    updated_by_id: UUID
    updated_by_username: str
    updated_at: datetime
    reason: Optional[str]

    class Config:
        from_attributes = True


class ClassificationWithPriceResponse(BaseModel):
    """Skema response classification dengan pricing info"""
    id: UUID
    user_id: UUID
    waste_type_id: Optional[UUID]
    waste_type_name: Optional[str]
    label: str
    confidence: float
    estimated_volume: Optional[float]
    actual_volume: Optional[float]
    volume_unit: str
    estimated_price: Optional[Decimal]
    timestamp: datetime
    image_url: Optional[str]
    processing_time_ms: Optional[int]

    class Config:
        from_attributes = True


class ClassificationVolumeUpdate(BaseModel):
    """Skema untuk update volume hasil klasifikasi (by user)"""
    actual_volume: float = Field(..., gt=0)
    reason: Optional[str] = Field(None, max_length=255)
