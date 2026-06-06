"""
Leaderboard Cog - XP server leaderboard
"""

import discord
from discord import app_commands
from discord.ext import commands

from utils.database import Database
from utils.embeds import embed


class Leaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: Database = bot.db
        self.BOT_COLOR = bot.config.get("BOT_COLOR", 0x2F3136)

    @app_commands.command(name="leaderboard", description="View the top 10 XP leaderboard for this server")
    async def leaderboard(self, interaction: discord.Interaction):

        if not interaction.guild:
            return await interaction.response.send_message(
                "❌ This command can only be used in a server.", ephemeral=True
            )

        await interaction.response.defer()

        try:
            rows = await self.db.get_leaderboard(interaction.guild_id, 10) or []

            if not rows:
                return await interaction.followup.send(
                    embed=embed("📊 No data yet!", "No XP data found in this server.", 0x95A5A6)
                )

            lb_embed = discord.Embed(  # FIX: renamed from `e` to `lb_embed` to avoid shadowing by `except ... as e`
                title=f"🏆 {interaction.guild.name} — Top 10",
                color=self.BOT_COLOR,
            )

            medals = ["🥇", "🥈", "🥉"]

            for i, row in enumerate(rows):
                user = interaction.guild.get_member(row.get("user_id"))
                name = user.mention if user else f"<@{row.get('user_id')}>"
                medal = medals[i] if i < 3 else f"#{i + 1}"

                lb_embed.add_field(
                    name=f"{medal} {name}",
                    value=f"Level **{row.get('level', 0)}** — `{row.get('xp', 0):,} XP`",
                    inline=False,
                )

            await interaction.followup.send(embed=lb_embed)

        except Exception as exc:  # FIX: renamed from `e` to `exc` — no more variable shadowing
            await interaction.followup.send(
                embed=embed(
                    "❌ Error",
                    f"Failed to load leaderboard.\n```{str(exc)}```",
                    0xED4245,
                ),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))
