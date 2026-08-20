# SIH25068 — Groundwater API (FastAPI backend)

Backend for the real-time groundwater level monitoring & forecasting system.
Loads the cleaned, feature-engineered CSV into a database, serves it and
the trained XGBoost model over a REST API for the React dashboard.

> **Fixes applied on top of the original zip — read this first.** Three
> bugs were found and fixed while wiring in Postgres + auth; all three
> would have broken the demo regardless of which database you use:
> 1. **Package structure was broken** — `main.py` imports `app.database`,
>    `app.routers.*` etc, but the zip had all files flat with no `app/`
>    folder or `app/routers/` subfolder. Fixed: files reorganized into the
>    structure shown in §7 below. Run everything from the **repo root**
>    (the folder containing `app/`, `data/`, `models/`), never from inside
>    `app/`.
> 2. **Model loader crashed** — `ml_model.py` used
>    `XGBRegressor().load_model()`, which throws
>    `` `_estimator_type` undefined `` against this saved file. Fixed:
>    switched to the raw `xgb.Booster()` API, which loads it correctly.
> 3. **Silent prediction bug — the important one.** `requirements.txt`
>    pinned `xgboost==2.1.1`. That version fails to parse this model's
>    `base_score` (stored as `"[-4.9993215E0]"`) and silently resets it to
>    `0.5` — no error, just every prediction shifted by a constant ~5.5m.
>    Verified: on 2.1.1, `/predict/Khoirabari` returned `+4.67`; on
>    `xgboost>=3.0`, it returns `-0.826`, matching this README's own
>    documented example exactly. **Do not downgrade xgboost below 3.0 for
>    this model file.**

## 1. Setup

```bash
cd gw-backend      # repo root — the folder with app/, data/, models/ inside it
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then edit .env — see §2 and §9
```

Drop your teammates' files into place (the model file is already included
in this handoff; the CSV is large so it's left out — copy your own in):

```
data/gwl_27stations_final_clean.csv
models/gw_model.json
```

## 2. Database — now Postgres by default

`.env` controls this — copy `.env.example` to `.env` and set `DATABASE_URL`
to the link your DB teammate gave you. Both of these work, no manual
edits needed:

```
DATABASE_URL=postgresql://user:pass@host:5432/dbname
DATABASE_URL=postgres://user:pass@host:5432/dbname          # auto-normalized
```

If your provider's dashboard gives you a URL with `?sslmode=require`
already on the end, keep it. `app/database.py` also sets
`pool_pre_ping=True` and `pool_recycle=1800` for any non-SQLite URL —
hosted Postgres (Neon/Supabase/Railway/RDS) silently drops idle
connections, and without these two settings the first request after any
gap throws a raw `SSL connection has been closed unexpectedly` instead of
just quietly reconnecting.

Still want SQLite for quick local testing? Leave `DATABASE_URL` unset or
set it to `sqlite:///./gw.db` — nothing else changes.

### Load the data

```bash
python -m app.ingest
```

For the live demo, simulate a real-time feed instead (replays rows with a
delay between timestamps):

```bash
python -m app.ingest --replay 0.05
```

Re-running `ingest.py` always wipes and reloads, so it's safe to run again
any time the CSV changes — this also means it's a fine way to smoke-test
that your Postgres connection actually works before booting the API.

## 3. Run the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs: http://localhost:8000/docs

## 4. Auth — API key, now implemented

`/health` and `/` stay public (so uptime checks and judges' first click
don't need a key). Every other route (`/stations`, `/readings`,
`/predict`, `/alerts`) requires header `X-API-Key: <value>` **once you set
`API_KEY` in `.env`**. If `API_KEY` is left empty, auth is off entirely —
same wide-open behavior as before, useful for local dev.

```bash
curl -H "X-API-Key: your-secret-here" http://localhost:8000/stations
```

Give the frontend teammate the key once it's set — every fetch call on
their end needs that header added. If a request is missing/wrong, they'll
get a `401` with `{"detail": "Missing or invalid API key. Send it as header: X-API-Key"}`.

## 5. Endpoints

| Method | Path | Auth required | Description |
|---|---|---|---|
| GET | `/stations` | yes (if API_KEY set) | All station metadata (name, district, lat/long) |
| GET | `/stations/{name}` | yes | One station's metadata |
| GET | `/readings/{name}?limit=200` | yes | Historical readings, chronological |
| GET | `/readings/{name}/latest` | yes | Most recent reading |
| GET | `/predict/{name}` | yes | Forecast the next 6-hourly level |
| GET | `/alerts?std_multiplier=1.5` | yes | Stations currently in depletion alert |
| GET | `/health` | no, always open | Liveness check |
| GET | `/` | no, always open | Root status |

Example:
```bash
curl -H "X-API-Key: your-secret" http://localhost:8000/predict/Khoirabari
```
```json
{
  "station": "Khoirabari",
  "last_known_timestamp": "2025-12-31T18:00:00",
  "last_known_level": -0.8,
  "predicted_next_level": -0.826,
  "predicted_change": -0.026
}
```
*(This is a real, verified response — not illustrative. Confirmed against the actual model+data with xgboost 3.4.1.)*

## 6. How `/predict` actually works

`gw_model.json` was trained on features like `lag_1`, `lag_4`,
`roll_mean_7d`, etc. — those don't exist yet for a future timestamp, so
`app/ml_model.py` rebuilds them live from the last 30 stored readings for
that station every time `/predict` is called (see
`build_next_step_features()`). This keeps inference in sync with
`train_model.py` by pulling the exact feature order from the saved model
(`model.feature_names`, read off the raw `xgb.Booster`) instead of
hardcoding it — if the ML teammate retrains with different features, this
code doesn't silently break, it'll just fail loudly with a clear KeyError.

## 7. How `/alerts` works

No ML — plain threshold logic on purpose (easy to explain to judges): a
station is flagged if its latest reading is more than `std_multiplier`
standard deviations below its own historical mean. Tune sensitivity with
the query param, e.g. `/alerts?std_multiplier=1.0` for more alerts.

## 8. File architecture

```
gw-backend/                      <- run all commands from HERE, not from inside app/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, CORS, startup (loads model once)
│   ├── config.py         # env-driven settings (DB url, paths, thresholds, API_KEY)
│   ├── database.py       # SQLAlchemy engine/session, Postgres URL normalization
│   ├── auth.py            # X-API-Key dependency
│   ├── models.py         # ORM tables: Station, Reading
│   ├── schemas.py        # Pydantic response models
│   ├── ml_model.py       # loads gw_model.json (xgb.Booster), builds live features, predicts
│   ├── ingest.py         # CSV -> DB loader / --replay demo mode
│   └── routers/
│       ├── __init__.py
│       ├── stations.py
│       ├── readings.py
│       ├── predict.py
│       └── alerts.py
├── data/gwl_27stations_final_clean.csv
├── models/gw_model.json
├── requirements.txt
├── .env.example
├── .env                  # you create this, gitignored, real secrets live here
└── README.md
```

## 9. Handing off to the frontend teammate

Give them the base URL + the table in §5 + the `X-API-Key` value once
you've set one. CORS is wide open (`CORS_ORIGINS=*`) for the hackathon —
tighten it in `.env` if needed. The API key does not replace CORS
restriction — it's a separate layer; tighten both before anything beyond
a hackathon demo.

## 10. Still TODO for you

- [x] ~~Switch to Postgres~~ — done, see §2. Untested against your team's
      actual live DB link from this environment (no network path to
      arbitrary external hosts here) — run `python -m app.ingest` once
      you've set the real `DATABASE_URL` to confirm the connection itself.
- [x] ~~Add simple API-key auth~~ — done, see §4.
- [ ] Point `/predict` at a background job (or cron) so predictions are
      pre-computed instead of live-computed on every request, if latency
      matters on demo day.
- [ ] Deploy: `uvicorn app.main:app --host 0.0.0.0 --port 8000` behind
      nginx, or just run it on the demo laptop.
- [ ] Rotate the `.env` API key before making the repo public, if it ever
      was committed by mistake — check `git log -p -- .env` once, just in
      case.
