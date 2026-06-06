"""
Reminders Cog - remind and poll commands with background task loop
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone
import logging

from utils.database import Database
from utils.embeds import embed
from utils.helpers import parse_duration

log = logging.getLogger("ApexBot")


class Reminders(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: Database = bot.db
        self.BOT_COLOR = bot.config["BOT_COLOR"]
        self.reminder_task.start()

    def cog_unload(self):
        self.reminder_task.cancel()

    # ─── REMIND ──────────────────────────────────────────────────────────────
    @app_commands.command(name="remind", description="Set a reminder (e.g. 10m, 2h30m, 1d)")
    async def remind(self, interaction: discord.Interaction, duration: str, message: str):
        td = parse_duration(duration)

        if not td:
            return await interaction.response.send_message(
                "❌ Invalid duration. Examples: `10m`, `2h30m`, `1d`", ephemeral=True
            )

        if td.total_seconds() > 86400 * 30:
            return await interaction.response.send_message(
                "❌ Maximum reminder time is 30 days.", ephemeral=True
            )

        remind_at = datetime.now(timezone.utc) + td

        await self.db.add_reminder(
            interaction.user.id,
            interaction.channel_id,
            message,
            remind_at,
        )

        dt_fmt = discord.utils.format_dt(remind_at, "R")

        await interaction.response.send_message(
            embed=embed(
                "⏰ Reminder Set!",
                f"I'll remind you **{dt_fmt}**\n\n> {message}",
                0x57F287,
            )
        )

    # ─── POLL ────────────────────────────────────────────────────────────────
    @app_commands.command(name="poll", description="Create a yes/no poll in this channel")
    async def poll(self, interaction: discord.Interaction, question: str):
        # FIX: guard against interaction.channel being None (e.g. ephemeral-only contexts)
        if interaction.channel is None:
            return await interaction.response.send_message(
                "❌ Cannot create a poll here.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        poll_embed = discord.Embed(
            title="📊 Poll",
            description=f"**{question}**",
            color=self.BOT_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        poll_embed.set_footer(
            text=f"Asked by {interaction.user}",
            icon_url=interaction.user.display_avatar.url,
        )

        try:
            msg = await interaction.channel.send(embed=poll_embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
            await interaction.followup.send("✅ Poll created!", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to send messages in this channel.", ephemeral=True
            )
        except Exception as exc:
            await interaction.followup.send(f"❌ Error creating poll: {exc}", ephemeral=True)

    # ─── BACKGROUND TASK ─────────────────────────────────────────────────────
    @tasks.loop(seconds=30)
    async def reminder_task(self):
        try:
            due = await self.db.get_due_reminders()

            for r in due:
                channel = self.bot.get_channel(r["channel_id"])

                if channel is None:
                    # Channel no longer accessible — delete the reminder silently
                    await self.db.delete_reminder(r["id"])
                    continue

                reminder_embed = discord.Embed(
                    title="⏰ Reminder!",
                    description=f"<@{r['user_id']}>\n\n> {r['content']}",
                    color=self.BOT_COLOR,
                    timestamp=datetime.now(timezone.utc),
                )

                try:
                    await channel.send(embed=reminder_embed)
                except discord.Forbidden:
                    pass  # Can't send — still delete to avoid retrying forever
                finally:
                    await self.db.delete_reminder(r["id"])

        except Exception as exc:
            log.error("Reminder task error: %s", exc)

    @reminder_task.before_loop
    async def before_reminder(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Reminders(bot))
