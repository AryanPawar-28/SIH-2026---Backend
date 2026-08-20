from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.database import Base, engine
from app import ml_model
from app.routers import stations, readings, predict, alerts


@asynccontextmanager
async def lifespan(app: FastAPI):
    # make sure tables exist (ingest.py is still what actually loads data)
    Base.metadata.create_all(bind=engine)
    # load the XGBoost model once, keep it warm in memory for every request
    ml_model.load_model()
    print("Model loaded. Feature count:", len(ml_model.get_feature_names()))
    yield


app = FastAPI(
    title="SIH25068 — Groundwater Level API",
    description="Backend for real-time groundwater level monitoring & forecasting (Assam DWLR).",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stations.router)
app.include_router(readings.router)
app.include_router(predict.router)
app.include_router(alerts.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "SIH25068 groundwater API"}


@app.get("/health")
def health():
    return {"status": "healthy"}
