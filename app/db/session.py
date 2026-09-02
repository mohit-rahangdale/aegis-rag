"""SQLAlchemy asynchronous database session and engine setup."""

from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import Settings, get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine(settings: Optional[Settings] = None) -> AsyncEngine:
    """Create or return the cached async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        if settings is None:
            settings = get_settings()

        # Build engine options based on environment
        connect_args = {}
        if "sqlite" in settings.database_url:
            connect_args["check_same_thread"] = False

        _engine = create_async_engine(
            settings.database_url,
            echo=settings.db_echo,
            future=True,
            connect_args=connect_args,
        )
    return _engine


def get_session_factory(settings: Optional[Settings] = None) -> async_sessionmaker[AsyncSession]:
    """Create or return the cached async session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine(settings)
        _session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_db_health(session: Optional[AsyncSession] = None) -> bool:
    """Verify database connectivity by executing a lightweight SELECT 1 query."""
    try:
        if session is not None:
            await session.execute(text("SELECT 1"))
            return True

        factory = get_session_factory()
        async with factory() as s:
            await s.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


def reset_db_connections() -> None:
    """Reset cached engine and session factory (primarily used in tests)."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None
