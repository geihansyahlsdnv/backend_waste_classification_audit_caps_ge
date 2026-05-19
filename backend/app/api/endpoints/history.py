from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List

from ...db.session import get_db
from ...db.models import ClassificationResult
from ...schemas.stats import HistoryParams
from ...core.security import check_permissions

router = APIRouter()

@router.get("/audits/history")
async def get_audits_history(
    current_user: dict = Depends(check_permissions("admin", "supervisor", "operator")),
    db: AsyncSession = Depends(get_db)
):
    query = select(ClassificationResult).options(selectinload(ClassificationResult.detections))
    filters = []
    
    if current_user["role"] != "admin":
        filters.append(ClassificationResult.user_id == current_user["user_id"])
        
    if filters: 
        query = query.where(and_(*filters))
    
    query = query.order_by(ClassificationResult.timestamp.desc())
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    response = []
    for item in items:
        total_detections = len(item.detections)
        avg_conf = sum(d.confidence for d in item.detections) / total_detections if total_detections > 0 else item.confidence
        response.append({
            "audit_id": str(item.id),
            "image_url": item.image_url,
            "top_label": item.label,
            "total_detections": total_detections,
            "average_confidence": round(avg_conf, 2),
            "created_at": item.timestamp.isoformat() + "Z"
        })
        
    return response

@router.get("/audits/{result_id}")
async def get_audit_detail(
    result_id: UUID,
    current_user: dict = Depends(check_permissions("admin", "supervisor", "operator")),
    db: AsyncSession = Depends(get_db)
):
    query = select(ClassificationResult).options(selectinload(ClassificationResult.detections)).where(ClassificationResult.id == result_id)
    if current_user["role"] != "admin":
        query = query.where(ClassificationResult.user_id == current_user["user_id"])
    
    classification = await db.scalar(query)
    if not classification:
        raise HTTPException(status_code=404, detail="Audit tidak ditemukan")
        
    import json
    response_detections = []
    for d in classification.detections:
        box_coords = d.box_2d if d.box_2d else [0,0,0,0]
        response_detections.append({
            "label": d.label,
            "confidence": d.confidence,
            "bbox": {
                "x1": box_coords[0],
                "y1": box_coords[1],
                "x2": box_coords[2],
                "y2": box_coords[3]
            }
        })
        
    return {
        "audit_id": str(classification.id),
        "image_url": classification.image_url,
        "top_prediction": classification.label,
        "created_at": classification.timestamp.isoformat() + "Z",
        "detections": response_detections
    }


@router.delete("/audits/{result_id}", status_code=200)
async def delete_audit(
    result_id: UUID,
    current_user: dict = Depends(check_permissions("admin", "supervisor", "operator")),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an audit. Operators and supervisors can only delete their own audits.
    Admins can delete any audit.
    """
    classification = await db.scalar(
        select(ClassificationResult).where(ClassificationResult.id == result_id)
    )
    if not classification:
        raise HTTPException(status_code=404, detail="Audit tidak ditemukan")

    if current_user["role"] != "admin" and classification.user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Tidak punya akses untuk menghapus audit ini")

    await db.delete(classification)
    await db.commit()

    return {"detail": "Audit berhasil dihapus", "audit_id": str(result_id)}