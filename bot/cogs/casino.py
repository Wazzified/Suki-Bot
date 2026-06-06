"""
Casino Cog - Slot Machine, Blackjack, Dadu, Roulette + Casino Help
"""

import discord
from discord import app_commands
from discord.ext import commands
import random
from typing import Optional

from utils.database import Database
from utils.embeds import embed
from utils.helpers import coins_fmt


def _parse_bet(amount: str, balance: int):
    if amount.lower() == "all":
        if balance <= 0:
            return None, "Koin kamu kosong!"
        return balance, None
    try:
        amt = int(amount)
    except ValueError:
        return None, "Taruhan harus angka atau `all`."
    if amt <= 0:
        return None, "Taruhan minimal 1 koin."
    if amt > balance:
        return None, f"Koin tidak cukup! Kamu punya **{coins_fmt(balance)}**."
    return amt, None


class Casino(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: Database = bot.db
        self.COLOR = bot.config.get("BOT_COLOR", 0xF1C40F)
        self._bj_sessions: dict[int, dict] = {}

    # ── SLOT MACHINE ──────────────────────────────────────────────────────────
    SLOTS = ["7", "D", "S", "G", "O", "L", "C"]
    SLOT_EMOJI = {"7": "7️⃣", "D": "💎", "S": "⭐", "G": "🍇", "O": "🍊", "L": "🍋", "C": "🍒"}
    SLOT_WEIGHTS = [1, 3, 6, 15, 20, 25, 30]
    SLOT_PAYOUTS = {"7": 50, "D": 20, "S": 10, "G": 5, "O": 3, "L": 2, "C": 1.5}

    def _spin(self):
        return [random.choices(self.SLOTS, weights=self.SLOT_WEIGHTS, k=1)[0] for _ in range(3)]

    def _slot_result(self, reels, bet):
        a, b, c = reels
        if a == b == c:
            mult = self.SLOT_PAYOUTS[a]
            return int(bet * mult), f"JACKPOT! 3x {self.SLOT_EMOJI[a]} = **{mult}x** taruhan!"
        if a == b or b == c or a == c:
            return int(bet * 0.5), "Dua sama — dapat **0.5x** taruhan balik."
        return 0, "Tidak ada yang cocok. Coba lagi!"

    @app_commands.command(name="slot", description="Putar slot machine dan menangkan koin!")
    async def slot(self, interaction: discord.Interaction, taruhan: str):
        await interaction.response.defer()
        usr = await self.db.get_user(interaction.user.id, interaction.guild_id)
        bal = usr.get("balance", 0)
        bet, err = _parse_bet(taruhan, bal)
        if err:
            return await interaction.followup.send(embed=embed("Taruhan Error", err, 0xED4245))

        reels = self._spin()
        win, txt = self._slot_result(reels, bet)
        net = win - bet
        await self.db.add_balance(interaction.user.id, interaction.guild_id, net)

        display = "  ".join(self.SLOT_EMOJI[r] for r in reels)
        color = 0xF1C40F if win > bet else (0x57F287 if win > 0 else 0xED4245)
        new_bal = bal + net

        e = discord.Embed(title="Slot Machine", color=color)
        e.add_field(name="Gulungan", value=f"[ {display} ]", inline=False)
        e.add_field(name="Hasil", value=txt, inline=False)
        e.add_field(name="Menang" if net >= 0 else "Kalah",
                    value=f"+{coins_fmt(win)}" if net >= 0 else f"-{coins_fmt(bet)}", inline=True)
        e.add_field(name="Saldo", value=coins_fmt(new_bal), inline=True)
        await interaction.followup.send(embed=e)

    # ── DADU ──────────────────────────────────────────────────────────────────
    @app_commands.command(name="dadu", description="Lempar dadu! Siapa lebih tinggi menang.")
    async def dadu(self, interaction: discord.Interaction, taruhan: str):
        await interaction.response.defer()
        usr = await self.db.get_user(interaction.user.id, interaction.guild_id)
        bal = usr.get("balance", 0)
        bet, err = _parse_bet(taruhan, bal)
        if err:
            return await interaction.followup.send(embed=embed("Taruhan Error", err, 0xED4245))

        DICE = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
        p = random.randint(1, 6)
        d = random.randint(1, 6)

        if p > d:
            net, txt, color = bet, f"Kamu menang! ({p} > {d})", 0x57F287
        elif p < d:
            net, txt, color = -bet, f"Dealer menang! ({p} < {d})", 0xED4245
        else:
            net, txt, color = 0, f"Seri! ({p} = {d}) Taruhan kembali.", 0xFEE75C

        await self.db.add_balance(interaction.user.id, interaction.guild_id, net)
        new_bal = bal + net

        e = discord.Embed(title="Lempar Dadu", color=color)
        e.add_field(name="Kamu", value=f"{DICE[p-1]} {p}", inline=True)
        e.add_field(name="Dealer", value=f"{DICE[d-1]} {d}", inline=True)
        e.add_field(name="Hasil", value=txt, inline=False)
        e.add_field(name="Menang" if net > 0 else ("Seri" if net == 0 else "Kalah"),
                    value=f"+{coins_fmt(net)}" if net > 0 else (coins_fmt(bet) if net == 0 else f"-{coins_fmt(bet)}"),
                    inline=True)
        e.add_field(name="Saldo", value=coins_fmt(new_bal), inline=True)
        await interaction.followup.send(embed=e)

    # ── ROULETTE ──────────────────────────────────────────────────────────────
    RED = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
    BLACK = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}

    @app_commands.command(name="roulette", description="Taruhan roulette! Pilih: merah/hitam/ganjil/genap/angka 0-36")
    async def roulette(self, interaction: discord.Interaction, taruhan: str, pilihan: str):
        await interaction.response.defer()
        usr = await self.db.get_user(interaction.user.id, interaction.guild_id)
        bal = usr.get("balance", 0)
        bet, err = _parse_bet(taruhan, bal)
        if err:
            return await interaction.followup.send(embed=embed("Taruhan Error", err, 0xED4245))

        pilihan = pilihan.lower().strip()
        valid = ["merah", "hitam", "ganjil", "genap"] + [str(i) for i in range(37)]
        if pilihan not in valid:
            return await interaction.followup.send(
                embed=embed("Pilihan Salah",
                    "Pilihan valid: `merah` `hitam` `ganjil` `genap` atau angka `0`-`36`", 0xED4245))

        result = random.randint(0, 36)
        circle = "🟢" if result == 0 else ("🔴" if result in self.RED else "⚫")

        won, mult = False, 1
        if pilihan == "merah":
            won = result in self.RED
        elif pilihan == "hitam":
            won = result in self.BLACK
        elif pilihan == "ganjil":
            won = result != 0 and result % 2 == 1
        elif pilihan == "genap":
            won = result != 0 and result % 2 == 0
        else:
            won = result == int(pilihan)
            mult = 35

        net = bet * mult if won else -bet
        await self.db.add_balance(interaction.user.id, interaction.guild_id, net)
        new_bal = bal + net

        e = discord.Embed(title="Roulette", color=0x57F287 if won else 0xED4245)
        e.add_field(name="Hasil", value=f"{circle} **{result}**", inline=True)
        e.add_field(name="Pilihanmu", value=f"`{pilihan}`", inline=True)
        e.add_field(name="Status", value="MENANG!" if won else "KALAH!", inline=False)
        e.add_field(name="Menang" if won else "Kalah",
                    value=f"+{coins_fmt(net)}" if won else f"-{coins_fmt(bet)}", inline=True)
        e.add_field(name="Saldo", value=coins_fmt(new_bal), inline=True)
        if mult == 35:
            e.set_footer(text="Taruhan angka spesifik bayar 35x!")
        await interaction.followup.send(embed=e)

    # ── BLACKJACK ─────────────────────────────────────────────────────────────
    BJ_SUITS = ["S", "H", "D", "C"]
    BJ_SUIT_EMOJI = {"S": "♠️", "H": "♥️", "D": "♦️", "C": "♣️"}
    BJ_VALS = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]

    def _new_deck(self):
        deck = [(v, s) for s in self.BJ_SUITS for v in self.BJ_VALS]
        random.shuffle(deck)
        return deck

    def _card_val(self, card):
        v = card[0]
        if v in ["J","Q","K"]: return 10
        if v == "A": return 11
        return int(v)

    def _hand_val(self, hand):
        total = sum(self._card_val(c) for c in hand)
        aces = sum(1 for c in hand if c[0] == "A")
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    def _fmt_hand(self, hand, hide=False):
        if hide and len(hand) > 1:
            v, s = hand[0]
            return f"{v}{self.BJ_SUIT_EMOJI[s]}  🂠"
        return "  ".join(f"{v}{self.BJ_SUIT_EMOJI[s]}" for v, s in hand)

    @app_commands.command(name="blackjack", description="Main Blackjack! Kalahkan dealer tanpa melebihi 21.")
    async def blackjack(self, interaction: discord.Interaction, taruhan: str):
        await interaction.response.defer()
        uid, gid = interaction.user.id, interaction.guild_id

        if uid in self._bj_sessions:
            return await interaction.followup.send(
                embed=embed("Masih Ada Sesi!",
                    "Selesaikan dulu game kamu!\nGunakan `/bj_hit`, `/bj_stand`, atau `/bj_double`.", 0xED4245))

        usr = await self.db.get_user(uid, gid)
        bal = usr.get("balance", 0)
        bet, err = _parse_bet(taruhan, bal)
        if err:
            return await interaction.followup.send(embed=embed("Taruhan Error", err, 0xED4245))

        await self.db.add_balance(uid, gid, -bet)
        deck = self._new_deck()
        player = [deck.pop(), deck.pop()]
        dealer = [deck.pop(), deck.pop()]
        self._bj_sessions[uid] = {"player": player, "dealer": dealer, "deck": deck, "bet": bet, "guild_id": gid}

        if self._hand_val(player) == 21:
            return await self._bj_end(interaction, uid, "blackjack")

        e = discord.Embed(title="Blackjack", color=0x2F3136)
        e.add_field(name="Dealer", value=self._fmt_hand(dealer, hide=True), inline=False)
        e.add_field(name=f"Kamu ({self._hand_val(player)})", value=self._fmt_hand(player), inline=False)
        e.add_field(name="Taruhan", value=coins_fmt(bet), inline=True)
        e.set_footer(text="/bj_hit = ambil kartu | /bj_stand = berhenti | /bj_double = double down")
        await interaction.followup.send(embed=e)

    @app_commands.command(name="bj_hit", description="Blackjack: Ambil satu kartu lagi")
    async def bj_hit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        uid = interaction.user.id
        if uid not in self._bj_sessions:
            return await interaction.followup.send(
                embed=embed("Tidak Ada Sesi", "Mulai dulu dengan `/blackjack <taruhan>`.", 0xED4245))

        sess = self._bj_sessions[uid]
        sess["player"].append(sess["deck"].pop())
        pv = self._hand_val(sess["player"])

        if pv > 21:
            return await self._bj_end(interaction, uid, "bust")
        if pv == 21:
            return await self._bj_end(interaction, uid, "stand")

        e = discord.Embed(title="Blackjack - Hit!", color=0x2F3136)
        e.add_field(name="Dealer", value=self._fmt_hand(sess["dealer"], hide=True), inline=False)
        e.add_field(name=f"Kamu ({pv})", value=self._fmt_hand(sess["player"]), inline=False)
        e.set_footer(text="/bj_hit | /bj_stand | /bj_double")
        await interaction.followup.send(embed=e)

    @app_commands.command(name="bj_stand", description="Blackjack: Berhenti, giliran dealer main")
    async def bj_stand(self, interaction: discord.Interaction):
        await interaction.response.defer()
        uid = interaction.user.id
        if uid not in self._bj_sessions:
            return await interaction.followup.send(
                embed=embed("Tidak Ada Sesi", "Mulai dulu dengan `/blackjack <taruhan>`.", 0xED4245))
        await self._bj_end(interaction, uid, "stand")

    @app_commands.command(name="bj_double", description="Blackjack: Double down — taruhan 2x, ambil 1 kartu lagi")
    async def bj_double(self, interaction: discord.Interaction):
        await interaction.response.defer()
        uid = interaction.user.id
        if uid not in self._bj_sessions:
            return await interaction.followup.send(
                embed=embed("Tidak Ada Sesi", "Mulai dulu dengan `/blackjack <taruhan>`.", 0xED4245))

        sess = self._bj_sessions[uid]
        gid = sess["guild_id"]
        usr = await self.db.get_user(uid, gid)
        if usr.get("balance", 0) < sess["bet"]:
            return await interaction.followup.send(
                embed=embed("Koin Tidak Cukup",
                    f"Double down butuh **{coins_fmt(sess['bet'])}** tambahan.", 0xED4245))

        await self.db.add_balance(uid, gid, -sess["bet"])
        sess["bet"] *= 2
        sess["player"].append(sess["deck"].pop())
        pv = self._hand_val(sess["player"])
        await self._bj_end(interaction, uid, "bust" if pv > 21 else "stand")

    async def _bj_end(self, interaction: discord.Interaction, uid: int, reason: str):
        sess = self._bj_sessions.pop(uid, None)
        if not sess:
            return

        gid = sess["guild_id"]
        bet, player, dealer, deck = sess["bet"], sess["player"], sess["dealer"], sess["deck"]
        pv = self._hand_val(player)

        while self._hand_val(dealer) < 17:
            dealer.append(deck.pop())
        dv = self._hand_val(dealer)

        if reason == "blackjack":
            payout, txt, color = int(bet * 2.5), "BLACKJACK! Bayar 1.5x!", 0xF1C40F
        elif reason == "bust" or pv > 21:
            payout, txt, color = 0, f"BUST! Kamu melebihi 21 ({pv}).", 0xED4245
        elif dv > 21:
            payout, txt, color = bet * 2, f"Dealer Bust ({dv})! Kamu menang!", 0x57F287
        elif pv > dv:
            payout, txt, color = bet * 2, f"Kamu Menang! ({pv} vs {dv})", 0x57F287
        elif pv == dv:
            payout, txt, color = bet, f"Seri! ({pv} vs {dv}) Taruhan kembali.", 0xFEE75C
        else:
            payout, txt, color = 0, f"Dealer Menang! ({pv} vs {dv})", 0xED4245

        if payout > 0:
            await self.db.add_balance(uid, gid, payout)

        usr = await self.db.get_user(uid, gid)
        net = payout - bet

        e = discord.Embed(title="Blackjack - Selesai!", color=color)
        e.add_field(name=f"Dealer ({dv})", value=self._fmt_hand(dealer), inline=False)
        e.add_field(name=f"Kamu ({pv})", value=self._fmt_hand(player), inline=False)
        e.add_field(name="Hasil", value=txt, inline=False)
        e.add_field(name="Menang" if net >= 0 else "Kalah",
                    value=f"+{coins_fmt(net)}" if net >= 0 else f"-{coins_fmt(bet)}", inline=True)
        e.add_field(name="Saldo", value=coins_fmt(usr.get("balance", 0)), inline=True)
        await interaction.followup.send(embed=e)

    # ── CASINO HELP ───────────────────────────────────────────────────────────
    @app_commands.command(name="casino_help", description="Panduan lengkap cara main semua game casino")
    async def casino_help(self, interaction: discord.Interaction):
        e = discord.Embed(
            title="Panduan Casino",
            description="Semua game casino pakai koin dari wallet. Cek saldo dengan `/balance`.",
            color=0xF1C40F,
        )
        e.add_field(
            name="🎰 /slot <taruhan>",
            value=(
                "Putar 3 gulungan, cocokkan simbol untuk menang.\n"
                "3 sama: 7x7x7=50x | Berlian=20x | Bintang=10x | Anggur=5x | Jeruk=3x | Lemon=2x | Ceri=1.5x\n"
                "2 sama: dapat 0.5x taruhan balik\n"
                "Contoh: `/slot 500` atau `/slot all`"
            ),
            inline=False,
        )
        e.add_field(
            name="🎲 /dadu <taruhan>",
            value=(
                "Lempar dadu 1-6, bandingkan dengan dealer.\n"
                "Kamu lebih tinggi = menang 2x | Sama = seri | Lebih rendah = kalah\n"
                "Contoh: `/dadu 300`"
            ),
            inline=False,
        )
        e.add_field(
            name="🎡 /roulette <taruhan> <pilihan>",
            value=(
                "Pilihan merah/hitam/ganjil/genap = menang 2x\n"
                "Pilihan angka 0 sampai 36 = menang 35x lipat!\n"
                "Contoh: `/roulette 1000 merah` atau `/roulette 100 17`"
            ),
            inline=False,
        )
        e.add_field(
            name="🃏 Blackjack",
            value=(
                "Tujuan: lebih dekat ke 21 dari dealer tanpa melebihi 21.\n"
                "A=1atau11 | J/Q/K=10 | Angka=nilai asli\n"
                "1. `/blackjack <taruhan>` - mulai game\n"
                "2. `/bj_hit` - ambil kartu lagi\n"
                "3. `/bj_stand` - berhenti, giliran dealer\n"
                "4. `/bj_double` - taruhan 2x, 1 kartu terakhir\n"
                "Blackjack (A+10)=1.5x | Menang=2x | Seri=balik | Bust>21=kalah"
            ),
            inline=False,
        )
        e.set_footer(text="Tips: /slot untuk cepat, /blackjack untuk strategi!")
        await interaction.response.send_message(embed=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(Casino(bot))
