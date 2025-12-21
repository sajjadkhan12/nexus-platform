from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Create async engine with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,  # Set to True to see SQL queries for debugging
    future=True,
    # Connection pooling configuration
    pool_size=20,  # Number of connections to maintain in the pool
    max_overflow=10,  # Maximum number of connections to create beyond pool_size
    pool_timeout=30,  # Seconds to wait before giving up on getting a connection
    pool_pre_ping=True,  # Verify connections before using them (handles stale connections)
    pool_recycle=3600,  # Recycle connections after 1 hour (prevents stale connections)
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
