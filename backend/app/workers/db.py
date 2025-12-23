"""Database session management for Celery workers"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Create a shared synchronous database engine for all Celery tasks
# This avoids creating a new engine for each task, improving connection pooling
_sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
if "postgresql://" not in _sync_db_url and "postgresql+psycopg2://" not in _sync_db_url:
    _sync_db_url = _sync_db_url.replace("postgresql:", "postgresql+psycopg2:")

# Shared engine with connection pooling for Celery tasks
_shared_sync_engine = create_engine(
    _sync_db_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True  # Verify connections before using
)

_shared_SessionLocal = sessionmaker(bind=_shared_sync_engine)


def get_sync_db_session():
    """Get a synchronous database session using the shared engine"""
    return _shared_SessionLocal()

