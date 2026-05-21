from typing import Optional, Tuple, List, Dict, Any
import time
import torch
import os
from ultralytics import YOLO
from PIL import Image
import io
import logging
import json
from fastapi import HTTPException

from .model_manager import model_manager

logger = logging.getLogger(__name__)

class InferenceService:
    def __init__(self):
        self.model: Optional[YOLO] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    async def load_model(self):
        """
        Memuat model YOLOv8. 
        Memprioritaskan file lokal best.pt di root folder sebelum mengecek model_manager.
        """
        # Mendapatkan path absolut ke file best.pt di root folder backend
        # Karena file ini ada di app/services/inference.py, kita naik 2 tingkat ke root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        local_model_path = os.path.join(base_dir, "best.pt")

        target_path = None

        # Cek apakah best.pt ada di root
        if os.path.exists(local_model_path):
            logger.info(f"Menggunakan model lokal yang ditemukan di: {local_model_path}")
            target_path = local_model_path
        elif model_manager.model_path:
            logger.info(f"Menggunakan model dari model_manager: {model_manager.model_path}")
            target_path = model_manager.model_path
        else:
            logger.error("Model tidak ditemukan secara lokal maupun di MinIO.")
            raise HTTPException(
                status_code=500, 
                detail="Model (best.pt) tidak ditemukan. Pastikan file ada di root folder backend."
            )
        
        try:
            # Muat model menggunakan library Ultralytics
            self.model = YOLO(target_path)
            self.model.to(self.device)
            
            if self.device == "cuda":
                torch.cuda.synchronize()
            
            logger.info(f"Model successfully loaded on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Gagal memuat model: {str(e)}")
    
    async def predict(self, image_bytes: bytes) -> Tuple[str, float, int, List[Dict[str, Any]]]:
        if not self.model:
            raise HTTPException(status_code=500, detail="Model belum dimuat")
        
        try:
            start_time = time.time()
            try:
                image = Image.open(io.BytesIO(image_bytes))
            except Exception:
                raise HTTPException(status_code=400, detail="File bukan gambar yang valid")
            
            # Jalankan inferensi
            with torch.no_grad():
                results = self.model(image)[0]
            
            if len(results.boxes) == 0:
                raise HTTPException(status_code=400, detail="Tidak ada objek yang terdeteksi")
            
            detections_data = []
            for box in results.boxes:
                coords = box.xyxy[0].tolist()
                detection_item = {
                    "label": self.model.names[int(box.cls[0])],
                    "confidence": float(box.conf[0]),
                    "box_2d": json.dumps([round(c, 2) for c in coords])
                }
                detections_data.append(detection_item)

            # Ambil deteksi terbaik (index 0 biasanya score tertinggi)
            best_box = results.boxes[0]
            confidence = float(best_box.conf[0])
            class_id = int(best_box.cls[0])
            
            # Ambil label dinamis langsung dari model YOLO
            label = self.model.names[class_id]
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return label, confidence, processing_time, detections_data

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Inference error: {str(e)}")
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
            "version": getattr(model_manager, 'current_version', 'local')
        }

inference_service = InferenceService()