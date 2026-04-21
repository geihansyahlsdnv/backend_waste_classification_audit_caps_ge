from datetime import datetime
import uuid
from typing import Optional
from decimal import Decimal
from sqlalchemy import String, DateTime, Float, ForeignKey, Enum as SQLEnum, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base_class import Base


class User(Base):
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(
        SQLEnum('operator', 'admin', 'developer', name='user_role'),
        default='operator'
    )
    
    classifications: Mapped[list["ClassificationResult"]] = relationship(
        "ClassificationResult", back_populates="user"
    )
    price_updates: Mapped[list["PriceHistory"]] = relationship(
        "PriceHistory", back_populates="updated_by_user"
    )


class WasteType(Base):
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str] = mapped_column(
        SQLEnum('recyclable', 'non-recyclable', name='waste_category')
    )
    unit: Mapped[str] = mapped_column(String(20), default='kg')
    current_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default='IDR')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    classifications: Mapped[list["ClassificationResult"]] = relationship(
        "ClassificationResult", back_populates="waste_type"
    )
    price_history: Mapped[list["PriceHistory"]] = relationship(
        "PriceHistory", back_populates="waste_type"
    )


class PriceHistory(Base):
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    waste_type_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('wastetype.id'), index=True
    )
    old_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    new_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    updated_by_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('user.id'), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    waste_type: Mapped["WasteType"] = relationship("WasteType", back_populates="price_history")
    updated_by_user: Mapped["User"] = relationship("User", back_populates="price_updates")


class ClassificationResult(Base):
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('user.id'), index=True)
    waste_type_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey('wastetype.id'), nullable=True
    )
    label: Mapped[str] = mapped_column(SQLEnum('recyclable', 'non-recyclable', name='waste_label'))
    confidence: Mapped[float] = mapped_column(Float)
    estimated_volume: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_volume: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume_unit: Mapped[str] = mapped_column(String(20), default='kg')
    estimated_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    user: Mapped["User"] = relationship("User", back_populates="classifications")
    waste_type: Mapped[Optional["WasteType"]] = relationship("WasteType", back_populates="classifications")