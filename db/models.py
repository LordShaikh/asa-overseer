"""SQLAlchemy async ORM models for asa-overseer."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PlayerSighting(Base):
    """Records when a player is seen on a server."""
    __tablename__ = "player_sightings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    eos_player_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    server_name: Mapped[str] = mapped_column(String(256), nullable=False)
    map_name: Mapped[str] = mapped_column(String(128), nullable=True)
    seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    joined: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TrackedPlayer(Base):
    """Guild-specific watchlist entry."""
    __tablename__ = "tracked_players"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    eos_player_id: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(256), nullable=True)
    added_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
