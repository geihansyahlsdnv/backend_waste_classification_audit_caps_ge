from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from ..core.config import settings
from .base_class import Base

# Create async engine optimized for PostgreSQL
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

async def init_db() -> None:
    """Initialize database, creating tables if they don't exist"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> Session:
    """Dependency for getting async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()