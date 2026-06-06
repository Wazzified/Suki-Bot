"""
Admin Cog - Guild setup and configuration commands
"""

import discord
from discord import app_commands
from discord.ext import commands

from utils.database import Database
from utils.embeds import embed


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: Database = bot.db
        self.BOT_COLOR = bot.config["BOT_COLOR"]

    @app_commands.command(name="setup_welcome", description="Set channel untuk pesan selamat datang member baru")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_welcome(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        perms = channel.permissions_for(interaction.guild.me)
        if not perms.send_messages or not perms.embed_links:
            return await interaction.followup.send(
                embed=embed("❌ Bot Tidak Bisa Kirim Pesan!",
                    f"Bot tidak punya permission **Send Messages** atau **Embed Links** di {channel.mention}.\n"
                    "Berikan dulu permission tersebut ke bot!", 0xED4245), ephemeral=True)
        await self.db.set_guild(interaction.guild_id, welcome_channel=channel.id)
        await interaction.followup.send(
            embed=embed("✅ Welcome Channel Diset!",
                f"Pesan selamat datang akan dikirim ke {channel.mention}.", 0x57F287), ephemeral=True)

    @app_commands.command(name="setup_goodbye", description="Set channel untuk pesan perpisahan member keluar")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_goodbye(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        perms = channel.permissions_for(interaction.guild.me)
        if not perms.send_messages or not perms.embed_links:
            return await interaction.followup.send(
                embed=embed("❌ Bot Tidak Bisa Kirim Pesan!",
                    f"Bot tidak punya permission di {channel.mention}.", 0xED4245), ephemeral=True)
        await self.db.set_guild(interaction.guild_id, goodbye_channel=channel.id)
        await interaction.followup.send(
            embed=embed("✅ Goodbye Channel Diset!",
                f"Pesan perpisahan akan dikirim ke {channel.mention}.", 0x57F287), ephemeral=True)

    @app_commands.command(name="setup_log", description="Set channel untuk log moderasi")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_log(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await self.db.set_guild(interaction.guild_id, log_channel=channel.id)
        await interaction.followup.send(
            embed=embed("✅ Log Channel Diset!",
                f"Log moderasi akan dikirim ke {channel.mention}.", 0x57F287), ephemeral=True)

    @app_commands.command(name="setup_antilink", description="Aktifkan/matikan anti-link")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_antilink(self, interaction: discord.Interaction, enabled: bool):
        await interaction.response.defer(ephemeral=True)
        await self.db.set_guild(interaction.guild_id, antilink_enabled=int(enabled))
        status = "Aktif ✅" if enabled else "Nonaktif ❌"
        color  = 0x57F287 if enabled else 0xED4245
        await interaction.followup.send(
            embed=embed(f"🔗 Anti-Link {status}", "Konfigurasi berhasil disimpan.", color), ephemeral=True)

    @app_commands.command(name="say", description="Bot kirim pesan ke channel ini")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def say(self, interaction: discord.Interaction, pesan: str):
        await interaction.response.send_message("✅ Terkirim!", ephemeral=True)
        await interaction.channel.send(pesan)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
