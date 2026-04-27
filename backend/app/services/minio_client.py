from typing import Optional
from minio import Minio
from minio.error import S3Error
import os
import aiohttp
import asyncio
from fastapi import HTTPException

from ..core.config import settings

class MinioClient:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        # self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            raise HTTPException(status_code=500, detail=f"Gagal membuat bucket: {str(e)}")
    
    async def download_model(self, model_path: str, version: str = "latest") -> str:
        try:
            local_path = f"/tmp/models/{version}"
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.client.fget_object(self.bucket_name, f"{model_path}_{version}", local_path)
            return local_path
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise HTTPException(status_code=404, detail=f"Model version {version} tidak ditemukan")
            raise HTTPException(status_code=500, detail=f"Gagal mengunduh model: {str(e)}")
    
    async def upload_file(self, file_path: str, object_name: str, content_type: Optional[str] = None) -> str:
        try:
            self.client.fput_object(self.bucket_name, object_name, file_path, content_type=content_type)
            return f"{settings.MINIO_ENDPOINT}/{self.bucket_name}/{object_name}"
        except S3Error as e:
            raise HTTPException(status_code=500, detail=f"Gagal mengupload file: {str(e)}")
    
    async def get_model_versions(self, model_path: str) -> list[str]:
        try:
            objects = self.client.list_objects(self.bucket_name, prefix=model_path)
            versions = []
            for obj in objects:
                name = obj.object_name
                if name.startswith(model_path):
                    version = name.replace(f"{model_path}_", "")
                    versions.append(version)
            return versions
        except S3Error as e:
            raise HTTPException(status_code=500, detail=f"Gagal mendapatkan versi model: {str(e)}")

minio_client = MinioClient()