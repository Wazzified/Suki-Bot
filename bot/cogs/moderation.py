"""
Moderation Cog - kick, ban, unban, timeout, warn, clearwarns
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

from utils.database import Database
from utils.embeds import embed
from utils.helpers import parse_duration


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: Database = bot.db
        self.BOT_COLOR = bot.config.get("BOT_COLOR", 0x2F3136)

    async def _log_action(self, guild, action, mod, target, reason, color=None):
        """Send an action to the guild's log channel, if set."""
        try:
            color = color or self.BOT_COLOR
            gs = await self.db.get_guild(guild.id) or {}
            log_id = gs.get("log_channel")
            if not log_id:
                return

            channel = guild.get_channel(int(log_id))
            if not channel:
                return

            e = discord.Embed(
                title=action,
                color=color,
                timestamp=datetime.now(timezone.utc),
            )
            e.add_field(name="Target",    value=f"{target} ({target.id})", inline=False)
            e.add_field(name="Moderator", value=f"{mod} ({mod.id})",       inline=False)
            e.add_field(name="Reason",    value=reason or "No reason provided", inline=False)
            e.set_thumbnail(url=target.display_avatar.url)
            await channel.send(embed=e)
        except Exception:
            pass

    # ─── KICK ────────────────────────────────────────────────────────────────
    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Guild only.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        if member.top_role >= interaction.user.top_role:
            return await interaction.followup.send(
                "❌ You cannot kick someone with an equal or higher role.", ephemeral=True
            )

        try:
            await member.kick(reason=reason)
            await interaction.followup.send(
                embed=embed("👢 Kicked", f"**{member}** has been kicked.\n**Reason:** {reason}", 0xFEE75C)
            )
            await self._log_action(interaction.guild, "👢 Kick", interaction.user, member, reason, 0xFEE75C)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to kick that member.", ephemeral=True)
        except Exception as exc:
            await interaction.followup.send(f"❌ Error: {exc}", ephemeral=True)

    # ─── BAN ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="ban", description="Permanently ban a member from the server")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Guild only.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        if member.top_role >= interaction.user.top_role:
            return await interaction.followup.send(
                "❌ You cannot ban someone with an equal or higher role.", ephemeral=True
            )

        try:
            await member.ban(reason=reason)
            await interaction.followup.send(
                embed=embed("🔨 Banned", f"**{member}** has been banned.\n**Reason:** {reason}", 0xED4245)
            )
            await self._log_action(interaction.guild, "🔨 Ban", interaction.user, member, reason, 0xED4245)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to ban that member.", ephemeral=True)
        except Exception as exc:
            await interaction.followup.send(f"❌ Error: {exc}", ephemeral=True)

    # ─── UNBAN ───────────────────────────────────────────────────────────────
    @app_commands.command(name="unban", description="Unban a user by their Discord user ID")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str,
        reason: str = "No reason provided",
    ):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Guild only.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user, reason=reason)
            await interaction.followup.send(
                embed=embed("✅ Unbanned", f"**{user}** has been unbanned.", 0x57F287)
            )
        except ValueError:
            await interaction.followup.send("❌ Invalid user ID — must be a number.", ephemeral=True)
        except discord.NotFound:
            await interaction.followup.send("❌ User not found or not banned.", ephemeral=True)
        except Exception as exc:
            await interaction.followup.send(f"❌ Error: {exc}", ephemeral=True)

    # ─── TIMEOUT ─────────────────────────────────────────────────────────────
    @app_commands.command(name="timeout", description="Timeout a member (e.g. 10m, 2h, 1d)")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str = "No reason provided",
    ):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Guild only.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        td = parse_duration(duration)
        if not td:
            return await interaction.followup.send(
                "❌ Invalid duration. Examples: `10m`, `2h`, `1d`", ephemeral=True
            )

        try:
            await member.timeout(td, reason=reason)
            await interaction.followup.send(
                embed=embed(
                    "⏱️ Timed Out",
                    f"**{member}** has been timed out for **{duration}**.\n**Reason:** {reason}",
                    0xFEE75C,
                )
            )
            await self._log_action(
                interaction.guild, "⏱️ Timeout", interaction.user, member, reason, 0xFEE75C
            )
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to timeout that member.", ephemeral=True)
        except Exception as exc:
            await interaction.followup.send(f"❌ Error: {exc}", ephemeral=True)

    # ─── WARN ────────────────────────────────────────────────────────────────
    # FIX: Command was listed in /help but was never implemented — added here
    @app_commands.command(name="warn", description="Give a warning to a member")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
    ):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Guild only.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        if member.bot:
            return await interaction.followup.send("❌ Cannot warn a bot.", ephemeral=True)

        total = await self.db.add_warning(member.id, interaction.guild_id, interaction.user.id, reason)

        await interaction.followup.send(
            embed=embed(
                "⚠️ Warning Issued",
                f"**{member.mention}** has been warned.\n**Reason:** {reason}\n\n"
                f"They now have **{total}** warning(s) in this server.",
                0xFEE75C,
            )
        )

        await self._log_action(
            interaction.guild, "⚠️ Warn", interaction.user, member, reason, 0xFEE75C
        )

        # Try to DM the member
        try:
            await member.send(
                embed=embed(
                    f"⚠️ You received a warning in {interaction.guild.name}",
                    f"**Reason:** {reason}\n\nYou now have **{total}** warning(s).",
                    0xFEE75C,
                )
            )
        except discord.Forbidden:
            pass  # DMs disabled

    # ─── CLEARWARNS ──────────────────────────────────────────────────────────
    # FIX: New command — database already had this capability unused
    @app_commands.command(name="clearwarns", description="Clear all warnings for a member")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clearwarns(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Guild only.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        warnings = await self.db.get_warnings(member.id, interaction.guild_id)
        if not warnings:
            return await interaction.followup.send(
                f"ℹ️ **{member}** has no warnings to clear.", ephemeral=True
            )

        await self.db.clear_warnings(member.id, interaction.guild_id)

        await interaction.followup.send(
            embed=embed(
                "✅ Warnings Cleared",
                f"All **{len(warnings)}** warning(s) for **{member.mention}** have been removed.",
                0x57F287,
            )
        )

    # ─── WARNINGS ────────────────────────────────────────────────────────────
    # FIX: New command — view all warnings for a member
    @app_commands.command(name="warnings", description="View all warnings for a member")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Guild only.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        warns = await self.db.get_warnings(member.id, interaction.guild_id)

        if not warns:
            return await interaction.followup.send(
                embed=embed(
                    f"✅ {member} has no warnings", "This member is clean!", 0x57F287
                ),
                ephemeral=True,
            )

        e = discord.Embed(
            title=f"⚠️ {member}'s Warnings ({len(warns)} total)",
            color=0xFEE75C,
        )
        e.set_thumbnail(url=member.display_avatar.url)

        for i, w in enumerate(warns[:10], 1):  # show max 10
            mod = interaction.guild.get_member(w["mod_id"])
            mod_str = str(mod) if mod else f"<@{w['mod_id']}>"
            e.add_field(
                name=f"Warning #{i}",
                value=f"**Reason:** {w['reason']}\n**By:** {mod_str}\n**When:** {w['created_at'][:10]}",
                inline=False,
            )

        await interaction.followup.send(embed=e, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
