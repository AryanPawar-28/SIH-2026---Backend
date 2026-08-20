from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Reading
from app.schemas import ReadingOut

router = APIRouter(prefix="/readings", tags=["readings"])


@router.get("/{station_name}", response_model=list[ReadingOut])
def get_readings(
    station_name: str,
    limit: int = Query(200, le=5000, description="max rows to return, most recent first"),
    since: datetime | None = Query(None, description="only readings at/after this ISO timestamp"),
    db: Session = Depends(get_db),
):
    """Historical readings for a station — feeds the actual-vs-predicted chart."""
    q = db.query(Reading).filter(Reading.station == station_name)
    if since:
        q = q.filter(Reading.timestamp >= since)
    rows = q.order_by(Reading.timestamp.desc()).limit(limit).all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No readings found for '{station_name}'")
    return list(reversed(rows))  # chronological order for charting


@router.get("/{station_name}/latest", response_model=ReadingOut)
def get_latest_reading(station_name: str, db: Session = Depends(get_db)):
    row = (
        db.query(Reading)
        .filter(Reading.station == station_name)
        .order_by(Reading.timestamp.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"No readings found for '{station_name}'")
    return row
