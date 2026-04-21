import pytest
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token
)
from app.core.config import settings

def test_password_hashing():
    """Test password hashing dan verifikasi"""
    password = "mypassword123"
    
    # Test hashing
    hashed = get_password_hash(password)
    assert hashed != password
    assert len(hashed) > 0
    
    # Test verifikasi
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)

def test_jwt_token_creation():
    """Test pembuatan JWT token"""
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    role = "operator"
    
    # Test token creation
    token = create_access_token(user_id, role)
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Decode and verify token
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
    
    assert payload["sub"] == user_id
    assert payload["role"] == role
    assert "exp" in payload

def test_jwt_token_expiration():
    """Test expirasi JWT token"""
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    role = "operator"
    
    # Create expired token
    expires_delta = timedelta(minutes=-1)
    token = create_access_token(user_id, role, expires_delta)
    
    # Verify token raises error
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    
    assert exc_info.value.status_code == 401

def test_invalid_token():
    """Test invalid token handling"""
    # Test invalid token format
    with pytest.raises(HTTPException) as exc_info:
        decode_token("invalid.token.format")
    
    assert exc_info.value.status_code == 401
    
    # Test tampered token
    with pytest.raises(HTTPException) as exc_info:
        decode_token("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzb21lIjoicGF5bG9hZCJ9.tampered")