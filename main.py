import discord
from discord.ext import commands
import asyncio
import os
import logging
import time
import random
from dotenv import load_dotenv

from utils.database import Database
from utils.helpers import level_from_xp
from bot.cogs import load_cogs

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ApexBot")


class ApexBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

        self.db = Database("apex_bot.db")
        self.config = {
            "BOT_COLOR": 0x57F287,
            "DAILY_COINS": 500,
            "WORK_COOLDOWN": 3600,
            "DAILY_COOLDOWN": 86400,
            "WORK_JOBS": [
                ("Cashier",    (50,  150)),
                ("Programmer", (200, 500)),
                ("Streamer",   (100, 300)),
                ("Trader",     (150, 400)),
                ("Farmer",     (75,  200)),
            ],
        }

    async def setup_hook(self):
        await self.db.connect()
        await load_cogs(self)
        synced = await self.tree.sync()
        log.info(f"Synced {len(synced)} commands")


bot = ApexBot()


async def _get_channel(guild: discord.Guild, channel_id: int):
    """
    FIX: Cari channel dengan 3 cara:
    1. guild.get_channel()  — dari cache guild
    2. bot.get_channel()    — dari cache global
    3. guild.fetch_channel() — API call (paling lambat tapi pasti dapat)
    """
    channel = guild.get_channel(channel_id)
    if channel:
        return channel

    channel = bot.get_channel(channel_id)
    if channel:
        return channel

    try:
        channel = await guild.fetch_channel(channel_id)
        return channel
    except (discord.NotFound, discord.Forbidden):
        return None


@bot.event
async def on_ready():
    print(f"Bot online: {bot.user}")


@bot.event
async def on_error(event, *args, **kwargs):
    log.error(f"Error in {event}", exc_info=True)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Global handler untuk semua app command error — mencegah 'did not respond'."""

    # Ambil error asli kalau dibungkus
    if isinstance(error, discord.app_commands.CommandInvokeError):
        error = error.original

    # Tentukan pesan error
    if isinstance(error, discord.app_commands.MissingPermissions):
        perms = ", ".join(error.missing_permissions)
        msg = f"Kamu tidak punya permission yang dibutuhkan: **{perms}**"
    elif isinstance(error, discord.app_commands.BotMissingPermissions):
        perms = ", ".join(error.missing_permissions)
        msg = f"Bot tidak punya permission: **{perms}**\nBerikan permission tersebut ke bot dulu!"
    elif isinstance(error, discord.app_commands.CommandOnCooldown):
        msg = f"Cooldown! Coba lagi dalam **{error.retry_after:.0f} detik**."
    elif isinstance(error, discord.app_commands.NoPrivateMessage):
        msg = "Command ini hanya bisa dipakai di server, bukan DM."
    elif isinstance(error, discord.app_commands.CheckFailure):
        msg = "Kamu tidak memenuhi syarat untuk menggunakan command ini."
    else:
        msg = f"Terjadi error: {str(error)[:200]}"
        log.error(f"Unhandled app command error: {error}", exc_info=True)

    e = discord.Embed(title="❌ Error", description=msg, color=0xED4245)

    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=e, ephemeral=True)
        else:
            await interaction.followup.send(embed=e, ephemeral=True)
    except Exception:
        pass  # Kalau sudah expired, diam saja


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    try:
        usr     = await bot.db.get_user(message.author.id, message.guild.id)
        now     = time.time()
        last_xp = usr.get("last_xp_ts", 0)

        if now - last_xp > 10:
            xp_gained = random.randint(5, 15)
            new_xp    = usr.get("xp", 0) + xp_gained
            old_level = usr.get("level", 0)
            new_level = level_from_xp(new_xp)

            await bot.db.set_user(
                message.author.id, message.guild.id,
                xp=new_xp, level=new_level, last_xp_ts=now,
            )

            if new_level > old_level:
                e = discord.Embed(
                    title="⭐ Level Up!",
                    description=f"{message.author.mention} reached level **{new_level}**!",
                    color=0x57F287,
                )
                await message.channel.send(embed=e)

    except Exception as err:
        log.error(f"Error in on_message XP: {err}")

    await bot.process_commands(message)


@bot.event
async def on_member_join(member: discord.Member):
    try:
        gs = await bot.db.get_guild(member.guild.id)
        channel_id = gs.get("welcome_channel") if gs else None
        if not channel_id:
            return

        channel = await _get_channel(member.guild, int(channel_id))
        if not channel:
            return

        # Coba buat welcome image pakai Pillow
        from utils.helpers import generate_welcome_card, PILLOW_OK
        if PILLOW_OK:
            try:
                avatar_bytes = await member.display_avatar.with_size(256).read()
                loop = asyncio.get_running_loop()
                card_bytes = await loop.run_in_executor(
                    None,
                    generate_welcome_card,
                    avatar_bytes,
                    str(member.name),
                    member.guild.name,
                    member.guild.member_count,
                )
                import io
                file = discord.File(io.BytesIO(card_bytes), filename="welcome.png")
                e = discord.Embed(
                    description=f"Selamat datang {member.mention} di **{member.guild.name}**! 🎉",
                    color=0x57F287,
                )
                e.set_image(url="attachment://welcome.png")
                await channel.send(file=file, embed=e)
                return
            except Exception as img_err:
                log.warning(f"Welcome image error: {img_err}")

        # Fallback embed tanpa image
        e = discord.Embed(
            title="🎉 Welcome!",
            description=f"Welcome {member.mention} to **{member.guild.name}**!",
            color=0x57F287,
        )
        e.set_thumbnail(url=member.display_avatar.url)
        e.set_footer(text=f"Member #{member.guild.member_count}")
        await channel.send(embed=e)

    except Exception as err:
        log.error(f"Error in on_member_join: {err}")


@bot.event
async def on_member_remove(member: discord.Member):
    try:
        gs = await bot.db.get_guild(member.guild.id)
        channel_id = gs.get("goodbye_channel") if gs else None
        if not channel_id:
            return

        # FIX: gunakan _get_channel agar tidak gagal karena cache miss
        channel = await _get_channel(member.guild, int(channel_id))
        if not channel:
            return

        e = discord.Embed(
            title="👋 Goodbye!",
            description=f"**{member.name}** has left the server.",
            color=0xED4245,
        )
        e.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=e)

    except Exception as err:
        log.error(f"Error in on_member_remove: {err}")


async def main():
    async with bot:
        try:
            await bot.start(TOKEN)
        finally:
            await bot.db.close()


if __name__ == "__main__":
    asyncio.run(main())
