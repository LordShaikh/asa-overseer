"""Async RCON client wrapper using mcrcon."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from mcrcon import MCRcon

from config import RconServer

log = logging.getLogger(__name__)


class RconClient:
    """Thread-safe async wrapper around MCRcon."""

    def __init__(self, server: RconServer) -> None:
        self.server = server

    async def send(self, command: str) -> str:
        """Send an RCON command and return the response."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._send_sync, command)

    def _send_sync(self, command: str) -> str:
        try:
            with MCRcon(self.server.host, self.server.password, self.server.port) as mcr:
                response = mcr.command(command)
                log.debug("[%s] RCON %r -> %r", self.server.name, command, response[:100])
                return response
        except Exception as exc:
            log.error("RCON error on %s: %s", self.server.name, exc)
            return ""

    async def broadcast(self, message: str) -> str:
        """Broadcast a server message via RCON."""
        return await self.send(f"ServerChat {message}")

    async def list_players(self) -> str:
        """Return the raw listplayers output."""
        return await self.send("listplayers")
