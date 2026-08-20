from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.database import get_db
from app.models import Reading, Station
from app.schemas import ReadingOut

router = APIRouter(
    prefix="/readings",
    tags=["readings"],
    dependencies=[Depends(require_api_key)],
)


@router.get("/{station_name}", response_model=list[ReadingOut])
def get_readings(
    station_name: str,
    limit: int = Query(
        200,
        le=5000,
        description="max rows to return, most recent first",
    ),
    since: datetime | None = Query(
        None,
        description="only readings at/after this ISO timestamp",
    ),
    db: Session = Depends(get_db),
):
    """Historical processed readings for a station."""

    q = (
        db.query(Reading)
        .join(Station, Reading.station_id == Station.id)
        .filter(Station.name == station_name)
    )

    if since:
        q = q.filter(Reading.timestamp >= since)

    rows = (
        q.order_by(Reading.timestamp.desc())
        .limit(limit)
        .all()
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No readings found for '{station_name}'",
        )

    return [
        ReadingOut(
            station=station_name,
            timestamp=row.timestamp,
            gw_level=row.gw_level,
        )
        for row in reversed(rows)
    ]


@router.get("/{station_name}/latest", response_model=ReadingOut)
def get_latest_reading(
    station_name: str,
    db: Session = Depends(get_db),
):
    """Return the latest processed reading for a station."""

    row = (
        db.query(Reading)
        .join(Station, Reading.station_id == Station.id)
        .filter(Station.name == station_name)
        .order_by(Reading.timestamp.desc())
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No readings found for '{station_name}'",
        )

    return ReadingOut(
        station=station_name,
        timestamp=row.timestamp,
        gw_level=row.gw_level,
    )