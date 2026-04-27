from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timedelta

from ...db.session import get_db
from ...db.models import ClassificationResult, Detection
from ...core.security import check_permissions

router = APIRouter()

@router.get("/reports/summary")
async def get_reports_summary(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(check_permissions("admin", "supervisor", "operator"))
):
    # Total audits
    total_audits = await db.scalar(select(func.count()).select_from(ClassificationResult))
    
    # Total objects (detections)
    total_objects = await db.scalar(select(func.count()).select_from(Detection))
    
    # Average confidence
    avg_conf = await db.scalar(select(func.avg(ClassificationResult.confidence)))
    
    # Category distribution (group by top_prediction)
    cat_dist_query = select(ClassificationResult.label, func.count()).group_by(ClassificationResult.label)
    cat_dist_result = await db.execute(cat_dist_query)
    
    category_distribution = []
    for row in cat_dist_result:
        category_distribution.append({"label": row[0], "count": row[1]})
        
    # Daily trend (last 7 days)
    start_date = datetime.utcnow() - timedelta(days=7)
    daily_query = select(
        func.date(ClassificationResult.timestamp).label("date"),
        func.count().label("count")
    ).where(
        ClassificationResult.timestamp >= start_date
    ).group_by(
        func.date(ClassificationResult.timestamp)
    ).order_by(
        func.date(ClassificationResult.timestamp).asc()
    )
    
    daily_results = await db.execute(daily_query)
    daily_trend = []
    for row in daily_results:
        daily_trend.append({"date": row[0].isoformat(), "count": row[1]})
        
    return {
        "total_audits": total_audits or 0,
        "total_objects": total_objects or 0,
        "average_confidence": round(float(avg_conf or 0), 2),
        "category_distribution": category_distribution,
        "daily_trend": daily_trend
    }