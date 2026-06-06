"""
Auto Role Cog - Reaction Role System
Admin setup channel dengan embed, user klik ✅ untuk dapat role otomatis.

Commands:
  /autorole setup  - Buat pesan reaction role di channel
  /autorole remove - Hapus reaction role
  /autorole list   - Lihat semua reaction role aktif
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging

from utils.embeds import embed

log = logging.getLogger("ApexBot")


class AutoRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db
        self.BOT_COLOR = bot.config.get("BOT_COLOR", 0x57F287)

    # ── GROUP ─────────────────────────────────────────────────────────────────
    autorole = app_commands.Group(name="autorole", description="Kelola sistem Auto Role server")

    # ── SETUP ─────────────────────────────────────────────────────────────────
    @autorole.command(name="setup", description="Buat pesan reaction role — user klik ✅ untuk dapat role")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_roles=True)
    async def autorole_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        role: discord.Role,
        judul: str = "Verifikasi Member",
        deskripsi: str = "Klik ✅ di bawah untuk mendapatkan role member!",
    ):
        await interaction.response.defer(ephemeral=True)

        # Cek permission bot
        if role >= interaction.guild.me.top_role:
            return await interaction.followup.send(
                embed=embed("❌ Role Terlalu Tinggi!",
                    f"Role {role.mention} lebih tinggi dari role bot.\n"
                    "Pindahkan role bot ke atas role tersebut di Server Settings → Roles.",
                    0xED4245),
                ephemeral=True,
            )

        perms = channel.permissions_for(interaction.guild.me)
        if not perms.send_messages or not perms.add_reactions or not perms.embed_links:
            return await interaction.followup.send(
                embed=embed("❌ Permission Kurang!",
                    f"Bot butuh **Send Messages**, **Add Reactions**, **Embed Links** di {channel.mention}.",
                    0xED4245),
                ephemeral=True,
            )

        # Kirim embed ke channel
        e = discord.Embed(
            title=f"✅ {judul}",
            description=f"{deskripsi}\n\n"
                        f"**Role yang didapat:** {role.mention}\n\n"
                        f"Klik ✅ di bawah untuk mendapatkan / melepas role.",
            color=self.BOT_COLOR,
        )
        e.set_footer(text=f"Server: {interaction.guild.name}")

        msg = await channel.send(embed=e)
        await msg.add_reaction("✅")

        # Simpan ke database
        await self.db.add_autorole(interaction.guild_id, channel.id, msg.id, role.id)

        await interaction.followup.send(
            embed=embed("✅ Auto Role Berhasil Dibuat!",
                f"Pesan sudah dikirim ke {channel.mention}\n"
                f"Role: {role.mention}\n"
                f"User tinggal klik ✅ untuk dapat role!",
                0x57F287),
            ephemeral=True,
        )

    # ── REMOVE ────────────────────────────────────────────────────────────────
    @autorole.command(name="remove", description="Hapus auto role dari server")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_roles=True)
    async def autorole_remove(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(ephemeral=True)

        removed = await self.db.remove_autorole(interaction.guild_id, role.id)
        if not removed:
            return await interaction.followup.send(
                embed=embed("❌ Tidak Ditemukan",
                    f"Tidak ada auto role untuk {role.mention}.", 0xED4245),
                ephemeral=True,
            )

        await interaction.followup.send(
            embed=embed("✅ Auto Role Dihapus!", f"Auto role untuk {role.mention} sudah dihapus.", 0x57F287),
            ephemeral=True,
        )

    # ── LIST ──────────────────────────────────────────────────────────────────
    @autorole.command(name="list", description="Lihat semua auto role yang aktif di server ini")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_roles=True)
    async def autorole_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        rows = await self.db.get_autoroles(interaction.guild_id)
        if not rows:
            return await interaction.followup.send(
                embed=embed("📋 Belum Ada Auto Role",
                    "Gunakan `/autorole setup` untuk membuat auto role.", 0x95A5A6),
                ephemeral=True,
            )

        e = discord.Embed(title="🎭 Daftar Auto Role", color=self.BOT_COLOR)
        for row in rows:
            role    = interaction.guild.get_role(row["role_id"])
            channel = interaction.guild.get_channel(row["channel_id"])
            e.add_field(
                name=f"{role.name if role else 'Role Dihapus'}",
                value=f"Channel: {channel.mention if channel else 'Dihapus'}\n"
                      f"Message ID: `{row['message_id']}`",
                inline=False,
            )

        await interaction.followup.send(embed=e, ephemeral=True)

    # ── EVENT: on_raw_reaction_add ────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) != "✅":
            return

        row = await self.db.get_autorole_by_message(payload.guild_id, payload.message_id)
        if not row:
            return

        guild  = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role   = guild.get_role(row["role_id"])

        if not member or not role:
            return

        try:
            await member.add_roles(role, reason="Auto Role — reaksi ✅")
            log.info(f"AutoRole: gave {role.name} to {member}")
        except discord.Forbidden:
            log.warning(f"AutoRole: cannot give role {role.name} — missing permissions")

    # ── EVENT: on_raw_reaction_remove ─────────────────────────────────────────
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) != "✅":
            return

        row = await self.db.get_autorole_by_message(payload.guild_id, payload.message_id)
        if not row:
            return

        guild  = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role   = guild.get_role(row["role_id"])

        if not member or not role:
            return

        try:
            await member.remove_roles(role, reason="Auto Role — reaksi ✅ dilepas")
            log.info(f"AutoRole: removed {role.name} from {member}")
        except discord.Forbidden:
            log.warning(f"AutoRole: cannot remove role {role.name} — missing permissions")


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRole(bot))
