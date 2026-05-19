from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ...db.session import get_db
from ...db.models import User, ClassificationResult
from ...core.security import check_permissions

router = APIRouter()

ALLOWED_ROLES = {"operator", "supervisor", "admin"}


class RoleUpdate(BaseModel):
    role: str = Field(..., description="One of: operator, supervisor, admin")


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


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    role_update: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(check_permissions("admin"))
):
    if role_update.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Role tidak valid. Pilihan: {', '.join(sorted(ALLOWED_ROLES))}"
        )

    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    # Prevent admin from demoting themselves to avoid lockout
    if str(user.id) == str(current_user["user_id"]) and role_update.role != "admin":
        raise HTTPException(
            status_code=400,
            detail="Tidak dapat mengubah role admin sendiri"
        )

    user.role = role_update.role
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "id": str(user.id),
        "name": user.username,
        "email": user.email,
        "role": user.role
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(check_permissions("admin"))
):
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    if str(user.id) == str(current_user["user_id"]):
        raise HTTPException(
            status_code=400,
            detail="Tidak dapat menghapus akun sendiri"
        )

    await db.delete(user)
    await db.commit()

    return {"detail": "User berhasil dihapus", "id": str(user_id)}


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