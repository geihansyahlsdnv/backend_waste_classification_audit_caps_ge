from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import datetime

from ...db.session import get_db
from ...db.models import WasteType, PriceHistory, ClassificationResult, User
from ...schemas.pricing import (
    WasteTypeCreate,
    WasteTypeResponse,
    PriceHistoryResponse,
    WasteTypePriceUpdate,
    ClassificationWithPriceResponse,
    ClassificationVolumeUpdate
)
from ...core.security import check_permissions

router = APIRouter()

@router.get("/waste-types", response_model=list[WasteTypeResponse])
async def list_waste_types(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    waste_types = await db.scalars(
        select(WasteType).where(WasteType.is_active == True).offset(skip).limit(limit)
    )
    return waste_types.all()


@router.post("/waste-types", response_model=WasteTypeResponse, status_code=201)
async def create_waste_type(
    waste_type_in: WasteTypeCreate,
    current_user: dict = Depends(check_permissions("admin")),
    db: AsyncSession = Depends(get_db)
):
    if await db.scalar(select(WasteType).where(WasteType.name == waste_type_in.name)):
        raise HTTPException(status_code=400, detail="Waste type dengan nama ini sudah ada")
    
    waste_type = WasteType(
        name=waste_type_in.name,
        category=waste_type_in.category,
        unit=waste_type_in.unit,
        current_price=waste_type_in.current_price,
        currency=waste_type_in.currency
    )
    db.add(waste_type)
    await db.commit()
    await db.refresh(waste_type)
    return waste_type


@router.patch("/waste-types/{waste_type_id}/price", response_model=WasteTypeResponse)
async def update_waste_type_price(
    waste_type_id: UUID,
    price_update: WasteTypePriceUpdate,
    current_user: dict = Depends(check_permissions("supervisor", "admin")),
    db: AsyncSession = Depends(get_db)
):
    waste_type = await db.scalar(select(WasteType).where(WasteType.id == waste_type_id))
    if not waste_type:
        raise HTTPException(status_code=404, detail="Waste type tidak ditemukan")
    
    price_history = PriceHistory(
        waste_type_id=waste_type.id,
        old_price=waste_type.current_price,
        new_price=price_update.new_price,
        updated_by_id=current_user["user_id"],
        reason=price_update.reason
    )
    
    waste_type.current_price = price_update.new_price
    db.add(price_history)
    db.add(waste_type)
    await db.commit()
    await db.refresh(waste_type)
    return waste_type


@router.get("/price-history", response_model=list[PriceHistoryResponse])
async def get_price_history(
    current_user: dict = Depends(check_permissions("admin", "supervisor")),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    result = await db.execute(
        select(PriceHistory)
        .options(
            selectinload(PriceHistory.waste_type),
            selectinload(PriceHistory.updated_by_user)
        )
        .order_by(PriceHistory.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    histories = result.scalars().all()

    return [
        {
            "id": h.id,
            "waste_type_id": h.waste_type_id,
            "waste_type_name": h.waste_type.name if h.waste_type else "Unknown",
            "old_price": h.old_price,
            "new_price": h.new_price,
            "updated_by_id": h.updated_by_id,
            "updated_by_username": h.updated_by_user.username if h.updated_by_user else "Unknown",
            "updated_at": h.updated_at,
            "reason": h.reason,
        }
        for h in histories
    ]


@router.patch("/classification/{result_id}/volume", response_model=ClassificationWithPriceResponse)
async def update_classification_volume(
    result_id: UUID,
    volume_update: ClassificationVolumeUpdate,
    current_user: dict = Depends(check_permissions("operator", "supervisor", "admin")),
    db: AsyncSession = Depends(get_db)
):
    classification = await db.scalar(select(ClassificationResult).where(ClassificationResult.id == result_id))
    if not classification:
        raise HTTPException(status_code=404, detail="Klasifikasi tidak ditemukan")
    
    if current_user["user_id"] != classification.user_id and current_user["role"] not in ["admin", "supervisor"]:
        raise HTTPException(status_code=403, detail="Tidak punya akses untuk edit hasil ini")
    
    classification.actual_volume = volume_update.actual_volume
    
    if classification.waste_type_id:
        await db.refresh(classification, ["waste_type"])
        if classification.waste_type and classification.waste_type.current_price:
            from decimal import Decimal
            classification.estimated_price = (
                Decimal(str(classification.actual_volume)) * 
                classification.waste_type.current_price
            )
    db.add(classification)
    await db.commit()
    await db.refresh(classification, ["waste_type"])
    
    return {
        "id": classification.id,
        "user_id": classification.user_id,
        "waste_type_id": classification.waste_type_id,
        "waste_type_name": classification.waste_type.name if classification.waste_type else None,
        "label": classification.label,
        "confidence": classification.confidence,
        "estimated_volume": classification.estimated_volume,
        "actual_volume": classification.actual_volume,
        "volume_unit": classification.volume_unit,
        "estimated_price": classification.estimated_price,
        "timestamp": classification.timestamp,
        "image_url": classification.image_url,
        "processing_time_ms": classification.processing_time_ms
    }


@router.get("/classification/{result_id}", response_model=ClassificationWithPriceResponse)
async def get_classification_detail(
    result_id: UUID,
    current_user: dict = Depends(check_permissions("operator", "supervisor", "admin")),
    db: AsyncSession = Depends(get_db)
):
    classification = await db.scalar(select(ClassificationResult).where(ClassificationResult.id == result_id))
    if not classification:
        raise HTTPException(status_code=404, detail="Klasifikasi tidak ditemukan")
    
    if current_user["user_id"] != classification.user_id and current_user["role"] not in ["admin", "supervisor"]:
        raise HTTPException(status_code=403, detail="Tidak punya akses")
    
    await db.refresh(classification, ["waste_type"])
    
    return {
        "id": classification.id,
        "user_id": classification.user_id,
        "waste_type_id": classification.waste_type_id,
        "waste_type_name": classification.waste_type.name if classification.waste_type else None,
        "label": classification.label,
        "confidence": classification.confidence,
        "estimated_volume": classification.estimated_volume,
        "actual_volume": classification.actual_volume,
        "volume_unit": classification.volume_unit,
        "estimated_price": classification.estimated_price,
        "timestamp": classification.timestamp,
        "image_url": classification.image_url,
        "processing_time_ms": classification.processing_time_ms
    }