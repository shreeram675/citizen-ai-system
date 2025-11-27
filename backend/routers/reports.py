from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from geoalchemy2 import WKTElement
from geoalchemy2.shape import to_shape
from typing import List, Optional
import httpx
import os
from database import get_db
from models import Report, User, UserRole, ReportStatus, ReportSeverity, Department, FieldTeam
from schemas import ReportCreate, ReportResponse, ReportUpdate
from routers.auth import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])

# AI Service URLs
AI_DUPLICATE_URL = os.getenv("AI_DUPLICATE_URL", "http://ai-duplicate:9001")

async def auto_assign_department(category: str, db: AsyncSession) -> Optional[int]:
    """Map category to department."""
    # Simple mapping for MVP
    mapping = {
        "pothole": "Roads",
        "street_light": "Electrical",
        "garbage": "Sanitation",
        "flooding": "Drainage",
        "graffiti": "Sanitation"
    }
    dept_name = mapping.get(category)
    if dept_name:
        result = await db.execute(select(Department).where(Department.name == dept_name))
        dept = result.scalars().first()
        if dept:
            return dept.id
    return None

async def predict_severity(text: str) -> ReportSeverity:
    """Predict severity using AI service."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_DUPLICATE_URL}/predict_severity",
                json={"text": text},
                timeout=5.0
            )
            if response.status_code == 200:
                result = response.json()
                severity_str = result['severity']
                # Map string to enum
                if severity_str in ReportSeverity.__members__:
                    return ReportSeverity[severity_str]
    except Exception as e:
        print(f"Severity prediction failed: {e}")

    # Fallback logic
    text_lower = text.lower()
    if "danger" in text_lower or "accident" in text_lower or "huge" in text_lower:
        return ReportSeverity.critical
    if "urgent" in text_lower:
        return ReportSeverity.high
    return ReportSeverity.medium

@router.post("/", response_model=ReportResponse)
async def create_report(
    report: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Create WKT point from lat/lon
    # Note: PostGIS uses (lon, lat) order for points
    location_wkt = f"POINT({report.longitude} {report.latitude})"
    
    # Auto-predict category if not provided or is generic
    predicted_category = report.category
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_DUPLICATE_URL}/predict_category",
                json={"text": f"{report.title}. {report.description}"},
                timeout=10.0
            )
            if response.status_code == 200:
                result = response.json()
                if result['confidence'] > 0.6:  # Only use if confident
                    predicted_category = result['category']
    except Exception as e:
        print(f"Category prediction failed: {e}")
    

    
    # Auto-assign Department
    department_id = await auto_assign_department(predicted_category, db)
    
    # Predict Severity
    severity = await predict_severity(f"{report.title}. {report.description}")

    new_report = Report(
        title=report.title,
        description=report.description,
        category=predicted_category,
        severity=severity,
        status=ReportStatus.pending,
        image_url=report.image_url,
        location=WKTElement(location_wkt, srid=4326),
        user_id=current_user.id,
        department_id=department_id
    )
    
    # TODO: Trigger AI duplicate check here (async task or direct call)
    # For now, we'll add it as a synchronous call for MVP
    try:
        async with httpx.AsyncClient() as client:
            # Get embedding for the new report
            embed_response = await client.post(
                f"{AI_DUPLICATE_URL}/embed",
                json={"text": f"{report.title}. {report.description}"},
                timeout=10.0
            )
            if embed_response.status_code == 200:
                embedding = embed_response.json()["embedding"]
                new_report.embedding = embedding
    except Exception as e:
        print(f"Embedding generation failed: {e}")
    
    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)
    return new_report

@router.get("/", response_model=List[ReportResponse])
async def get_reports(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius: Optional[float] = Query(None, description="Radius in meters"),
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Report)
    
    if category:
        query = query.where(Report.category == category)
        
    if lat is not None and lon is not None and radius is not None:
        # ST_DWithin takes geometry, geometry, distance_in_meters (if using geography type or appropriate projection)
        # Since we used Geometry(POINT, 4326), the unit is degrees. 
        # To use meters, we should cast to Geography or use ST_DistanceSphere (deprecated) or ST_DWithin with geography cast.
        # Best practice: cast to geography for meter-based distance.
        pt = WKTElement(f"POINT({lon} {lat})", srid=4326)
        query = query.where(
            func.ST_DWithin(
                Report.location.cast(func.geography),
                func.ST_GeogFromText(f"SRID=4326;POINT({lon} {lat})"),
                radius
            )
        )
    
    result = await db.execute(query)
    reports = result.scalars().all()
    
    # Convert WKT/Geometry to lat/lon for response
    # This is a bit manual, ideally we use a serializer or property
    # For MVP, we'll just let Pydantic handle it if we map it correctly, 
    # but the ReportResponse expects lat/lon which are not on the model.
    # We need to patch the response objects.
    
    response_reports = []
    for r in reports:
        # Extract lat/lon from WKT or use ST_X/ST_Y in query
        # For simplicity, we'll just return the object and let the frontend parse WKT if needed,
        # OR we can update the query to return lat/lon columns.
        # Let's update the query to fetch lat/lon explicitly if we want to be clean,
        # but for now let's just assume the frontend can handle it or we add properties to the model.
        
        # Use to_shape to parse WKBElement
        if r.location is not None:
            point = to_shape(r.location)
            r.latitude = point.y
            r.longitude = point.x
        else:
            r.latitude = 0.0
            r.longitude = 0.0
        
        response_reports.append(r)

    return response_reports

@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.location is not None:
        point = to_shape(report.location)
        report.latitude = point.y
        report.longitude = point.x
    else:
        report.latitude = 0.0
        report.longitude = 0.0
    return report

@router.post("/{report_id}/verify", response_model=ReportResponse)
async def verify_report(
    report_id: int,
    feedback: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Citizen verifies the resolution."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.user_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if report.status != ReportStatus.resolved:
        raise HTTPException(status_code=400, detail="Report is not in resolved state")

    report.status = ReportStatus.closed
    report.citizen_feedback = feedback
    await db.commit()
    await db.refresh(report)
    return report

@router.post("/{report_id}/reopen", response_model=ReportResponse)
async def reopen_report(
    report_id: int,
    feedback: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Citizen rejects resolution and reopens report."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.user_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    report.status = ReportStatus.reopened
    report.citizen_feedback = feedback
    await db.commit()
    await db.refresh(report)
    return report
