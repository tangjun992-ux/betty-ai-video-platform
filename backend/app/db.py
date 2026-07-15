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
        await conn.run_sync(_migrate_timeline_settings_column)
        await conn.run_sync(_migrate_team_and_transaction_columns)


def _migrate_team_and_transaction_columns(connection):
    """Add team billing columns on existing SQLite/Postgres DBs."""
    from sqlalchemy import inspect, text

    try:
        insp = inspect(connection)
        tables = set(insp.get_table_names())
        if "teams" in tables:
            cols = {c["name"] for c in insp.get_columns("teams")}
            if "seat_limit" not in cols:
                connection.execute(text("ALTER TABLE teams ADD COLUMN seat_limit INTEGER DEFAULT 5"))
        if "transactions" in tables:
            cols = {c["name"] for c in insp.get_columns("transactions")}
            if "team_id" not in cols:
                connection.execute(text("ALTER TABLE transactions ADD COLUMN team_id VARCHAR(36)"))
    except Exception:
        pass


def _migrate_timeline_settings_column(connection):
    """Add settings column to timeline_projects when upgrading an existing DB."""
    from sqlalchemy import inspect, text
    try:
        insp = inspect(connection)
        if "timeline_projects" not in insp.get_table_names():
            return
        cols = {c["name"] for c in insp.get_columns("timeline_projects")}
        if "settings" not in cols:
            connection.execute(text("ALTER TABLE timeline_projects ADD COLUMN settings JSON"))
    except Exception:
        pass
