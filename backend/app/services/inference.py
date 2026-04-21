from typing import Optional, Tuple
import time
import torch
from ultralytics import YOLO
from PIL import Image
import io
import logging
from fastapi import HTTPException

from .model_manager import model_manager

logger = logging.getLogger(__name__)

class InferenceService:
    def __init__(self):
        self.model: Optional[YOLO] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    async def load_model(self):
        if not model_manager.model_path:
            raise HTTPException(status_code=500, detail="Model belum diunduh dari MinIO")
        
        try:
            self.model = YOLO(model_manager.model_path)
            self.model.to(self.device)
            if self.device == "cuda":
                torch.cuda.synchronize()
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Gagal memuat model: {str(e)}")
    
    async def predict(self, image_bytes: bytes) -> Tuple[str, float, int]:
        if not self.model:
            raise HTTPException(status_code=500, detail="Model belum dimuat")
        
        try:
            start_time = time.time()
            image = Image.open(io.BytesIO(image_bytes))
            
            with torch.no_grad():
                results = self.model(image)[0]
            
            if len(results.boxes) == 0:
                raise HTTPException(status_code=400, detail="Tidak ada objek yang terdeteksi")
            
            confidence = float(results.boxes.conf[0])
            class_id = int(results.boxes.cls[0])
            label = "recyclable" if class_id == 0 else "non-recyclable"
            processing_time = int((time.time() - start_time) * 1000)
            
            return label, confidence, processing_time
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal melakukan inferensi: {str(e)}")
    
    def get_model_info(self) -> dict:
        if not self.model:
            return {
                "status": "not_loaded",
                "device": self.device,
                "version": None
            }
        
        return {
            "status": "loaded",
            "device": self.device,
            "version": model_manager.current_version
        }

inference_service = InferenceService()