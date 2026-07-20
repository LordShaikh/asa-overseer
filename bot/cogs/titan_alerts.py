"""Titan Alerts cog - Discord notifications for roaming King Titan on ALL official
ASA Small Tribes Extinction servers, detected via the existing EOS poller.

No RCON required.  Hooks titan_monitor.process_snapshot() into the Poller
callback so it runs on every existing EOS poll tick automatically.
"""
from __future__ import annotations

import logging
from datetime import timezone

import discord
from discord.ext import commands

from config import settings
from core.poller import poller
from core.rcon.titan_monitor import TitanEvent, titan_monitor

log = logging.getLogger(__name__)

# Extinction / Wasteland colour
EXT_COLOUR = discord.Colour.from_str("#7b2d8b")


class TitanAlertsCog(commands.Cog, name="TitanAlerts"):
    """Listens to EOS poller snapshots and posts King Titan spawn/despawn alerts."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        """Wire titan_monitor into the existing Poller so we share EOS poll ticks."""
        # Register our snapshot handler with titan_monitor
        titan_monitor.add_callback(self.on_titan_event)

        # Register a Poller callback that feeds snapshots into titan_monitor.
        # The Poller receives a SnapshotDiff; we reconstruct the full current
        # snapshot from poller._prev_snapshot which is always up-to-date.
        async def _poller_hook(diff) -> None:  # noqa: ANN001
            await titan_monitor.process_snapshot(poller._prev_snapshot)

        poller.add_callback(_poller_hook)
        log.info(
            "TitanAlerts cog loaded - monitoring all official Extinction servers "
            "via EOS poller (no RCON needed)"
        )

    async def on_titan_event(self, event: TitanEvent) -> None:
        """Called by TitanMonitor whenever a titan state change is detected."""
        channel_id = getattr(settings, "titan_channel_id", None) or settings.log_channel_id
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            log.warning("TitanAlerts: channel %d not found", channel_id)
            return

        ts = event.detected_at.astimezone(timezone.utc)
        ts_str = discord.utils.format_dt(ts, style="T")

        # Clean up the map name for display
        map_display = (
            event.map_name
            .replace("_WP", "")
            .replace("_wp", "")
            .replace("_P", "")
            .capitalize()
        )

        if event.present:
            embed = discord.Embed(
                title="🐉 Roaming King Titan Detected!",
                description=(
                    f"A **Roaming King Titan** is active on:\n"
                    f"> **{event.server_name}** `({map_display})`\n\n"
                    f"Grab your gear and get moving!"
                ),
                colour=EXT_COLOUR,
                timestamp=event.detected_at,
            )
            embed.add_field(name="Server", value=event.server_name, inline=True)
            embed.add_field(name="Map", value=map_display, inline=True)
            embed.add_field(name="Detected at", value=ts_str, inline=True)
            embed.set_footer(text="ASA Overseer • EOS Live Detection • Official Small Tribes")
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
            embed.add_field(name="Map", value=map_display, inline=True)
            embed.add_field(name="Last seen", value=ts_str, inline=True)
            embed.set_footer(text="ASA Overseer • EOS Live Detection • Official Small Tribes")

        await channel.send(embed=embed)
        log.info(
            "TitanAlerts: posted %s for %s",
            "SPAWN" if event.present else "DESPAWN",
            event.server_name,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TitanAlertsCog(bot))
