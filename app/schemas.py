from datetime import datetime
from pydantic import BaseModel


class StationOut(BaseModel):
    name: str
    district: str | None = None
    tehsil: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    rl_msl: float | None = None

    class Config:
        from_attributes = True


class ReadingOut(BaseModel):
    station: str
    timestamp: datetime
    gw_level: float

    class Config:
        from_attributes = True


class PredictionOut(BaseModel):
    station: str
    last_known_timestamp: datetime
    last_known_level: float
    predicted_next_level: float
    predicted_change: float


class AlertOut(BaseModel):
    station: str
    latest_level: float
    historical_mean: float
    historical_std: float
    threshold: float
    timestamp: datetime
    severity: str
