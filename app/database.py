from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL

# Some hosted Postgres providers (Railway, Render, old Heroku links) hand out
# "postgres://" URLs. SQLAlchemy 1.4+/2.0 only accepts "postgresql://" —
# normalize it here so whatever link a teammate pastes into .env just works,
# instead of failing with a cryptic "could not parse SQLAlchemy URL" error.
_db_url = DATABASE_URL
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

is_sqlite = _db_url.startswith("sqlite")

# check_same_thread only needed for SQLite.
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    _db_url,
    connect_args=connect_args,
    # Hosted Postgres instances (Supabase/Neon/RDS/etc.) silently close idle
    # connections. Without these two, the first request after any idle gap
    # throws "SSL connection has been closed unexpectedly" instead of just
    # reconnecting. pool_pre_ping checks liveness before handing out a
    # connection; pool_recycle forces a refresh before the provider's own
    # idle timeout hits. No-ops for SQLite.
    pool_pre_ping=not is_sqlite,
    pool_recycle=1800 if not is_sqlite else -1,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
