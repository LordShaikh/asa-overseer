"""Polling loop - fetches EOS sessions at regular intervals and fires events."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Callable, Awaitable, Optional

from config import settings
from core.eos.matchmaking import eos_mm, EOSSession
from core.diff import compute_diff, SnapshotDiff

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

EventCallback = Callable[[SnapshotDiff], Awaitable[None]]


class Poller:
    """Periodic poller that diffs EOS snapshots and emits events."""

    def __init__(self) -> None:
        self._prev_snapshot: dict[str, EOSSession] = {}
        self._callbacks: list[EventCallback] = []
        self._task: Optional[asyncio.Task] = None

    def add_callback(self, cb: EventCallback) -> None:
        self._callbacks.append(cb)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())
            log.info("Poller started with interval=%ds", settings.poll_interval)

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            log.info("Poller stopped")

    async def _loop(self) -> None:
        while True:
            try:
                await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.exception("Poller tick error: %s", exc)
            await asyncio.sleep(settings.poll_interval)

    async def _tick(self) -> None:
        sessions = await eos_mm.get_sessions()
        current = {s.session_id: s for s in sessions}
        diff = compute_diff(self._prev_snapshot, current)
        self._prev_snapshot = current

        if diff.has_changes:
            log.debug(
                "Diff: +%d servers, -%d servers, %d player changes",
                len(diff.added_servers),
                len(diff.removed_servers),
                len(diff.player_changes),
            )
            for cb in self._callbacks:
                try:
                    await cb(diff)
                except Exception as exc:
                    log.exception("Event callback error: %s", exc)


# Singleton
poller = Poller()
