import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Reading
from app.schemas import PredictionOut
from app import ml_model

router = APIRouter(prefix="/predict", tags=["predict"])


@router.get("/{station_name}", response_model=PredictionOut)
def predict_station(station_name: str, db: Session = Depends(get_db)):
    """Forecast the next 6-hourly groundwater level for a station, using
    the last 30 known readings to rebuild lag/rolling features live."""
    rows = (
        db.query(Reading)
        .filter(Reading.station == station_name)
        .order_by(Reading.timestamp.desc())
        .limit(30)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"No readings found for '{station_name}'")

    history = pd.DataFrame([{
        "timestamp": r.timestamp,
        "gw_level": r.gw_level,
        "latitude": r.latitude,
        "longitude": r.longitude,
        "rl_msl": r.rl_msl,
    } for r in rows])

    try:
        result = ml_model.predict_next(station_name, history)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PredictionOut(
        station=station_name,
        last_known_timestamp=history["timestamp"].max(),
        last_known_level=result["last_known_level"],
        predicted_next_level=result["predicted_next_level"],
        predicted_change=result["predicted_change"],
    )
