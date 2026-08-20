import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.database import get_db
from app.models import Reading, Station
from app.schemas import PredictionOut
from app import ml_model


router = APIRouter(
    prefix="/predict",
    tags=["predict"],
    dependencies=[Depends(require_api_key)],
)


@router.get("/{station_name}", response_model=PredictionOut)
def predict_station(
    station_name: str,
    db: Session = Depends(get_db),
):
    """
    Forecast the next 6-hourly groundwater level for a station.

    Uses the latest 30 processed readings and station metadata
    to rebuild the features required by the ML model.
    """

    rows = (
        db.query(Reading, Station)
        .join(Station, Reading.station_id == Station.id)
        .filter(Station.name == station_name)
        .order_by(Reading.timestamp.desc())
        .limit(30)
        .all()
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No readings found for '{station_name}'",
        )

    history = pd.DataFrame([
        {
            "timestamp": reading.timestamp,
            "gw_level": reading.gw_level,
            "latitude": station.latitude,
            "longitude": station.longitude,
            "rl_msl": station.rl_msl,
        }
        for reading, station in rows
    ])

    try:
        result = ml_model.predict_next(station_name, history)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}",
        )

    return PredictionOut(
        station=station_name,
        last_known_timestamp=history["timestamp"].max(),
        last_known_level=result["last_known_level"],
        predicted_next_level=result["predicted_next_level"],
        predicted_change=result["predicted_change"],
    )