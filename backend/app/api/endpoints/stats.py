from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from datetime import datetime, timedelta

from ...db.session import get_db
from ...db.models import ClassificationResult, User
from ...schemas.stats import UserStats, GlobalStats, DailyStats
from ...core.security import get_current_user, check_permissions
from ...services.redis_service import redis_service

router = APIRouter()

@router.get("/stats/me", response_model=UserStats, dependencies=[Depends(check_permissions("admin", "supervisor", "operator"))])
async def get_user_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    cache_key = f"stats:user:{current_user['user_id']}"
    cached = await redis_service.get(cache_key)
    if cached:
        return UserStats(**cached)
    
    query = select(
        func.count().label("total"),
        func.sum(case((ClassificationResult.label == "recyclable", 1), else_=0)).label("recyclable"),
        func.sum(case((ClassificationResult.label == "non-recyclable", 1), else_=0)).label("non_recyclable"),
        func.avg(ClassificationResult.confidence).label("avg_confidence"),
        func.avg(ClassificationResult.processing_time_ms).label("avg_processing")
    ).where(ClassificationResult.user_id == current_user["user_id"])
    
    result = await db.execute(query)
    stats = result.first()
    
    user_stats = UserStats(
        total_classifications=stats.total or 0,
        recyclable_count=stats.recyclable or 0,
        non_recyclable_count=stats.non_recyclable or 0,
        avg_confidence=float(stats.avg_confidence or 0),
        avg_processing_time=float(stats.avg_processing or 0)
    )
    
    await redis_service.set(cache_key, user_stats.dict(), 300)
    return user_stats

@router.get("/stats/global", response_model=GlobalStats, dependencies=[Depends(check_permissions("admin", "supervisor"))])
async def get_global_stats(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db)
):
    cache_key = f"stats:global:{days}"
    cached = await redis_service.get(cache_key)
    if cached:
        return GlobalStats(**cached)
    
    total_users = await db.scalar(select(func.count()).select_from(User))
    
    stats_query = select(
        func.count().label("total"),
        func.sum(case((ClassificationResult.label == "recyclable", 1), else_=0)).label("recyclable"),
        func.sum(case((ClassificationResult.label == "non-recyclable", 1), else_=0)).label("non_recyclable"),
        func.avg(ClassificationResult.confidence).label("avg_confidence"),
        func.avg(ClassificationResult.processing_time_ms).label("avg_processing")
    ).select_from(ClassificationResult)
    
    result = await db.execute(stats_query)
    stats = result.first()
    
    total = stats.total or 0
    recyclable = stats.recyclable or 0
    non_recyclable = stats.non_recyclable or 0
    
    start_date = datetime.utcnow() - timedelta(days=days)
    daily_query = select(
        func.date(ClassificationResult.timestamp).label("date"),
        func.count().label("total"),
        func.sum(case((ClassificationResult.label == "recyclable", 1), else_=0)).label("recyclable"),
        func.sum(case((ClassificationResult.label == "non-recyclable", 1), else_=0)).label("non_recyclable"),
        func.avg(ClassificationResult.confidence).label("avg_confidence")
    ).where(
        ClassificationResult.timestamp >= start_date
    ).group_by(
        func.date(ClassificationResult.timestamp)
    ).order_by(
        func.date(ClassificationResult.timestamp).desc()
    )
    
    daily_results = await db.execute(daily_query)
    daily_stats = [
        DailyStats(
            date=row.date,
            total_classifications=row.total,
            recyclable_count=row.recyclable or 0,
            non_recyclable_count=row.non_recyclable or 0,
            avg_confidence=float(row.avg_confidence or 0)
        )
        for row in daily_results
    ]
    
    global_stats = GlobalStats(
        total_users=total_users,
        total_classifications=total,
        recyclable_percentage=recyclable / total * 100 if total > 0 else 0,
        non_recyclable_percentage=non_recyclable / total * 100 if total > 0 else 0,
        avg_confidence=float(stats.avg_confidence or 0),
        avg_processing_time=float(stats.avg_processing or 0),
        daily_stats=daily_stats
    )
    
    await redis_service.set(cache_key, global_stats.dict(), 300)
    return global_stats