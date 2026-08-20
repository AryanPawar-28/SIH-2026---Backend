"""
Wraps the trained XGBoost model (gw_model.json) and knows how to turn the
latest known readings for a station into a feature row the model can
score — i.e. it reproduces, at inference time, the same feature
engineering the ML teammate did offline in train_model.py.
"""
import math
from datetime import timedelta

import numpy as np
import pandas as pd
import xgboost as xgb

from app.config import MODEL_PATH

_model: xgb.XGBRegressor | None = None
_feature_names: list[str] | None = None


def load_model() -> xgb.XGBRegressor:
    """Load once at app startup and cache in module scope."""
    global _model, _feature_names
    if _model is None:
        _model = xgb.XGBRegressor()
        _model.load_model(MODEL_PATH)
        # feature_names is the exact column order the model was trained on
        # (including every station_<name> one-hot column) — pull it straight
        # from the saved model instead of hardcoding, so we can never drift
        # out of sync with train_model.py.
        _feature_names = _model.get_booster().feature_names
    return _model


def get_feature_names() -> list[str]:
    if _feature_names is None:
        load_model()
    return _feature_names


def _is_monsoon(month: int) -> int:
    # Same convention used when the CSV was built: Jun-Sep = monsoon in Assam
    return 1 if month in (6, 7, 8, 9) else 0


def build_next_step_features(station: str, history: pd.DataFrame) -> pd.DataFrame:
    """
    history: DataFrame of the station's readings, ascending by timestamp,
             must include at least the last 30 rows (fewer is OK, just
             less accurate for the rolling features) with columns:
             timestamp, gw_level, latitude, longitude, rl_msl

    Returns a single-row DataFrame with columns in the exact order the
    model expects, ready for model.predict().
    """
    if len(history) < 4:
        raise ValueError(f"Need at least 4 historical readings for '{station}' to forecast, "
                          f"only have {len(history)}")

    history = history.sort_values("timestamp").reset_index(drop=True)
    last = history.iloc[-1]
    next_ts = last["timestamp"] + timedelta(hours=6)  # data is 6-hourly

    lag_1 = float(last["gw_level"])
    lag_4 = float(history.iloc[-4]["gw_level"]) if len(history) >= 4 else lag_1

    window_7 = history["gw_level"].tail(7)
    window_30 = history["gw_level"].tail(30)
    roll_mean_7d = float(window_7.mean())
    roll_std_7d = float(window_7.std(ddof=0)) if len(window_7) > 1 else 0.0
    roll_mean_30d = float(window_30.mean())

    month = next_ts.month
    doy = next_ts.timetuple().tm_yday

    row = {
        "lag_1": lag_1,
        "lag_4": lag_4,
        "roll_mean_7d": roll_mean_7d,
        "roll_std_7d": roll_std_7d,
        "roll_mean_30d": roll_mean_30d,
        "month_sin": math.sin(2 * math.pi * month / 12),
        "month_cos": math.cos(2 * math.pi * month / 12),
        "doy_sin": math.sin(2 * math.pi * doy / 365),
        "doy_cos": math.cos(2 * math.pi * doy / 365),
        "is_monsoon": _is_monsoon(month),
        "Hour": next_ts.hour,
        "DayOfWeek": next_ts.weekday(),
        "Latitude": float(last["latitude"]),
        "Longitude": float(last["longitude"]),
        "RL_MSL": float(last["rl_msl"]),
    }

    # one-hot station columns — set the current station to True, rest False
    feature_names = get_feature_names()
    for col in feature_names:
        if col.startswith("station_"):
            row[col] = 1 if col == f"station_{station}" else 0

    # order columns EXACTLY as the model expects
    ordered = {col: row[col] for col in feature_names}
    return pd.DataFrame([ordered]), next_ts


def predict_next(station: str, history: pd.DataFrame) -> dict:
    model = load_model()
    features_df, next_ts = build_next_step_features(station, history)
    pred = float(model.predict(features_df)[0])
    last_level = float(history.sort_values("timestamp").iloc[-1]["gw_level"])
    return {
        "predicted_next_level": pred,
        "next_timestamp": next_ts,
        "last_known_level": last_level,
        "predicted_change": pred - last_level,
    }
