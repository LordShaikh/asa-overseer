from __future__ import annotations

import json
import os
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RconServer(BaseSettings):
    host: str
    port: int = 27020
    password: str
    name: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Discord
    discord_token: str
    guild_id: int
    log_channel_id: int
        titan_channel_id: Optional[int] = Field(default=None)

    # EOS
    eos_client_id: str
    eos_client_secret: str
    eos_deployment_id: str
    eos_sandbox_id: str

    # Database
    database_url: str

    # RCON
    rcon_servers: str = Field(default="[]")

    # Polling
    poll_interval: int = Field(default=60)

    # Logging
    log_level: str = Field(default="INFO")

    def get_rcon_servers(self) -> List[RconServer]:
        data = json.loads(self.rcon_servers)
        return [RconServer(**s) for s in data]


settings = Settings()
