import uuid
from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Request, Query
import os
import aiofiles
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from ...db.session import get_db
from ...db.models import ClassificationResult, Detection, WasteType
from ...services.inference import inference_service
from ...core.security import check_permissions

router = APIRouter()

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}


def validate_image(file: UploadFile) -> None:
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Format tidak didukung")


async def _lookup_waste_type(db: AsyncSession, label: str) -> Optional[WasteType]:
    """Look up a WasteType row by its name (case-insensitive). Returns None if not found."""
    if not label:
        return None
    return await db.scalar(
        select(WasteType).where(WasteType.name.ilike(label))
    )


@router.post("/detect")
async def detect_image(
    request: Request,
    file: UploadFile = File(...),
    preview: bool = Query(
        False,
        description="If true, run inference only. Do not save image to disk or write to DB. "
                    "Used for real-time / live preview frames so storage and history aren't polluted."
    ),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(check_permissions("operator", "admin", "supervisor"))
):
    try:
        validate_image(file)
        contents = await file.read()

        # Run inference (always required)
        label, confidence, processing_time, detections_data = await inference_service.predict(contents)

        # Try to link the top label to a waste_type row.
        # Returns None when the waste_type table is empty or has no matching entry,
        # in which case price info will be null in the response.
        waste_type = await _lookup_waste_type(db, label)
        waste_type_id = waste_type.id if waste_type else None
        price_per_unit = waste_type.current_price if waste_type else None
        currency = waste_type.currency if waste_type else None
        unit = waste_type.unit if waste_type else None

        # Build detections response (same shape for both preview and full mode)
        response_detections = []
        for det in detections_data:
            box_coords = json.loads(det["box_2d"]) if isinstance(det["box_2d"], str) else det["box_2d"]
            response_detections.append({
                "label": det["label"],
                "confidence": det["confidence"],
                "bbox": {
                    "x1": box_coords[0],
                    "y1": box_coords[1],
                    "x2": box_coords[2],
                    "y2": box_coords[3]
                }
            })

        # PREVIEW MODE: skip disk write and DB persistence entirely
        if preview:
            return {
                "audit_id": None,
                "image_url": None,
                "top_prediction": label,
                "confidence": confidence,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "detections": response_detections,
                "pricing": {
                    "waste_type_id": str(waste_type_id) if waste_type_id else None,
                    "price_per_unit": float(price_per_unit) if price_per_unit is not None else None,
                    "currency": currency,
                    "unit": unit,
                },
                "preview": True
            }

        # FULL MODE: persist image, save classification result, save detections
        audit_id = uuid.uuid4()
        ext = file.filename.split(".")[-1].lower()
        filename = f"audit-{audit_id}.{ext}"
        filepath = os.path.join("uploads", filename)

        async with aiofiles.open(filepath, "wb") as f:
            await f.write(contents)

        base_url = str(request.base_url).rstrip('/')
        image_url = f"{base_url}/uploads/{filename}"

        result = ClassificationResult(
            id=audit_id,
            user_id=current_user["user_id"],
            waste_type_id=waste_type_id,
            label=label,
            confidence=confidence,
            image_url=image_url,
            processing_time_ms=processing_time,
            timestamp=datetime.utcnow()
        )
        db.add(result)

        for det in detections_data:
            box_coords = json.loads(det["box_2d"]) if isinstance(det["box_2d"], str) else det["box_2d"]
            d = Detection(
                id=uuid.uuid4(),
                result_id=audit_id,
                label=det["label"],
                confidence=det["confidence"],
                box_2d=box_coords
            )
            db.add(d)

        await db.commit()

        return {
            "audit_id": str(audit_id),
            "image_url": image_url,
            "top_prediction": label,
            "confidence": confidence,
            "created_at": result.timestamp.isoformat() + "Z",
            "detections": response_detections,
            "pricing": {
                "waste_type_id": str(waste_type_id) if waste_type_id else None,
                "price_per_unit": float(price_per_unit) if price_per_unit is not None else None,
                "currency": currency,
                "unit": unit,
            },
            "preview": False
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))