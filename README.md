# SIH25068 — Groundwater API (FastAPI backend)

Backend for the real-time groundwater level monitoring & forecasting system.
Loads the cleaned, feature-engineered CSV into a database, serves it and
the trained XGBoost model over a REST API for the React dashboard.

## 1. Setup

```bash
cd gw-backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Drop your teammates' files into place (already done if you got this as a zip):

```
data/gwl_27stations_final_clean.csv
models/gw_model.json
```

## 2. Load the data into the database

Uses SQLite by default (`gw.db`, created automatically — nothing to install).

```bash
python -m app.ingest
```

For the live demo, simulate a real-time feed instead (replays rows with a
delay between timestamps):

```bash
python -m app.ingest --replay 0.05
```

Re-running `ingest.py` always wipes and reloads, so it's safe to run again
any time the CSV changes.

### Switching to Postgres later
```bash
pip install psycopg2-binary
createdb gwdb
export DATABASE_URL="postgresql://gwuser:gwpass@localhost:5432/gwdb"
python -m app.ingest
```

## 3. Run the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs: http://localhost:8000/docs

## 4. Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/stations` | All station metadata (name, district, lat/long) |
| GET | `/stations/{name}` | One station's metadata |
| GET | `/readings/{name}?limit=200` | Historical readings, chronological |
| GET | `/readings/{name}/latest` | Most recent reading |
| GET | `/predict/{name}` | Forecast the next 6-hourly level |
| GET | `/alerts?std_multiplier=1.5` | Stations currently in depletion alert |
| GET | `/health` | Liveness check |

Example:
```bash
curl http://localhost:8000/predict/Khoirabari
```
```json
{
  "station": "Khoirabari",
  "last_known_timestamp": "2025-12-31T18:00:00",
  "last_known_level": -0.80,
  "predicted_next_level": -0.826,
  "predicted_change": -0.026
}
```

## 5. How `/predict` actually works

`gw_model.json` was trained on features like `lag_1`, `lag_4`,
`roll_mean_7d`, etc. — those don't exist yet for a future timestamp, so
`app/ml_model.py` rebuilds them live from the last 30 stored readings for
that station every time `/predict` is called (see
`build_next_step_features()`). This keeps inference in sync with
`train_model.py` by pulling the exact feature order from the saved model
(`model.get_booster().feature_names`) instead of hardcoding it — if the ML
teammate retrains with different features, this code doesn't silently
break, it'll just fail loudly with a clear KeyError.

## 6. How `/alerts` works

No ML — plain threshold logic on purpose (easy to explain to judges): a
station is flagged if its latest reading is more than `std_multiplier`
standard deviations below its own historical mean. Tune sensitivity with
the query param, e.g. `/alerts?std_multiplier=1.0` for more alerts.

## 7. File architecture

```
gw-backend/
├── app/
│   ├── main.py          # FastAPI app, CORS, startup (loads model once)
│   ├── config.py         # env-driven settings (DB url, paths, thresholds)
│   ├── database.py       # SQLAlchemy engine/session
│   ├── models.py         # ORM tables: Station, Reading
│   ├── schemas.py        # Pydantic response models
│   ├── ml_model.py       # loads gw_model.json, builds live features, predicts
│   ├── ingest.py         # CSV -> DB loader / --replay demo mode
│   └── routers/
│       ├── stations.py
│       ├── readings.py
│       ├── predict.py
│       └── alerts.py
├── data/gwl_27stations_final_clean.csv
├── models/gw_model.json
├── requirements.txt
├── .env.example
└── README.md
```

## 8. Handing off to the frontend teammate

Give them this base URL + the table above. Enable CORS is already wide open
(`CORS_ORIGINS=*`) for the hackathon — tighten it in `.env` if needed.

## 9. Still TODO for you

- [ ] Point `/predict` at a background job (or cron) so predictions are
      pre-computed instead of live-computed on every request, if latency
      matters on demo day.
- [ ] Add simple API-key auth if judges ask about security.
- [ ] Deploy: `uvicorn app.main:app --host 0.0.0.0 --port 8000` behind
      nginx, or just run it on the demo laptop.
