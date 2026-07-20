"""Roaming King Titan monitor - uses EOS matchmaking snapshots to detect
roaming King Titan events on all official ASA Small Tribes Extinction servers.

No RCON required - hooks into the existing Poller snapshot data.

Detection strategy:
  Official Extinction sessions expose a 'RoamingBossActive_i' (or similar)
  attribute when the roaming King Titan is up. We also check the
  CUSTOMSERVERNAME_s for known titan-event suffixes as a fallback.
  On every Poller tick we compare the current EOS snapshot against our
  previous state and fire TitanEvent callbacks on transitions.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Awaitable, Dict, List, Optional

from core.eos.matchmaking import EOSSession

log = logging.getLogger(__name__)

# Map name patterns that identify Extinction sessions
EXT_MAP_RE = re.compile(r"extinction", re.IGNORECASE)

# EOS session attribute keys that signal the roaming King Titan is active.
# Wildcard Studio typically uses these attribute names in official sessions.
TITAN_ACTIVE_ATTRS = {
    "RoamingBossActive_i",
    "RoamingBossActive_b",
    "RoamingKingTitanActive_i",
    "RoamingKingTitanActive_b",
    "EventActive_i",
}

# Fallback: server name substrings that indicate an active roaming titan event
# (Wildcard sometimes appends e.g. "[KingTitan]" or "- RoamingBoss" to the name)
TITAN_NAME_RE = re.compile(
    r"(?:KingTitan|RoamingBoss|RoamingKingTitan|KingKaiju)",
    re.IGNORECASE,
)


def _session_has_titan(sess: EOSSession) -> bool:
    """Return True if this EOS session's attributes indicate an active roaming King Titan."""
    attrs: dict = sess.raw.get("attributes", {})

    # Check known boolean/integer attribute keys
    for key in TITAN_ACTIVE_ATTRS:
        val = attrs.get(key)
        if val not in (None, 0, False, "0", "false"):
            return True

    # Fallback: scan ALL attribute values for titan keywords
    for key, val in attrs.items():
        if isinstance(val, str) and TITAN_NAME_RE.search(val):
            return True

    # Final fallback: check the server name itself
    if TITAN_NAME_RE.search(sess.server_name):
        return True

    return False


@dataclass
class TitanEvent:
    session_id: str
    server_name: str
    map_name: str
    present: bool          # True = titan spawned, False = titan gone
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


TitanCallback = Callable[[TitanEvent], Awaitable[None]]


class TitanMonitor:
    """Watches EOS snapshot diffs for roaming King Titan events on all Extinction servers.

    Usage - call process_snapshot() on every Poller tick with the current
    Dict[session_id, EOSSession] snapshot.  Fires TitanEvent callbacks
    whenever a titan appears or disappears on any Extinction server.
    """

    def __init__(self) -> None:
        self._callbacks: list[TitanCallback] = []
        # Per session_id: True = titan currently active
        self._state: Dict[str, bool] = {}

    def add_callback(self, cb: TitanCallback) -> None:
        self._callbacks.append(cb)

    async def process_snapshot(self, snapshot: Dict[str, EOSSession]) -> None:
        """Called with the latest EOS snapshot on every poller tick."""
        # Only care about Extinction sessions
        ext_sessions: Dict[str, EOSSession] = {
            sid: sess
            for sid, sess in snapshot.items()
            if EXT_MAP_RE.search(sess.map_name or "")
        }

        # Detect sessions that have left the snapshot (server gone) -
        # if titan was active on them, fire a 'gone' event
        for sid in list(self._state.keys()):
            if self._state[sid] and sid not in ext_sessions:
                await self._fire(sid, "<offline>", "Extinction", present=False)
                del self._state[sid]

        # Check every live Extinction session
        for sid, sess in ext_sessions.items():
            now_active = _session_has_titan(sess)
            was_active = self._state.get(sid, False)

            if now_active != was_active:
                self._state[sid] = now_active
                await self._fire(sid, sess.server_name, sess.map_name, present=now_active)

            elif sid not in self._state:
                # First time we see this session - record state without firing
                self._state[sid] = now_active

    async def _fire(self, sid: str, name: str, map_name: str, present: bool) -> None:
        event = TitanEvent(
            session_id=sid,
            server_name=name,
            map_name=map_name,
            present=present,
        )
        log.info(
            "TitanMonitor: %s on %s (%s)",
            "SPAWN" if present else "GONE",
            name,
            sid,
        )
        for cb in self._callbacks:
            try:
                await cb(event)
            except Exception as exc:
                log.exception("TitanMonitor callback error: %s", exc)


# Singleton
titan_monitor = TitanMonitor()
