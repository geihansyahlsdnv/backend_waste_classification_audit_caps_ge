from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from uuid import UUID
from datetime import datetime, timedelta

from ...db.session import get_db
from ...db.models import ClassificationResult
from ...schemas.stats import HistoryParams, PaginatedHistory
from ...schemas.classification import ClassificationResponse
from ...core.security import get_current_user, check_permissions

router = APIRouter()

@router.get("/history", response_model=PaginatedHistory, dependencies=[Depends(check_permissions("admin", "supervisor", "operator"))])
async def get_classification_history(
    params: HistoryParams = Depends(),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(ClassificationResult)
    filters = []
    
    if current_user["role"] != "admin":
        filters.append(ClassificationResult.user_id == current_user["user_id"])
    
    if params.start_date:
        filters.append(ClassificationResult.timestamp >= params.start_date)
    if params.end_date:
        filters.append(ClassificationResult.timestamp <= params.end_date)
    if params.label:
        filters.append(ClassificationResult.label == params.label)
    if params.min_confidence:
        filters.append(ClassificationResult.confidence >= params.min_confidence)
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.order_by(ClassificationResult.timestamp.desc())
    
    total = await db.scalar(select(func.count()).select_from(ClassificationResult).where(and_(*filters) if filters else True))
    
    query = query.offset((params.page - 1) * params.per_page).limit(params.per_page)
    result = await db.execute(query)
    items = result.scalars().all()
    
    return PaginatedHistory(
        total=total,
        page=params.page,
        per_page=params.per_page,
        items=items
    )

@router.get("/history/{result_id}", response_model=ClassificationResponse, dependencies=[Depends(check_permissions("admin", "supervisor", "operator"))])
async def get_classification_detail(
    result_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(ClassificationResult).where(ClassificationResult.id == result_id)
    
    if current_user["role"] != "admin":
        query = query.where(ClassificationResult.user_id == current_user["user_id"])
    
    classification = await db.scalar(query)
    if not classification:
        raise HTTPException(status_code=404, detail="Hasil klasifikasi tidak ditemukan")
    
    return classification