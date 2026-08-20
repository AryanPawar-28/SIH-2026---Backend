from sqlalchemy import Column, Integer, BigInteger, Float, String, DateTime, Index, ForeignKey, Boolean
from app.database import Base


class Station(Base):
    __tablename__ = "stations"

    id = Column("station_id", Integer, primary_key=True, index=True)
    name = Column("station_name", String, unique=True, index=True, nullable=False)
    district = Column(String)
    tehsil = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    rl_msl = Column(Float)

class Reading(Base):
    """Processed groundwater readings used by the dashboard and ML model."""
    __tablename__ = "processed_readings"

    id = Column(BigInteger, primary_key=True, index=True)

    station_id = Column(
        Integer,
        ForeignKey("stations.station_id"),
        nullable=False,
        index=True
    )

    timestamp = Column(
        "reading_time",
        DateTime,
        index=True,
        nullable=False
    )

    gw_level = Column(Float, nullable=False)

    lag_1 = Column(Float)
    lag_4 = Column(Float)
    roll_mean_7d = Column(Float)
    roll_std_7d = Column(Float)
    roll_mean_30d = Column(Float)

    month_sin = Column(Float)
    month_cos = Column(Float)
    doy_sin = Column(Float)
    doy_cos = Column(Float)

    is_monsoon = Column(Boolean)
    hour = Column(Integer)
    day_of_week = Column(Integer)

    __table_args__ = (
        Index(
            "ix_processed_station_timestamp",
            "station_id",
            "reading_time"
        ),
    )