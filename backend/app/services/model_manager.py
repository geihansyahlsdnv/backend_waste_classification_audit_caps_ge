import asyncio
from typing import Optional
from fastapi import HTTPException

from .minio_client import minio_client
from ..core.config import settings

class ModelManager:
    def __init__(self):
        self.model_path: Optional[str] = None
        self.current_version: Optional[str] = None
    
    async def initialize(self):
        try:
            versions = await minio_client.get_model_versions("yolov8s")
            if not versions:
                raise HTTPException(status_code=500, detail="Tidak ada model yang tersedia di MinIO")
            
            latest_version = versions[-1]
            self.model_path = await minio_client.download_model("yolov8s", latest_version)
            self.current_version = latest_version
        except Exception as e:
            raise

model_manager = ModelManager()

async def init_minio():
    await model_manager.initialize()