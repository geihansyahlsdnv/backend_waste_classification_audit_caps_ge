import uuid
from typing import List
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Request
import os
import aiofiles
import json
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from ...db.session import get_db
from ...db.models import ClassificationResult, Detection
from ...services.inference import inference_service
from ...core.security import check_permissions

router = APIRouter()

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

def validate_image(file: UploadFile) -> None:
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Format tidak didukung")

@router.post("/detect")
async def detect_image(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(check_permissions("operator", "admin", "supervisor"))
):
    try:
        validate_image(file)
        contents = await file.read()

        # Panggil AI YOLO lo
        label, confidence, processing_time, detections_data = await inference_service.predict(contents)

        audit_id = uuid.uuid4()
        ext = file.filename.split(".")[-1].lower()
        filename = f"audit-{audit_id}.{ext}"
        filepath = os.path.join("uploads", filename)
        
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(contents)
            
        base_url = str(request.base_url).rstrip('/')
        image_url = f"{base_url}/uploads/{filename}"
        
        # Save to DB
        result = ClassificationResult(
            id=audit_id,
            user_id=current_user["user_id"],
            label=label,
            confidence=confidence,
            image_url=image_url,
            processing_time_ms=processing_time,
            timestamp=datetime.utcnow()
        )
        db.add(result)
        
        response_detections = []
        for det in detections_data:
            detection_id = uuid.uuid4()
            d = Detection(
                id=detection_id,
                result_id=audit_id,
                label=det["label"],
                confidence=det["confidence"],
                box_2d=det["box_2d"]
            )
            db.add(d)
            
            box_coords = json.loads(det["box_2d"])
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
            
        await db.commit()
        
        return {
            "audit_id": str(audit_id),
            "image_url": image_url,
            "top_prediction": label,
            "created_at": result.timestamp.isoformat() + "Z",
            "detections": response_detections
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
