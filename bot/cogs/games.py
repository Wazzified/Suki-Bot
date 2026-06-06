"""
Games Cog - Trivia Quiz, Tebak Kata, Tebak Angka
Commands:
  /trivia      - Kuis trivia, jawab benar dapat koin
  /tebakkata   - Tebak kata dari huruf acak, jawab benar dapat koin
  /tebakangka  - Tebak angka 1-100, ada hint tinggi/rendah
"""

import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

from utils.embeds import embed
from utils.helpers import coins_fmt


# ══════════════════════════════════════════════════════════════════════════════
#  DATA TRIVIA
# ══════════════════════════════════════════════════════════════════════════════

TRIVIA_QUESTIONS = [
    # (pertanyaan, jawaban, pilihan_salah_3)
    ("Ibu kota Indonesia adalah?", "Jakarta", ["Surabaya", "Bandung", "Medan"]),
    ("Berapa hasil dari 15 x 15?", "225", ["200", "215", "250"]),
    ("Planet terbesar di tata surya adalah?", "Jupiter", ["Saturnus", "Uranus", "Neptunus"]),
    ("Siapa penemu bola lampu?", "Thomas Edison", ["Nikola Tesla", "Albert Einstein", "Isaac Newton"]),
    ("Bahasa pemrograman apa yang dipakai untuk membuat bot ini?", "Python", ["Java", "JavaScript", "C++"]),
    ("Berapa jumlah provinsi di Indonesia?", "38", ["34", "36", "40"]),
    ("Gunung tertinggi di dunia adalah?", "Everest", ["K2", "Kilimanjaro", "Fuji"]),
    ("Negara terluas di dunia adalah?", "Rusia", ["Kanada", "Amerika Serikat", "China"]),
    ("Siapa presiden pertama Indonesia?", "Soekarno", ["Soeharto", "Habibie", "Megawati"]),
    ("Hewan apa yang memiliki leher terpanjang?", "Jerapah", ["Unta", "Kuda", "Zebra"]),
    ("Berapa jumlah sisi pada segitiga?", "3", ["4", "5", "6"]),
    ("Apa warna pelangi yang paling atas?", "Merah", ["Kuning", "Ungu", "Hijau"]),
    ("Berapa jumlah pemain dalam satu tim sepak bola?", "11", ["10", "12", "9"]),
    ("Siapa yang menciptakan teori relativitas?", "Albert Einstein", ["Isaac Newton", "Galileo", "Stephen Hawking"]),
    ("Apa nama mata uang Jepang?", "Yen", ["Won", "Yuan", "Baht"]),
    ("Berapa jumlah benua di dunia?", "7", ["5", "6", "8"]),
    ("Air mendidih pada suhu berapa derajat Celsius?", "100", ["90", "110", "80"]),
    ("Apa nama samudra terbesar di dunia?", "Pasifik", ["Atlantik", "Hindia", "Arktik"]),
    ("Siapa yang menulis novel Harry Potter?", "J.K. Rowling", ["Tolkien", "Stephen King", "Roald Dahl"]),
    ("Apa simbol kimia untuk emas?", "Au", ["Ag", "Fe", "Cu"]),
    ("Berapa jumlah huruf dalam alfabet Indonesia?", "26", ["24", "28", "25"]),
    ("Negara mana yang dijuluki Negeri Sakura?", "Jepang", ["China", "Korea", "Thailand"]),
    ("Apa nama planet merah?", "Mars", ["Venus", "Merkurius", "Jupiter"]),
    ("Berapa jumlah warna pada bendera Indonesia?", "2", ["3", "4", "1"]),
    ("Siapa penemu telepon?", "Alexander Graham Bell", ["Thomas Edison", "Nikola Tesla", "Marconi"]),
    ("Apa bahasa resmi Brazil?", "Portugis", ["Spanyol", "Inggris", "Prancis"]),
    ("Hewan apa yang bisa hidup paling lama?", "Kura-kura", ["Gajah", "Paus", "Buaya"]),
    ("Berapa jumlah lubang pada gitar standar?", "1", ["0", "2", "3"]),
    ("Apa nama sungai terpanjang di dunia?", "Nil", ["Amazon", "Yangtze", "Mississippi"]),
    ("Siapa pelukis Mona Lisa?", "Leonardo da Vinci", ["Michelangelo", "Raphael", "Picasso"]),
]

# ══════════════════════════════════════════════════════════════════════════════
#  DATA TEBAK KATA
# ══════════════════════════════════════════════════════════════════════════════

KATA_LIST = [
    "python", "discord", "server", "gaming", "musik", "koding", "laptop",
    "keyboard", "monitor", "internet", "android", "komputer", "robot",
    "hewan", "bunga", "gunung", "sungai", "lautan", "udara", "angin",
    "matahari", "bintang", "bulan", "planet", "galaksi", "meteor",
    "nasi", "ayam", "ikan", "sayur", "buah", "makan", "minum",
    "buku", "pensil", "kertas", "sekolah", "belajar", "pintar",
    "motor", "mobil", "pesawat", "kapal", "kereta", "sepeda",
    "rumah", "gedung", "jembatan", "jalan", "kota", "desa",
]


def _acak_huruf(kata: str) -> str:
    """Acak huruf dalam kata."""
    huruf = list(kata)
    random.shuffle(huruf)
    # Pastikan tidak sama dengan kata asli
    while "".join(huruf) == kata and len(kata) > 1:
        random.shuffle(huruf)
    return "".join(huruf)


# ══════════════════════════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════════════════════════

class Games(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = bot.db
        self.BOT_COLOR = bot.config.get("BOT_COLOR", 0x57F287)

        # Active sessions per channel {channel_id: True}
        self._active: set[int] = set()

    def _lock(self, channel_id: int) -> bool:
        """Return True if channel is free, False if already has active game."""
        if channel_id in self._active:
            return False
        self._active.add(channel_id)
        return True

    def _unlock(self, channel_id: int):
        self._active.discard(channel_id)

    # ══════════════════════════════════════════════════════════════════════════
    #  🧩 TRIVIA QUIZ
    # ══════════════════════════════════════════════════════════════════════════
    @app_commands.command(name="trivia", description="Kuis trivia! Jawab benar dapat koin.")
    @app_commands.guild_only()
    async def trivia(self, interaction: discord.Interaction):
        if not self._lock(interaction.channel_id):
            return await interaction.response.send_message(
                embed=embed("❌ Ada Game Aktif!", "Tunggu game sebelumnya selesai dulu.", 0xED4245),
                ephemeral=True,
            )

        await interaction.response.defer()

        try:
            q, jawaban, salah = random.choice(TRIVIA_QUESTIONS)
            hadiah = random.randint(50, 200)

            # Acak pilihan jawaban
            pilihan = [jawaban] + random.sample(salah, min(3, len(salah)))
            random.shuffle(pilihan)

            e = discord.Embed(
                title="🧩 Trivia Quiz!",
                description=f"**{q}**\n\nHadiah: **{coins_fmt(hadiah)}** 🪙\nWaktu: **20 detik**",
                color=0x3498DB,
            )

            view = TriviaView(
                bot=self.bot,
                db=self.db,
                guild_id=interaction.guild_id,
                jawaban=jawaban,
                pilihan=pilihan,
                hadiah=hadiah,
                unlock_fn=lambda: self._unlock(interaction.channel_id),
            )

            await interaction.followup.send(embed=e, view=view)

        except Exception as err:
            self._unlock(interaction.channel_id)
            await interaction.followup.send(
                embed=embed("❌ Error", str(err), 0xED4245)
            )

    # ══════════════════════════════════════════════════════════════════════════
    #  📝 TEBAK KATA
    # ══════════════════════════════════════════════════════════════════════════
    @app_commands.command(name="tebakkata", description="Tebak kata dari huruf yang diacak! Jawab benar dapat koin.")
    @app_commands.guild_only()
    async def tebakkata(self, interaction: discord.Interaction):
        if not self._lock(interaction.channel_id):
            return await interaction.response.send_message(
                embed=embed("❌ Ada Game Aktif!", "Tunggu game sebelumnya selesai dulu.", 0xED4245),
                ephemeral=True,
            )

        await interaction.response.defer()

        kata  = random.choice(KATA_LIST)
        acak  = _acak_huruf(kata)
        hadiah = len(kata) * random.randint(20, 40)  # Kata lebih panjang = hadiah lebih besar

        e = discord.Embed(
            title="📝 Tebak Kata!",
            description=f"Huruf acak: **`{acak.upper()}`**\n\n"
                        f"Susun huruf di atas menjadi kata yang benar!\n"
                        f"Hadiah: **{coins_fmt(hadiah)}** 🪙\n"
                        f"Waktu: **30 detik**",
            color=0xE67E22,
        )
        e.set_footer(text="Ketik jawaban kamu di chat!")

        await interaction.followup.send(embed=e)

        def check(m: discord.Message):
            return (
                m.channel.id == interaction.channel_id
                and not m.author.bot
                and m.content.lower().strip() == kata.lower()
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30.0)

            # Pemenang!
            await self.db.add_balance(msg.author.id, interaction.guild_id, hadiah)
            await interaction.channel.send(
                embed=embed(
                    "✅ Benar!",
                    f"{msg.author.mention} berhasil menebak kata **{kata.upper()}**!\n"
                    f"Dapat **{coins_fmt(hadiah)}** 🪙",
                    0x57F287,
                )
            )

        except asyncio.TimeoutError:
            await interaction.channel.send(
                embed=embed(
                    "⏰ Waktu Habis!",
                    f"Tidak ada yang berhasil menebak!\nJawaban: **{kata.upper()}**",
                    0xED4245,
                )
            )
        finally:
            self._unlock(interaction.channel_id)

    # ══════════════════════════════════════════════════════════════════════════
    #  🔢 TEBAK ANGKA
    # ══════════════════════════════════════════════════════════════════════════
    @app_commands.command(name="tebakangka", description="Tebak angka 1-100! Ada hint tinggi/rendah.")
    @app_commands.guild_only()
    async def tebakangka(self, interaction: discord.Interaction):
        if not self._lock(interaction.channel_id):
            return await interaction.response.send_message(
                embed=embed("❌ Ada Game Aktif!", "Tunggu game sebelumnya selesai dulu.", 0xED4245),
                ephemeral=True,
            )

        await interaction.response.defer()

        angka  = random.randint(1, 100)
        hadiah = random.randint(100, 300)
        percobaan_max = 7

        e = discord.Embed(
            title="🔢 Tebak Angka!",
            description=f"Aku punya angka antara **1 - 100**!\n\n"
                        f"Tebak angkanya! Kamu punya **{percobaan_max} percobaan**.\n"
                        f"Aku akan kasih hint **Terlalu Tinggi** atau **Terlalu Rendah**.\n\n"
                        f"Hadiah: **{coins_fmt(hadiah)}** 🪙",
            color=0x9B59B6,
        )
        e.set_footer(text="Ketik angka di chat!")
        await interaction.followup.send(embed=e)

        percobaan = 0
        winner    = None

        def check(m: discord.Message):
            return (
                m.channel.id == interaction.channel_id
                and not m.author.bot
                and m.content.strip().isdigit()
            )

        while percobaan < percobaan_max:
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30.0)
            except asyncio.TimeoutError:
                await interaction.channel.send(
                    embed=embed("⏰ Waktu Habis!", f"Jawabannya adalah **{angka}**!", 0xED4245)
                )
                self._unlock(interaction.channel_id)
                return

            tebakan = int(msg.content.strip())
            percobaan += 1
            sisa = percobaan_max - percobaan

            if tebakan == angka:
                winner = msg.author
                break
            elif tebakan < angka:
                hint = "📈 Terlalu Rendah!"
            else:
                hint = "📉 Terlalu Tinggi!"

            if sisa > 0:
                await msg.reply(
                    embed=embed(hint, f"Sisa percobaan: **{sisa}**", 0xFEE75C),
                )
            else:
                await interaction.channel.send(
                    embed=embed("❌ Percobaan Habis!", f"Jawabannya adalah **{angka}**!", 0xED4245)
                )

        if winner:
            bonus = max(100, hadiah - (percobaan - 1) * 30)  # Lebih cepat = bonus lebih besar
            await self.db.add_balance(winner.id, interaction.guild_id, bonus)
            await interaction.channel.send(
                embed=embed(
                    "🎉 Benar!",
                    f"{winner.mention} berhasil menebak angka **{angka}** dalam **{percobaan}** percobaan!\n"
                    f"Dapat **{coins_fmt(bonus)}** 🪙",
                    0x57F287,
                )
            )

        self._unlock(interaction.channel_id)


# ══════════════════════════════════════════════════════════════════════════════
#  TRIVIA VIEW — tombol pilihan jawaban
# ══════════════════════════════════════════════════════════════════════════════

class TriviaView(discord.ui.View):
    def __init__(self, bot, db, guild_id, jawaban, pilihan, hadiah, unlock_fn):
        super().__init__(timeout=20.0)
        self.bot       = bot
        self.db        = db
        self.guild_id  = guild_id
        self.jawaban   = jawaban
        self.hadiah    = hadiah
        self.unlock_fn = unlock_fn
        self.answered  = False

        # Tambah tombol dinamis
        styles = [
            discord.ButtonStyle.primary,
            discord.ButtonStyle.success,
            discord.ButtonStyle.danger,
            discord.ButtonStyle.secondary,
        ]
        for i, p in enumerate(pilihan):
            btn = discord.ui.Button(
                label=p,
                style=styles[i % len(styles)],
                custom_id=f"trivia_{i}",
            )
            btn.callback = self._make_callback(p)
            self.add_item(btn)

    def _make_callback(self, pilihan_text: str):
        async def callback(interaction: discord.Interaction):
            if self.answered:
                return await interaction.response.send_message(
                    "Sudah ada yang menjawab!", ephemeral=True
                )

            self.answered = True
            self.stop()
            self._disable_all()

            if pilihan_text == self.jawaban:
                await self.db.add_balance(interaction.user.id, self.guild_id, self.hadiah)
                await interaction.response.edit_message(
                    embed=embed(
                        "✅ Benar!",
                        f"{interaction.user.mention} menjawab dengan benar!\n"
                        f"Jawaban: **{self.jawaban}**\n"
                        f"Dapat **{coins_fmt(self.hadiah)}** 🪙",
                        0x57F287,
                    ),
                    view=self,
                )
            else:
                await interaction.response.edit_message(
                    embed=embed(
                        "❌ Salah!",
                        f"{interaction.user.mention} menjawab **{pilihan_text}**.\n"
                        f"Jawaban yang benar: **{self.jawaban}**",
                        0xED4245,
                    ),
                    view=self,
                )

            self.unlock_fn()
        return callback

    def _disable_all(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def on_timeout(self):
        self._disable_all()
        self.unlock_fn()


async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))
