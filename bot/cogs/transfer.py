"""
Transfer Cog - Coin Transfer & Coinflip
Commands:
  /transfer  - Kirim koin ke user lain
  /coinflip  - Tantang user lain lempar koin, menang dapat semua taruhan
"""

import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

from utils.embeds import embed
from utils.helpers import coins_fmt


class Transfer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db
        self.BOT_COLOR = bot.config.get("BOT_COLOR", 0x57F287)

        # Simpan sesi coinflip yang sedang menunggu {challenger_id: data}
        self._cf_sessions: dict[int, dict] = {}

    # ══════════════════════════════════════════════════════════════════════════
    #  💸 COIN TRANSFER
    # ══════════════════════════════════════════════════════════════════════════
    @app_commands.command(name="transfer", description="Kirim koin ke user lain")
    @app_commands.guild_only()
    async def transfer(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        jumlah: int,
    ):
        await interaction.response.defer()

        # Validasi target
        if user.id == interaction.user.id:
            return await interaction.followup.send(
                embed=embed("❌ Tidak Bisa!", "Kamu tidak bisa transfer koin ke diri sendiri.", 0xED4245)
            )
        if user.bot:
            return await interaction.followup.send(
                embed=embed("❌ Tidak Bisa!", "Kamu tidak bisa transfer koin ke bot.", 0xED4245)
            )
        if jumlah <= 0:
            return await interaction.followup.send(
                embed=embed("❌ Jumlah Salah!", "Jumlah transfer minimal 1 koin.", 0xED4245)
            )

        # Cek saldo pengirim
        sender = await self.db.get_user(interaction.user.id, interaction.guild_id)
        bal    = sender.get("balance", 0)

        if jumlah > bal:
            return await interaction.followup.send(
                embed=embed("❌ Koin Tidak Cukup!",
                    f"Kamu punya **{coins_fmt(bal)}** tapi mau transfer **{coins_fmt(jumlah)}**.",
                    0xED4245)
            )

        # Proses transfer
        await self.db.add_balance(interaction.user.id, interaction.guild_id, -jumlah)
        await self.db.add_balance(user.id, interaction.guild_id, jumlah)

        sender_new = await self.db.get_user(interaction.user.id, interaction.guild_id)

        e = discord.Embed(title="💸 Transfer Berhasil!", color=0x57F287)
        e.add_field(name="Pengirim",  value=interaction.user.mention, inline=True)
        e.add_field(name="Penerima",  value=user.mention,             inline=True)
        e.add_field(name="Jumlah",    value=f"**{coins_fmt(jumlah)}** 🪙", inline=False)
        e.add_field(name="Sisa Saldo", value=coins_fmt(sender_new.get("balance", 0)), inline=True)

        await interaction.followup.send(embed=e)

        # Notif ke penerima via DM
        try:
            await user.send(
                embed=embed(
                    "💸 Kamu Dapat Transfer Koin!",
                    f"**{interaction.user}** mengirim **{coins_fmt(jumlah)}** 🪙 ke kamu\n"
                    f"di server **{interaction.guild.name}**!",
                    0x57F287,
                )
            )
        except discord.Forbidden:
            pass  # DM dimatikan, tidak masalah

    # ══════════════════════════════════════════════════════════════════════════
    #  🎳 COINFLIP
    # ══════════════════════════════════════════════════════════════════════════
    @app_commands.command(name="coinflip", description="Tantang user lain lempar koin — menang dapat semua taruhan!")
    @app_commands.guild_only()
    async def coinflip(
        self,
        interaction: discord.Interaction,
        lawan: discord.Member,
        taruhan: int,
    ):
        await interaction.response.defer()

        # Validasi
        if lawan.id == interaction.user.id:
            return await interaction.followup.send(
                embed=embed("❌ Tidak Bisa!", "Kamu tidak bisa tantang diri sendiri.", 0xED4245)
            )
        if lawan.bot:
            return await interaction.followup.send(
                embed=embed("❌ Tidak Bisa!", "Kamu tidak bisa tantang bot.", 0xED4245)
            )
        if taruhan <= 0:
            return await interaction.followup.send(
                embed=embed("❌ Taruhan Salah!", "Taruhan minimal 1 koin.", 0xED4245)
            )
        if interaction.user.id in self._cf_sessions:
            return await interaction.followup.send(
                embed=embed("❌ Masih Ada Tantangan!", "Selesaikan coinflip sebelumnya dulu.", 0xED4245)
            )

        # Cek saldo penantang
        challenger_data = await self.db.get_user(interaction.user.id, interaction.guild_id)
        if challenger_data.get("balance", 0) < taruhan:
            return await interaction.followup.send(
                embed=embed("❌ Koin Tidak Cukup!",
                    f"Kamu butuh **{coins_fmt(taruhan)}** untuk menantang.", 0xED4245)
            )

        # Simpan sesi
        self._cf_sessions[interaction.user.id] = {
            "challenger": interaction.user,
            "opponent":   lawan,
            "taruhan":    taruhan,
            "guild_id":   interaction.guild_id,
        }

        # Buat view dengan tombol Terima/Tolak
        view = CoinflipView(
            bot=self.bot,
            db=self.db,
            sessions=self._cf_sessions,
            challenger=interaction.user,
            opponent=lawan,
            taruhan=taruhan,
            guild_id=interaction.guild_id,
        )

        e = discord.Embed(
            title="🎳 Tantangan Coinflip!",
            description=f"{lawan.mention}, kamu ditantang oleh {interaction.user.mention}!\n\n"
                        f"**Taruhan:** {coins_fmt(taruhan)} 🪙 masing-masing\n"
                        f"**Total Hadiah:** {coins_fmt(taruhan * 2)} 🪙\n\n"
                        f"Terima atau tolak tantangan ini?",
            color=0xFEE75C,
        )
        e.set_footer(text="Tantangan hangus dalam 60 detik jika tidak direspon")

        await interaction.followup.send(
            content=lawan.mention,
            embed=e,
            view=view,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  COINFLIP VIEW
# ══════════════════════════════════════════════════════════════════════════════

class CoinflipView(discord.ui.View):
    def __init__(self, bot, db, sessions, challenger, opponent, taruhan, guild_id):
        super().__init__(timeout=60.0)
        self.bot        = bot
        self.db         = db
        self.sessions   = sessions
        self.challenger = challenger
        self.opponent   = opponent
        self.taruhan    = taruhan
        self.guild_id   = guild_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                "❌ Hanya lawan yang bisa merespon tantangan ini!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Terima", style=discord.ButtonStyle.success, emoji="✅")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.stop()
        self._disable_all()

        # Cek saldo lawan
        opp_data = await self.db.get_user(self.opponent.id, self.guild_id)
        if opp_data.get("balance", 0) < self.taruhan:
            self.sessions.pop(self.challenger.id, None)
            return await interaction.followup.send(
                embed=embed("❌ Koin Tidak Cukup!",
                    f"{self.opponent.mention} tidak punya cukup koin untuk menerima tantangan.",
                    0xED4245)
            )

        # Kurangi taruhan kedua user
        await self.db.add_balance(self.challenger.id, self.guild_id, -self.taruhan)
        await self.db.add_balance(self.opponent.id,   self.guild_id, -self.taruhan)

        # Animasi lempar koin
        coin_msg = await interaction.followup.send("🪙 Melempar koin...")
        await asyncio.sleep(1)
        await coin_msg.edit(content="🌀 Koin berputar...")
        await asyncio.sleep(1)

        # Tentukan pemenang
        winner = random.choice([self.challenger, self.opponent])
        loser  = self.opponent if winner.id == self.challenger.id else self.challenger
        hadiah = self.taruhan * 2

        await self.db.add_balance(winner.id, self.guild_id, hadiah)
        self.sessions.pop(self.challenger.id, None)

        coin_result = random.choice(["HEADS 👑", "TAILS 🦅"])

        e = discord.Embed(title="🎳 Coinflip Selesai!", color=0xF1C40F)
        e.add_field(name="Hasil Koin", value=f"**{coin_result}**", inline=False)
        e.add_field(name="🏆 Pemenang", value=winner.mention, inline=True)
        e.add_field(name="💸 Kalah",    value=loser.mention,  inline=True)
        e.add_field(name="💰 Hadiah",   value=f"**{coins_fmt(hadiah)}** 🪙", inline=False)

        await coin_msg.edit(content=None, embed=e)

    @discord.ui.button(label="Tolak", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        self._disable_all()
        self.sessions.pop(self.challenger.id, None)

        await interaction.response.send_message(
            embed=embed("❌ Tantangan Ditolak!",
                f"{self.opponent.mention} menolak tantangan coinflip dari {self.challenger.mention}.",
                0xED4245)
        )

    def _disable_all(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def on_timeout(self):
        self._disable_all()
        self.sessions.pop(self.challenger.id, None)


async def setup(bot: commands.Bot):
    await bot.add_cog(Transfer(bot))
