from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db
from models import User, UserRole
from routers.auth import get_current_user
from typing import List, Dict

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/predictive-maintenance")
async def predictive_maintenance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Identify hotspots for predictive maintenance.
    Aggregates reports by location and category to find recurring issues.
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Query to find clusters of reports (simplified for MVP)
    # In a real app, use PostGIS ST_ClusterDBSCAN
    query = text("""
        SELECT 
            category,
            COUNT(*) as count,
            AVG(ST_X(location::geometry)) as avg_lon,
            AVG(ST_Y(location::geometry)) as avg_lat
        FROM reports
        WHERE created_at > NOW() - INTERVAL '30 days'
        GROUP BY category
        HAVING COUNT(*) > 2
        ORDER BY count DESC
    """)
    
    result = await db.execute(query)
    hotspots = []
    for row in result:
        hotspots.append({
            "category": row.category,
            "report_count": row.count,
            "location": {"lat": row.avg_lat, "lon": row.avg_lon},
            "recommendation": f"Schedule maintenance for {row.category} in this area."
        })
        
    return {"hotspots": hotspots}
