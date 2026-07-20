"""Events cog - listens to the poller diff and posts join/leave alerts."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands

from config import settings
from core.diff import SnapshotDiff, PlayerChange
from core.poller import poller
from db.models import PlayerSighting
from db.store import log_sighting, get_tracked_players

log = logging.getLogger(__name__)


class EventsCog(commands.Cog, name="Events"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        poller.add_callback(self.on_diff)

    async def on_diff(self, diff: SnapshotDiff) -> None:
        """Handle snapshot diff events from the poller."""
        channel = self.bot.get_channel(settings.log_channel_id)
        if channel is None:
            log.warning("Log channel %d not found", settings.log_channel_id)
            return

        guild_id = settings.guild_id
        tracked = {tp.eos_player_id: tp for tp in await get_tracked_players(guild_id)}

        for change in diff.player_changes:
            # Persist sighting
            await log_sighting(
                PlayerSighting(
                    eos_player_id=change.player_id,
                    session_id=change.session_id,
                    server_name=change.server_name,
                    joined=change.joined,
                )
            )

            # Only alert for tracked players
            if change.player_id not in tracked:
                continue

            tp = tracked[change.player_id]
            label = tp.label or change.player_id
            action = "joined" if change.joined else "left"
            color = discord.Color.green() if change.joined else discord.Color.red()

            embed = discord.Embed(
                title=f"Tracked Player {action.capitalize()}",
                description=f"**{label}** {action} **{change.server_name}**",
                color=color,
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="EOS ID", value=change.player_id, inline=True)
            embed.add_field(name="Server", value=change.server_name, inline=True)
            embed.set_footer(text="ASA Overseer")

            await channel.send(embed=embed)

        for server in diff.added_servers:
            log.info("Server appeared: %s", server.server_name)

        for server in diff.removed_servers:
            log.info("Server disappeared: %s", server.server_name)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EventsCog(bot))
