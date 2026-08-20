"""
Loads gwl_27stations_final_clean.csv into the database.

Usage:
    python -m app.ingest                 # bulk load, as fast as possible
    python -m app.ingest --replay 0.05   # replay rows with a small delay
                                          # per timestamp step, to simulate
                                          # a live telemetry feed for the demo

Safe to re-run: it wipes and reloads the readings/stations tables each time,
so it always matches the CSV exactly.
"""
import argparse
import time

import pandas as pd
from sqlalchemy.orm import Session

from app.config import CSV_PATH
from app.database import Base, engine, SessionLocal
from app.models import Station, Reading

GW_COL = "Groundwater Level Telemetry 6 Hourly (meter)"


def load_csv() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, parse_dates=["Data Acquisition Time"])
    df = df.sort_values(["Station", "Data Acquisition Time"]).reset_index(drop=True)
    return df


def ingest_stations(db: Session, df: pd.DataFrame):
    meta = df.drop_duplicates(subset="Station", keep="last")
    for _, r in meta.iterrows():
        db.merge(Station(
            name=r["Station"],
            district=r.get("District"),
            tehsil=r.get("Tehsil"),
            latitude=r["Latitude"],
            longitude=r["Longitude"],
            rl_msl=r["RL_MSL"],
        ))
    db.commit()
    print(f"Loaded {len(meta)} stations")


def ingest_readings(db: Session, df: pd.DataFrame, replay_delay: float = 0.0):
    total = len(df)
    batch = []
    last_ts = None
    for i, r in df.iterrows():
        batch.append(Reading(
            station=r["Station"],
            timestamp=r["Data Acquisition Time"],
            gw_level=r[GW_COL],
            latitude=r["Latitude"],
            longitude=r["Longitude"],
            rl_msl=r["RL_MSL"],
            lag_1=r["lag_1"],
            lag_4=r["lag_4"],
            roll_mean_7d=r["roll_mean_7d"],
            roll_std_7d=r["roll_std_7d"],
            roll_mean_30d=r["roll_mean_30d"],
            month_sin=r["month_sin"],
            month_cos=r["month_cos"],
            doy_sin=r["doy_sin"],
            doy_cos=r["doy_cos"],
            is_monsoon=r["is_monsoon"],
            hour=r["Hour"],
            day_of_week=r["DayOfWeek"],
        ))

        if len(batch) >= 500:
            db.bulk_save_objects(batch)
            db.commit()
            print(f"  ...{i + 1}/{total} rows")
            batch = []

        if replay_delay and r["Data Acquisition Time"] != last_ts:
            time.sleep(replay_delay)
            last_ts = r["Data Acquisition Time"]

    if batch:
        db.bulk_save_objects(batch)
        db.commit()
    print(f"Loaded {total} readings")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", type=float, default=0.0,
                         help="seconds to sleep per unique timestamp, to simulate a live feed")
    args = parser.parse_args()

    print("Creating tables (if they don't exist)...")
    Base.metadata.create_all(bind=engine)

    df = load_csv()
    print(f"Read {len(df)} rows from {CSV_PATH}")

    db = SessionLocal()
    try:
        db.query(Reading).delete()
        db.query(Station).delete()
        db.commit()

        ingest_stations(db, df)
        ingest_readings(db, df, replay_delay=args.replay)
    finally:
        db.close()

    print("Done.")


if __name__ == "__main__":
    main()
