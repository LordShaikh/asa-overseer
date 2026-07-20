"""Roaming King Titan monitor - polls RCON GetGameLog on Extinction servers."""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Awaitable, Optional

from config import RconServer
from core.rcon.client import RconClient

log = logging.getLogger(__name__)

# Patterns in the ARK ShooterGame log for the roaming King Titan
# The roaming boss triggers when ASA spawns it at the scheduled daily time.
# We match lines that indicate the creature appearing/despawning in the world.
SPAWN_PATTERNS = [
    re.compile(r"KingKaiju.*?(?:Spawned|AddToWorld|BeginPlay)", re.IGNORECASE),
    re.compile(r"RoamingBoss.*?(?:Spawned|AddToWorld|BeginPlay)", re.IGNORECASE),
    re.compile(r"(?:Spawned|AddToWorld).*?KingKaiju", re.IGNORECASE),
]
DESPAWN_PATTERNS = [
    re.compile(r"KingKaiju.*?(?:Destroyed|EndPlay|Died|Death)", re.IGNORECASE),
    re.compile(r"RoamingBoss.*?(?:Destroyed|EndPlay|Died|Death)", re.IGNORECASE),
    re.compile(r"(?:Destroyed|EndPlay|Died).*?KingKaiju", re.IGNORECASE),
]


@dataclass
class TitanEvent:
    server_name: str
    present: bool          # True = spawned, False = despawned/killed
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


TitanCallback = Callable[[TitanEvent], Awaitable[None]]


class TitanMonitor:
    """Per-interval RCON log poller that detects roaming King Titan spawn/despawn."""

    def __init__(self) -> None:
        self._callbacks: list[TitanCallback] = []
        self._task: Optional[asyncio.Task] = None
        # Track titan presence per server name
        self._state: dict[str, bool] = {}  # server_name -> is_titan_present
        # Track last seen log lines per server to avoid re-processing
        self._seen_lines: dict[str, set[str]] = {}

    def add_callback(self, cb: TitanCallback) -> None:
        self._callbacks.append(cb)

    def start(self, servers: list[RconServer], interval: int = 120) -> None:
        """Start the polling loop. interval is in seconds (default 2 min)."""
        if self._task and not self._task.done():
            return
        self._servers = servers
        self._interval = interval
        self._task = asyncio.create_task(self._loop())
        log.info("TitanMonitor started for %d servers, interval=%ds", len(servers), interval)

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            log.info("TitanMonitor stopped")

    async def _loop(self) -> None:
        while True:
            try:
                await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.exception("TitanMonitor tick error: %s", exc)
            await asyncio.sleep(self._interval)

    async def _tick(self) -> None:
        for server in self._servers:
            try:
                await self._poll_server(server)
            except Exception as exc:
                log.warning("TitanMonitor: error polling %s: %s", server.name, exc)

    async def _poll_server(self, server: RconServer) -> None:
        client = RconClient(server)
        raw = await client.send("GetGameLog")
        if not raw:
            return

        lines = raw.splitlines()
        seen = self._seen_lines.setdefault(server.name, set())
        new_lines = [ln for ln in lines if ln not in seen]
        seen.update(lines)

        if not new_lines:
            return

        was_present = self._state.get(server.name, False)
        now_present = was_present

        for line in new_lines:
            if not was_present:
                if any(p.search(line) for p in SPAWN_PATTERNS):
                    now_present = True
                    log.info("[%s] Roaming King Titan SPAWNED detected: %s", server.name, line[:120])
                    break
            if was_present:
                if any(p.search(line) for p in DESPAWN_PATTERNS):
                    now_present = False
                    log.info("[%s] Roaming King Titan GONE detected: %s", server.name, line[:120])
                    break

        if now_present != was_present:
            self._state[server.name] = now_present
            event = TitanEvent(server_name=server.name, present=now_present)
            for cb in self._callbacks:
                try:
                    await cb(event)
                except Exception as exc:
                    log.exception("TitanMonitor callback error: %s", exc)


# Singleton
titan_monitor = TitanMonitor()
