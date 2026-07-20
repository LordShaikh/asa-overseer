"""Titan Alerts cog - Discord notifications for roaming King Titan on Extinction servers."""
from __future__ import annotations

import logging
from datetime import timezone

import discord
from discord.ext import commands

from config import settings
from core.rcon.titan_monitor import TitanEvent, titan_monitor

log = logging.getLogger(__name__)

# Extinction map colour: dark purple-ish to evoke the Wasteland
EXT_COLOUR = discord.Colour.from_str("#7b2d8b")


class TitanAlertsCog(commands.Cog, name="TitanAlerts"):
    """Listens to the TitanMonitor and posts spawn/despawn alerts."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        titan_monitor.add_callback(self.on_titan_event)

    async def cog_load(self) -> None:
        """Start the monitor when the cog loads, using all configured RCON servers."""
        ext_servers = [
            s for s in settings.get_rcon_servers()
            if s.name.lower().startswith("ext") or "extinction" in s.name.lower()
        ]
        if not ext_servers:
            log.warning(
                "TitanAlerts: no Extinction servers found in RCON_SERVERS. "
                "Add entries whose name starts with 'Ext' or contains 'Extinction'."
            )
            return
        # Use all configured RCON servers that match Extinction; poll every 2 minutes
        titan_monitor.start(ext_servers, interval=120)
        log.info("TitanAlerts cog loaded, monitoring %d Extinction server(s)", len(ext_servers))

    async def cog_unload(self) -> None:
        titan_monitor.stop()

    async def on_titan_event(self, event: TitanEvent) -> None:
        """Called by TitanMonitor when titan state changes on any server."""
        channel_id = getattr(settings, "titan_channel_id", None)
        if not channel_id:
            # Fall back to the main log channel if no dedicated titan channel is set
            channel_id = settings.log_channel_id

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            log.warning("TitanAlerts: channel %d not found", channel_id)
            return

        ts = event.detected_at.astimezone(timezone.utc)
        ts_str = discord.utils.format_dt(ts, style="T")  # e.g. 21:07:00

        if event.present:
            embed = discord.Embed(
                title="🐉 Roaming King Titan Detected!",
                description=(
                    f"**{event.server_name}** — a Roaming King Titan has appeared "
                    f"in the Wasteland and is on the move."
                ),
                colour=EXT_COLOUR,
                timestamp=event.detected_at,
            )
            embed.add_field(name="Server", value=event.server_name, inline=True)
            embed.add_field(name="Detected at", value=ts_str, inline=True)
            embed.set_footer(text="ASA Overseer • Extinction Titan Alert")
        else:
            embed = discord.Embed(
                title="☠️ Roaming King Titan Gone",
                description=(
                    f"The Roaming King Titan on **{event.server_name}** "
                    f"has been defeated or despawned."
                ),
                colour=discord.Colour.dark_gray(),
                timestamp=event.detected_at,
            )
            embed.add_field(name="Server", value=event.server_name, inline=True)
            embed.add_field(name="Last seen", value=ts_str, inline=True)
            embed.set_footer(text="ASA Overseer • Extinction Titan Alert")

        await channel.send(embed=embed)
        log.info(
            "TitanAlerts: posted %s notification for %s",
            "spawn" if event.present else "despawn",
            event.server_name,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TitanAlertsCog(bot))
