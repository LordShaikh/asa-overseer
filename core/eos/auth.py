"""EOS OAuth2 client credentials token manager."""
from __future__ import annotations

import time
import base64
import logging
from typing import Optional

import aiohttp

from config import settings

log = logging.getLogger(__name__)

EOS_AUTH_URL = "https://api.epicgames.dev/epic/oauth/v2/token"


class EOSToken:
    def __init__(self, access_token: str, expires_at: float) -> None:
        self.access_token = access_token
        self.expires_at = expires_at

    @property
    def is_valid(self) -> bool:
        return time.time() < self.expires_at - 30


class EOSAuth:
    """Manages EOS client credentials access token with auto-refresh."""

    def __init__(self) -> None:
        self._token: Optional[EOSToken] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _fetch_token(self) -> EOSToken:
        credentials = base64.b64encode(
            f"{settings.eos_client_id}:{settings.eos_client_secret}".encode()
        ).decode()
        session = await self._get_session()
        async with session.post(
            EOS_AUTH_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            expires_at = time.time() + data["expires_in"]
            log.info("EOS token refreshed, expires in %ds", data["expires_in"])
            return EOSToken(data["access_token"], expires_at)

    async def get_token(self) -> str:
        if self._token is None or not self._token.is_valid:
            self._token = await self._fetch_token()
        return self._token.access_token

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()


# Singleton
eos_auth = EOSAuth()
