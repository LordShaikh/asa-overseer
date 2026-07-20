"""Discord bot client setup and lifecycle."""
from __future__ import annotations

import logging
from pathlib import Path

import discord
from discord.ext import commands

from config import settings
from db.store import init_db
from core.poller import poller

log = logging.getLogger(__name__)

INTENTS = discord.Intents.default()
INTENTS.guilds = True
INTENTS.members = True
INTENTS.message_content = True

COGS_DIR = Path(__file__).parent / "cogs"


class OverseerBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix="!",
            intents=INTENTS,
            application_id=None,
        )

    async def setup_hook(self) -> None:
        # Initialize DB
        await init_db()

        # Load all cogs
        for cog_file in COGS_DIR.glob("*.py"):
            if cog_file.stem.startswith("_"):
                continue
            cog_name = f"bot.cogs.{cog_file.stem}"
            try:
                await self.load_extension(cog_name)
                log.info("Loaded cog: %s", cog_name)
            except Exception as exc:
                log.error("Failed to load cog %s: %s", cog_name, exc)

        # Sync slash commands to the guild
        guild = discord.Object(id=settings.guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        log.info("Slash commands synced to guild %d", settings.guild_id)

        # Start the poller
        poller.start()

    async def on_ready(self) -> None:
        log.info("Logged in as %s (ID: %d)", self.user, self.user.id)

    async def close(self) -> None:
        poller.stop()
        from core.eos.auth import eos_auth
        from core.eos.matchmaking import eos_mm
        await eos_auth.close()
        await eos_mm.close()
        await super().close()
