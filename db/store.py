"""Database store - async session factory and CRUD helpers."""
from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from config import settings
from db.models import Base, PlayerSighting, TrackedPlayer

log = logging.getLogger(__name__)

_engine = None
_session_factory: Optional[async_sessionmaker] = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def get_session_factory() -> async_sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _session_factory


async def init_db() -> None:
    """Create all tables if they don't exist."""
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Database tables initialized")


async def log_sighting(sighting: PlayerSighting) -> None:
    async with get_session_factory()() as session:
        session.add(sighting)
        await session.commit()


async def get_tracked_players(guild_id: int) -> List[TrackedPlayer]:
    async with get_session_factory()() as session:
        result = await session.execute(
            select(TrackedPlayer).where(
                TrackedPlayer.guild_id == guild_id,
                TrackedPlayer.active == True,
            )
        )
        return list(result.scalars().all())


async def add_tracked_player(
    guild_id: int, eos_player_id: str, label: Optional[str], added_by: int
) -> TrackedPlayer:
    async with get_session_factory()() as session:
        tp = TrackedPlayer(
            guild_id=guild_id,
            eos_player_id=eos_player_id,
            label=label,
            added_by=added_by,
        )
        session.add(tp)
        await session.commit()
        await session.refresh(tp)
        return tp


async def remove_tracked_player(guild_id: int, eos_player_id: str) -> bool:
    async with get_session_factory()() as session:
        result = await session.execute(
            select(TrackedPlayer).where(
                TrackedPlayer.guild_id == guild_id,
                TrackedPlayer.eos_player_id == eos_player_id,
                TrackedPlayer.active == True,
            )
        )
        tp = result.scalar_one_or_none()
        if tp is None:
            return False
        tp.active = False
        await session.commit()
        return True
