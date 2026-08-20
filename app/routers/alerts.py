from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.database import get_db
from app.models import Reading, Station
from app.schemas import AlertOut
from app.config import ALERT_STD_MULTIPLIER


router = APIRouter(
    prefix="/alerts",
    tags=["alerts"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=list[AlertOut])
def get_alerts(
    std_multiplier: float = Query(
        ALERT_STD_MULTIPLIER,
        description="how many std-devs below the historical mean counts as critical",
    ),
    db: Session = Depends(get_db),
):
    """
    A station is flagged when its latest reading falls more than
    `std_multiplier` standard deviations below its historical mean.

    This uses transparent threshold logic rather than ML.
    """

    # Get all stations from the stations table.
    stations = db.query(Station).order_by(Station.name).all()

    alerts = []

    for station in stations:

        # Historical mean and count for this station.
        stats = (
            db.query(
                func.avg(Reading.gw_level),
                func.count(Reading.gw_level),
            )
            .filter(Reading.station_id == station.id)
            .one()
        )

        mean_level, n = stats

        if n < 5 or mean_level is None:
            continue

        # Population variance/std deviation.
        variance_row = (
            db.query(
                func.avg(
                    (Reading.gw_level - mean_level)
                    * (Reading.gw_level - mean_level)
                )
            )
            .filter(Reading.station_id == station.id)
            .scalar()
        )

        std_level = (variance_row or 0) ** 0.5

        # Latest reading for this station.
        latest = (
            db.query(Reading)
            .filter(Reading.station_id == station.id)
            .order_by(Reading.timestamp.desc())
            .first()
        )

        if not latest or std_level == 0:
            continue

        threshold = mean_level - std_multiplier * std_level

        if latest.gw_level < threshold:

            deficit = (
                (threshold - latest.gw_level) / std_level
                if std_level
                else 0
            )

            severity = "high" if deficit > 1 else "medium"

            alerts.append(
                AlertOut(
                    station=station.name,
                    latest_level=round(latest.gw_level, 3),
                    historical_mean=round(mean_level, 3),
                    historical_std=round(std_level, 3),
                    threshold=round(threshold, 3),
                    timestamp=latest.timestamp,
                    severity=severity,
                )
            )

    # Worst depletion first.
    alerts.sort(
        key=lambda a: a.latest_level - a.threshold
    )

    return alerts