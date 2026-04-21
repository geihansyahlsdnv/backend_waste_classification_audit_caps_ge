import uuid
from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles
import os
from datetime import datetime

from ...db.session import get_db
from ...db.models import ClassificationResult
from ...schemas.classification import ClassificationResponse, BatchClassificationResponse
from ...core.security import get_current_user, check_permissions
from ...services.inference import inference_service
from ...services.minio_client import minio_client

router = APIRouter()

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def validate_image(file: UploadFile) -> None:
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Format file tidak didukung. Gunakan: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Ukuran file terlalu besar. Maksimum: {MAX_FILE_SIZE/1024/1024}MB"
        )

@router.post(
    "/classify",
    response_model=ClassificationResponse,
    dependencies=[Depends(check_permissions("admin", "supervisor", "operator"))]
)
async def classify_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    validate_image(file)
    contents = await file.read()
    label, confidence, processing_time = await inference_service.predict(contents)
    
    image_url = None
    if confidence > 0.8:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        object_name = f"classifications/{current_user['user_id']}/{timestamp}_{file.filename}"
        temp_path = f"/tmp/{uuid.uuid4()}_{file.filename}"
        
        async with aiofiles.open(temp_path, "wb") as f:
            await f.write(contents)
        
        image_url = await minio_client.upload_file(temp_path, object_name, file.content_type)
        os.remove(temp_path)
    
    result = ClassificationResult(
        user_id=current_user["user_id"],
        label=label,
        confidence=confidence,
        image_url=image_url,
        processing_time_ms=processing_time
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)
    return result

@router.post(
    "/classify/batch",
    response_model=BatchClassificationResponse,
    dependencies=[Depends(check_permissions("admin", "supervisor"))]
)
async def classify_multiple_images(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maksimum 10 file per batch")
    
    start_time = datetime.utcnow()
    results = []
    
    for file in files:
        result = await classify_image(file, current_user, db)
        results.append(result)
    
    total_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    return BatchClassificationResponse(
        total_count=len(results),
        processing_time_ms=total_time,
        results=results
    )