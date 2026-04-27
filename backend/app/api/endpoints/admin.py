from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ...db.session import get_db
from ...db.models import User, ClassificationResult
from ...core.security import check_permissions

router = APIRouter()

@router.get("/users")
async def get_admin_users(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(check_permissions("admin"))
):
    query = select(User)
    result = await db.execute(query)
    users = result.scalars().all()
    
    response = []
    for u in users:
        response.append({
            "id": str(u.id),
            "name": u.username,
            "email": u.email,
            "role": u.role
        })
    return response

@router.get("/audits")
async def get_admin_audits(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(check_permissions("admin"))
):
    query = select(ClassificationResult).options(selectinload(ClassificationResult.detections)).order_by(ClassificationResult.timestamp.desc())
    result = await db.execute(query)
    audits = result.scalars().all()
    
    response = []
    for item in audits:
        total_detections = len(item.detections)
        avg_conf = sum(d.confidence for d in item.detections) / total_detections if total_detections > 0 else item.confidence
        response.append({
            "audit_id": str(item.id),
            "user_id": str(item.user_id),
            "image_url": item.image_url,
            "top_label": item.label,
            "total_detections": total_detections,
            "average_confidence": round(avg_conf, 2),
            "created_at": item.timestamp.isoformat() + "Z"
        })
    return response
