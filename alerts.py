from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Reading
from app.schemas import AlertOut
from app.config import ALERT_STD_MULTIPLIER

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def get_alerts(
    std_multiplier: float = Query(ALERT_STD_MULTIPLIER, description="how many std-devs below the historical mean counts as critical"),
    db: Session = Depends(get_db),
):
    """
    A station is flagged when its LATEST reading falls more than
    `std_multiplier` standard deviations below its own historical mean —
    i.e. it's depleting further than its normal seasonal range.
    This is simple threshold logic (no ML), by design — see the system
    flow doc: alerts should be transparent and easy to justify to judges.
    """
    stations = [r[0] for r in db.query(Reading.station).distinct().all()]
    alerts = []

    for station in stations:
        stats = (
            db.query(func.avg(Reading.gw_level), func.count(Reading.gw_level))
            .filter(Reading.station == station)
            .one()
        )
        mean_level, n = stats
        if n < 5 or mean_level is None:
            continue

        # population std (simple, no need for another round trip)
        variance_row = db.query(
            func.avg((Reading.gw_level - mean_level) * (Reading.gw_level - mean_level))
        ).filter(Reading.station == station).scalar()
        std_level = (variance_row or 0) ** 0.5

        latest = (
            db.query(Reading)
            .filter(Reading.station == station)
            .order_by(Reading.timestamp.desc())
            .first()
        )
        if not latest or std_level == 0:
            continue

        threshold = mean_level - std_multiplier * std_level
        if latest.gw_level < threshold:
            deficit = (threshold - latest.gw_level) / std_level if std_level else 0
            severity = "high" if deficit > 1 else "medium"
            alerts.append(AlertOut(
                station=station,
                latest_level=round(latest.gw_level, 3),
                historical_mean=round(mean_level, 3),
                historical_std=round(std_level, 3),
                threshold=round(threshold, 3),
                timestamp=latest.timestamp,
                severity=severity,
            ))

    # worst first
    alerts.sort(key=lambda a: a.latest_level - a.threshold)
    return alerts
