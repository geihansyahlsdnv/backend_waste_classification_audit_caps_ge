import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
import json
from datetime import datetime, timedelta

from app.db.models import User, ClassificationResult

async def test_register_user(client: TestClient, test_db: AsyncSession):
    """Test registrasi user baru"""
    response = client.post(
        "/auth/register",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
            "role": "operator"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"
    assert "id" in data
    
    # Verify user in database
    result = await test_db.get(User, data["id"])
    assert result is not None
    assert result.username == "newuser"

async def test_login(client: TestClient, test_user: User):
    """Test login user"""
    response = client.post(
        "/auth/login",
        json={
            "username": "testuser",
            "password": "password123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

async def test_classify_image(
    client: TestClient,
    test_token: str,
    test_image: bytes
):
    """Test klasifikasi gambar"""
    response = client.post(
        "/api/classify",
        files={"file": ("test.jpg", test_image, "image/jpeg")},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["label"] in ["recyclable", "non-recyclable"]
    assert isinstance(data["confidence"], float)
    assert isinstance(data["processing_time_ms"], int)

async def test_get_history(
    client: TestClient,
    test_token: str,
    test_classification: ClassificationResult
):
    """Test mengambil riwayat klasifikasi"""
    response = client.get(
        "/api/history",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["items"][0]["id"] == str(test_classification.id)

async def test_get_stats(
    client: TestClient,
    test_token: str,
    test_admin: User
):
    """Test mengambil statistik"""
    # Login sebagai admin
    admin_token = client.post(
        "/auth/login",
        json={
            "username": "admin",
            "password": "password123"
        }
    ).json()["access_token"]
    
    response = client.get(
        "/api/stats/global",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_users" in data
    assert "total_classifications" in data
    assert "daily_stats" in data

async def test_unauthorized_access(client: TestClient):
    """Test akses tanpa token"""
    endpoints = [
        "/api/classify",
        "/api/history",
        "/api/stats/global"
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 401

async def test_invalid_image(client: TestClient, test_token: str):
    """Test upload invalid image"""
    response = client.post(
        "/api/classify",
        files={"file": ("test.txt", b"not an image", "text/plain")},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 400