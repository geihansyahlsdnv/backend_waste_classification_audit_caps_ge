import asyncio
import pytest
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool
import os
from datetime import datetime
import uuid

from app.main import app
from app.db.base_class import Base
from app.db.session import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.db.models import User, ClassificationResult

# Test database URL
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

# Create async engine for testing
engine_test = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

# Test database session
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine_test) as session:
        yield session

# Override the database dependency
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def setup_database():
    """Set up test database"""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def client(setup_database) -> Generator:
    """Create a test client"""
    with TestClient(app) as c:
        yield c

@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Get test database session"""
    async with AsyncSession(engine_test) as session:
        yield session

@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Create a test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$LQVqGvHSCXY6GBcYHp0QOOYCZRJkNEFhh8EX4TDD1QAcPOAlZ7mIi",  # "password123"
        role="operator"
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user

@pytest.fixture
def test_token(test_user: User) -> str:
    """Create a test JWT token"""
    return create_access_token(
        user_id=test_user.id,
        role=test_user.role
    )

@pytest.fixture
async def test_admin(test_db: AsyncSession) -> User:
    """Create a test admin user"""
    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password="$2b$12$LQVqGvHSCXY6GBcYHp0QOOYCZRJkNEFhh8EX4TDD1QAcPOAlZ7mIi",
        role="admin"
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin

@pytest.fixture
def test_image() -> bytes:
    """Create a test image"""
    # Create a small valid image for testing
    from PIL import Image
    import io
    
    img = Image.new('RGB', (100, 100), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()

@pytest.fixture
async def test_classification(
    test_db: AsyncSession,
    test_user: User
) -> ClassificationResult:
    """Create a test classification result"""
    result = ClassificationResult(
        user_id=test_user.id,
        label="recyclable",
        confidence=0.95,
        processing_time_ms=150,
        timestamp=datetime.utcnow()
    )
    test_db.add(result)
    await test_db.commit()
    await test_db.refresh(result)
    return result