"""
Central configuration.
Reads from environment variables (or a .env file) so the same code runs
locally with SQLite during dev and with Postgres for the real deployment.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Database -----------------------------------------------------------
# Default: local SQLite file, zero setup, perfect for hackathon dev.
# For the "real" deploy, set DATABASE_URL to something like:
#   postgresql://user:password@localhost:5432/gwdb
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/gw.db")

# --- Data / model paths ---------------------------------------------------
CSV_PATH = os.getenv("CSV_PATH", str(BASE_DIR / "data" / "gwl_27stations_final_clean.csv"))
MODEL_PATH = os.getenv("MODEL_PATH", str(BASE_DIR / "models" / "gw_model.json"))

# --- Alerts ---------------------------------------------------------------
# A station is "critical" if its latest reading is this many standard
# deviations below its own historical mean. Lower std multiplier = more
# alerts fire (more sensitive). Tune this on demo day.
ALERT_STD_MULTIPLIER = float(os.getenv("ALERT_STD_MULTIPLIER", "1.5"))

# --- CORS -------------------------------------------------------------
# React dev server + Vite default ports, wide open for the hackathon demo
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# --- Auth -------------------------------------------------------------
# If unset/empty, auth is OFF (dev mode) — every route stays open, same as
# before. Set API_KEY in .env for the demo/deploy and every data route
# (stations/readings/predict/alerts) requires header: X-API-Key: <value>
# / and /health are never gated, so uptime checks don't need the key.
API_KEY = os.getenv("API_KEY", "")
