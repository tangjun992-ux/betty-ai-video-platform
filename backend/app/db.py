from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings


def _create_engine():
    """Create an engine that works with PostgreSQL or SQLite"""
    url = settings.DATABASE_URL
    
    # SQLite async driver
    if url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool
        return create_async_engine(
            url,
            echo=settings.ENV == "development",
            connect_args={"check_same_thread": False} if "sqlite" in url else {},
            poolclass=StaticPool if url == "sqlite+aiosqlite:///./dev.db" else None,
        )
    
    return create_async_engine(
        url,
        echo=settings.ENV == "development",
        pool_size=getattr(settings, "DATABASE_POOL_SIZE", 5),
        max_overflow=getattr(settings, "DATABASE_MAX_OVERFLOW", 10),
        pool_pre_ping=True,
    )


engine = _create_engine()

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """FastAPI dependency for database sessions"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables"""
    from app.models import Base
    # Import collector models so SQLAlchemy discovers their table definitions
    import app.collector.models  # noqa: F401 - registers TrendingTopic/ViralSignal/TrendReport with Base.metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
