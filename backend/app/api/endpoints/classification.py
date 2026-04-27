import uuid
from typing import List
from fastapi import APIRouter, File, UploadFile, HTTPException
import os

# Import service inti saja, jangan import model DB dulu karena lagi error
from ...services.inference import inference_service

router = APIRouter()

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

def validate_image(file: UploadFile) -> None:
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Format tidak didukung")

@router.post("/classify")
async def classify_image(file: UploadFile = File(...)):
    try:
        validate_image(file)
        contents = await file.read()

        # Panggil AI YOLO lo
        label, confidence, processing_time, detections_data = await inference_service.predict(contents)

        # Susun response manual (Tanpa simpan ke Database)
        return {
            "status": "success",
            "data": {
                "id": str(uuid.uuid4()),
                "label": label,
                "confidence": float(confidence),
                "processing_time_ms": processing_time,
                "detections": detections_data
            }
        }
    except Exception as e:
        # Biar ketahuan kalau AI-nya yang error
        return {"status": "error", "message": str(e)}