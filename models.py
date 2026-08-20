from sqlalchemy import Column, Integer, Float, String, DateTime, Index
from app.database import Base


class Station(Base):
    """One row per station — static metadata, used to populate /stations
    and to draw markers on the dashboard map."""
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    district = Column(String)
    tehsil = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    rl_msl = Column(Float)


class Reading(Base):
    """Every 6-hourly reading, already cleaned + feature-engineered by the
    data teammate (lag/rolling/seasonal columns already computed in the CSV).
    This is the 'processed_readings' table from the system-flow diagram."""
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)
    station = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)

    gw_level = Column(Float, nullable=False)  # target column
    latitude = Column(Float)
    longitude = Column(Float)
    rl_msl = Column(Float)

    lag_1 = Column(Float)
    lag_4 = Column(Float)
    roll_mean_7d = Column(Float)
    roll_std_7d = Column(Float)
    roll_mean_30d = Column(Float)
    month_sin = Column(Float)
    month_cos = Column(Float)
    doy_sin = Column(Float)
    doy_cos = Column(Float)
    is_monsoon = Column(Integer)
    hour = Column(Integer)
    day_of_week = Column(Integer)

    __table_args__ = (
        Index("ix_station_timestamp", "station", "timestamp"),
    )
