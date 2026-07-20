"""Watchlist cog - slash commands for managing the tracked players list."""
from __future__ import annotations

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from db.store import get_tracked_players, add_tracked_player, remove_tracked_player

log = logging.getLogger(__name__)


class WatchlistCog(commands.Cog, name="Watchlist"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="watch", description="Add a player to the watchlist by EOS ID")
    @app_commands.describe(
        eos_id="The player's EOS (Epic Online Services) ID",
        label="Optional human-readable name for this player",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def watch(self, interaction: discord.Interaction, eos_id: str, label: Optional[str] = None) -> None:
        await interaction.response.defer(ephemeral=True)
        tp = await add_tracked_player(
            guild_id=interaction.guild_id,
            eos_player_id=eos_id,
            label=label,
            added_by=interaction.user.id,
        )
        display = tp.label or tp.eos_player_id
        await interaction.followup.send(f"Now watching **{display}** (`{tp.eos_player_id}`)", ephemeral=True)

    @app_commands.command(name="unwatch", description="Remove a player from the watchlist")
    @app_commands.describe(eos_id="The player's EOS ID to stop watching")
    @app_commands.default_permissions(manage_guild=True)
    async def unwatch(self, interaction: discord.Interaction, eos_id: str) -> None:
        await interaction.response.defer(ephemeral=True)
        removed = await remove_tracked_player(guild_id=interaction.guild_id, eos_player_id=eos_id)
        if removed:
            await interaction.followup.send(f"Stopped watching `{eos_id}`", ephemeral=True)
        else:
            await interaction.followup.send(f"`{eos_id}` was not on the watchlist", ephemeral=True)

    @app_commands.command(name="watchlist", description="Show the current watchlist")
    async def show_watchlist(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        players = await get_tracked_players(guild_id=interaction.guild_id)
        if not players:
            await interaction.followup.send("The watchlist is empty.", ephemeral=True)
            return
        lines = []
        for tp in players:
            label = tp.label or tp.eos_player_id
            lines.append(f"- **{label}** (`{tp.eos_player_id}`), added by <@{tp.added_by}>")
        embed = discord.Embed(
            title="Watchlist",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WatchlistCog(bot))
