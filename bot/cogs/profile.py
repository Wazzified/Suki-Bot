"""
Profile & Basic Cog - ping, help, say, userinfo, avatar, serverinfo, rank
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import io
import logging

from utils.database import Database
from utils.embeds import embed
from utils.helpers import generate_rank_card, xp_for_level, coins_fmt, PILLOW_OK

log = logging.getLogger("ApexBot")


class Profile(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: Database = bot.db
        self.BOT_COLOR = bot.config.get("BOT_COLOR", 0x2F3136)

    # ─── PING ────────────────────────────────────────────────────────────────
    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.defer()

        latency = round(self.bot.latency * 1000)
        color = 0x57F287 if latency < 100 else (0xFEE75C if latency < 200 else 0xED4245)

        e = discord.Embed(
            title="🏓 Pong!",
            description=f"**Latency:** `{latency} ms`",
            color=color,
        )
        await interaction.followup.send(embed=e)

    # ─── HELP ────────────────────────────────────────────────────────────────
    @app_commands.command(name="help", description="View all available bot commands")
    async def help_cmd(self, interaction: discord.Interaction):
        e = discord.Embed(
            title="📖 Suki Bot — Daftar Command",
            description="Gunakan `/` di Discord untuk melihat semua command tersedia.",
            color=self.BOT_COLOR,
        )

        e.add_field(name="🔧 Basic", inline=False,
            value="`/ping` `/help` `/userinfo` `/avatar` `/serverinfo` `/rank` `/leaderboard`")

        e.add_field(name="💰 Economy", inline=False, value=(
            "`/balance` `/daily` `/work` `/deposit` `/withdraw`\n"
            "`/transfer` — kirim koin ke user lain\n"
            "`/coinflip` — tantang user lain lempar koin"
        ))

        e.add_field(name="🎣 Sidejob", inline=False, value=(
            "`/shop` `/buy` `/inventory` `/sell` `/sellall`\n"
            "`/fish` — mancing (butuh rod + umpan)\n"
            "`/hunt` — berburu (butuh rifle + peluru)\n"
            "`/mine` — tambang (butuh pickaxe)"
        ))

        e.add_field(name="🎰 Casino", inline=False, value=(
            "`/slot` `/dadu` `/roulette`\n"
            "`/blackjack` `/bj_hit` `/bj_stand` `/bj_double`\n"
            "`/casino_help` — panduan lengkap cara main casino"
        ))

        e.add_field(name="🎮 Games", inline=False, value=(
            "`/trivia` — kuis 4 pilihan, benar dapat koin\n"
            "`/tebakkata` — tebak kata dari huruf acak\n"
            "`/tebakangka` — tebak angka 1-100 dengan hint"
        ))

        e.add_field(name="🤖 Chatbot AI", inline=False, value=(
            "`/chat <pesan>` — ngobrol dengan AI\n"
            "`/chatreset` — reset riwayat percakapan"
        ))

        e.add_field(name="⏰ Utilities", inline=False, value=(
            "`/remind` — set pengingat\n"
            "`/poll` — buat polling ya/tidak"
        ))

        e.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False,
            value="🔐 **ADMIN COMMANDS** — butuh permission khusus")

        e.add_field(name="🔨 Moderasi  *(Kick / Ban / Manage Messages)*", inline=False, value=(
            "`/kick` `/ban` `/unban` `/timeout`\n"
            "`/warn` `/warnings` `/clearwarns`"
        ))

        e.add_field(name="🎭 Auto Role  *(Manage Roles)*", inline=False, value=(
            "`/autorole setup` — buat pesan reaction role\n"
            "`/autorole remove` — hapus auto role\n"
            "`/autorole list` — lihat semua auto role aktif"
        ))

        e.add_field(name="⚙️ Setup Server  *(Manage Server)*", inline=False, value=(
            "`/setup_welcome` — set channel welcome\n"
            "`/setup_goodbye` — set channel goodbye\n"
            "`/setup_log` — set channel log moderasi\n"
            "`/setup_antilink` — aktifkan/matikan anti-link\n"
            "`/chatsetup` — set channel khusus chatbot AI\n"
            "`/say` — bot kirim pesan ke channel"
        ))

        e.set_footer(text="🔐 = Butuh permission admin  |  Suki Bot")
        await interaction.response.send_message(embed=e)

    # ─── USERINFO ────────────────────────────────────────────────────────────
    @app_commands.command(name="userinfo", description="View detailed info about a user")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        await interaction.response.defer()

        m = member or interaction.user
        usr = await self.db.get_user(m.id, interaction.guild_id) or {}

        e = discord.Embed(title=f"👤 {m}", color=self.BOT_COLOR)
        e.set_thumbnail(url=m.display_avatar.url)

        e.add_field(name="ID",       value=str(m.id),         inline=True)
        e.add_field(name="Nickname", value=m.nick or "—",      inline=True)
        e.add_field(name="Roles",    value=len(m.roles) - 1,   inline=True)

        e.add_field(name="Level",  value=usr.get("level", 0),               inline=True)
        e.add_field(name="XP",     value=f"{usr.get('xp', 0):,}",          inline=True)
        e.add_field(name="Coins",  value=coins_fmt(usr.get("balance", 0)), inline=True)

        joined = discord.utils.format_dt(m.joined_at, "R") if m.joined_at else "—"
        created = discord.utils.format_dt(m.created_at, "R")
        e.add_field(name="Joined Server", value=joined,  inline=True)
        e.add_field(name="Account Age",   value=created, inline=True)

        await interaction.followup.send(embed=e)

    # ─── AVATAR ──────────────────────────────────────────────────────────────
    @app_commands.command(name="avatar", description="View a member's avatar in full size")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        m = member or interaction.user

        e = discord.Embed(title=f"🖼️ {m.name}'s Avatar", color=self.BOT_COLOR)
        e.set_image(url=m.display_avatar.with_size(1024).url)

        await interaction.response.send_message(embed=e)

    # ─── SERVERINFO ──────────────────────────────────────────────────────────
    @app_commands.command(name="serverinfo", description="View detailed info about this server")
    async def serverinfo(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Guild only.", ephemeral=True)

        g = interaction.guild
        bots   = sum(1 for m in g.members if m.bot)
        humans = (g.member_count or 0) - bots
        owner  = getattr(g, "owner", None)

        e = discord.Embed(title=f"🏰 {g.name}", color=self.BOT_COLOR)
        if g.icon:
            e.set_thumbnail(url=g.icon.url)

        e.add_field(name="Owner",    value=str(owner) if owner else "Unknown", inline=True)
        e.add_field(name="Members",  value=f"{humans} 👤 / {bots} 🤖",        inline=True)
        e.add_field(name="Roles",    value=len(g.roles),                       inline=True)
        e.add_field(name="Channels", value=len(g.channels),                    inline=True)
        e.add_field(name="Boosts",   value=g.premium_subscription_count,       inline=True)

        created = discord.utils.format_dt(g.created_at, "R")
        e.add_field(name="Created", value=created, inline=True)

        await interaction.response.send_message(embed=e)

    # ─── RANK ────────────────────────────────────────────────────────────────
    @app_commands.command(name="rank", description="View your (or another member's) XP rank card")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        await interaction.response.defer()

        m   = member or interaction.user
        usr = await self.db.get_user(m.id, interaction.guild_id) or {}
        lb  = await self.db.get_leaderboard(interaction.guild_id, 100) or []

        # FIX: Correct rank fallback — shows ">100" if not in top 100, not a wrong number
        rank_entry = next((i + 1 for i, r in enumerate(lb) if r["user_id"] == m.id), None)
        rank_pos   = rank_entry if rank_entry is not None else len(lb) + 1

        lvl     = usr.get("level", 0)
        total_xp = usr.get("xp", 0)
        needed  = xp_for_level(lvl + 1) - xp_for_level(lvl)
        current = total_xp - xp_for_level(lvl)
        current = max(0, current)  # guard against negative values

        if PILLOW_OK:
            try:
                avatar_bytes = await m.display_avatar.with_size(256).read()
                loop = asyncio.get_running_loop()
                card_bytes = await loop.run_in_executor(
                    None,
                    generate_rank_card,
                    avatar_bytes,
                    str(m.name),
                    lvl,
                    current,
                    needed,
                    rank_pos,
                )
                file = discord.File(io.BytesIO(card_bytes), filename="rank.png")
                return await interaction.followup.send(file=file)
            except Exception as exc:
                log.warning("Rank card error: %s", exc)

        # Fallback embed (no Pillow or image error)
        rank_str = f"#{rank_pos}" if rank_entry else f">{len(lb)}"
        e = discord.Embed(title=f"⭐ {m.name}'s Rank", color=self.BOT_COLOR)
        e.set_thumbnail(url=m.display_avatar.url)
        e.add_field(name="Rank",    value=rank_str)
        e.add_field(name="Level",   value=str(lvl))
        e.add_field(name="XP",      value=f"{current:,} / {needed:,}")
        e.add_field(name="Total XP", value=f"{total_xp:,}")
        await interaction.followup.send(embed=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
