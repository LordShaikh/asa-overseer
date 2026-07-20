"""EOS Matchmaking API client - fetches sessions for ASA Small Tribes."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import aiohttp

from config import settings
from core.eos.auth import eos_auth

log = logging.getLogger(__name__)

EOS_MM_BASE = "https://api.epicgames.dev/matchmaking/v1"

# ARK: Survival Ascended Small Tribes bucket filter
SMALL_TRIBES_ATTRIBUTES = {
    "bucket": "OFFICIAL:pc:ArkAscended:SmallTribes"
}


class EOSSession:
    """Represents a single EOS matchmaking session (server)."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.session_id: str = data.get("id", "")
        self.server_name: str = data.get("attributes", {}).get("CUSTOMSERVERNAME_s", "Unknown")
        self.map_name: str = data.get("attributes", {}).get("MAPNAME_s", "")
        self.num_public_connections: int = data.get("settings", {}).get("numPublicConnections", 0)
        self.num_open_public_connections: int = data.get("numOpenPublicConnections", 0)
        self.players: List[Dict[str, Any]] = data.get("registeredPlayers", [])
        self.raw: Dict[str, Any] = data

    @property
    def player_count(self) -> int:
        return self.num_public_connections - self.num_open_public_connections

    @property
    def player_ids(self) -> List[str]:
        return [p.get("playerId", "") for p in self.players]


class EOSMatchmaking:
    """Queries EOS matchmaking for ASA Small Tribes sessions."""

    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _get_headers(self) -> Dict[str, str]:
        token = await eos_auth.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def get_sessions(self, max_results: int = 500) -> List[EOSSession]:
        """Fetch all Small Tribes sessions from EOS matchmaking."""
        url = f"{EOS_MM_BASE}/{settings.eos_sandbox_id}/sessions/matchTickets"
        headers = await self._get_headers()
        session = await self._get_session()
        payload = {
            "criteria": [
                {
                    "key": "bucket",
                    "op": "EQUAL",
                    "value": SMALL_TRIBES_ATTRIBUTES["bucket"],
                }
            ],
            "maxResults": max_results,
        }
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status == 204:
                return []
            resp.raise_for_status()
            data = await resp.json()
            sessions_data = data.get("sessions", [])
            log.debug("Fetched %d EOS sessions", len(sessions_data))
            return [EOSSession(s) for s in sessions_data]

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()


# Singleton
eos_mm = EOSMatchmaking()
