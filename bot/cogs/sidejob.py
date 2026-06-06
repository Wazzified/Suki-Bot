"""
Sidejob Cog - Fishing, Hunting, Mining
Sistem kerja sampingan lengkap dengan toko, inventory, dan jual hasil tangkapan.

Commands:
  /shop        - Lihat toko peralatan
  /buy         - Beli item dari toko
  /inventory   - Lihat inventory kamu
  /fish        - Pergi memancing (butuh Rod + Umpan)
  /hunt        - Pergi berburu  (butuh Rifle + Peluru)
  /mine        - Pergi menambang (butuh Pickaxe)
  /sell        - Jual item tertentu
  /sellall     - Jual semua tangkapan sekaligus
"""

import discord
from discord import app_commands
from discord.ext import commands
import random
from typing import List

from utils.database import Database
from utils.embeds import embed
from utils.helpers import coins_fmt


# ══════════════════════════════════════════════════════════════════════════════
#  TOKO — semua item yang bisa dibeli
# ══════════════════════════════════════════════════════════════════════════════
# type "equipment" → hanya bisa dimiliki 1, tidak habis pakai
# type "consumable" → bisa ditumpuk, habis setiap dipakai

SHOP: dict[str, dict] = {
    # ── Fishing ───────────────────────────────────────────────────────────────
    "basic_rod": {
        "name": "🎣 Basic Rod",
        "price": 500,
        "cat": "🎣 Fishing",
        "desc": "Diperlukan untuk memancing",
        "type": "equipment",
    },
    "pro_rod": {
        "name": "🎣 Pro Rod",
        "price": 2_500,
        "cat": "🎣 Fishing",
        "desc": "Kail pro — peluang ikan langka +20%",
        "type": "equipment",
    },
    "bait": {
        "name": "🪱 Umpan",
        "price": 50,
        "cat": "🎣 Fishing",
        "desc": "Habis setiap kali memancing",
        "type": "consumable",
    },
    "premium_bait": {
        "name": "✨ Umpan Premium",
        "price": 150,
        "cat": "🎣 Fishing",
        "desc": "Umpan terbaik — peluang ikan langka +20%",
        "type": "consumable",
    },

    # ── Hunting ───────────────────────────────────────────────────────────────
    "basic_rifle": {
        "name": "🔫 Basic Rifle",
        "price": 1_000,
        "cat": "🏹 Hunting",
        "desc": "Senapan berburu standar",
        "type": "equipment",
    },
    "pro_rifle": {
        "name": "🔫 Pro Rifle",
        "price": 4_000,
        "cat": "🏹 Hunting",
        "desc": "Senapan sniper — akurasi & hewan langka +20%",
        "type": "equipment",
    },
    "ammo": {
        "name": "🔫 Peluru",
        "price": 75,
        "cat": "🏹 Hunting",
        "desc": "Habis setiap kali berburu",
        "type": "consumable",
    },
    "premium_ammo": {
        "name": "💥 Peluru Premium",
        "price": 200,
        "cat": "🏹 Hunting",
        "desc": "Peluru tajam — peluang hewan langka +20%",
        "type": "consumable",
    },

    # ── Mining ────────────────────────────────────────────────────────────────
    "pickaxe": {
        "name": "⛏️ Pickaxe",
        "price": 800,
        "cat": "⛏️ Mining",
        "desc": "Diperlukan untuk menambang",
        "type": "equipment",
    },
    "pro_pickaxe": {
        "name": "⛏️ Pro Pickaxe",
        "price": 3_000,
        "cat": "⛏️ Mining",
        "desc": "Beliung baja — peluang bijih langka +20%",
        "type": "equipment",
    },
}


# ══════════════════════════════════════════════════════════════════════════════
#  TABEL TANGKAPAN
#  Format: (item_id, nama, emoji, harga_jual_min, harga_jual_max, berat, raritas)
# ══════════════════════════════════════════════════════════════════════════════

FISH_TABLE = [
    ("trash",           "Sampah / Sepatu Lama", "🥾",  0,      0,    8,  "Sampah"),
    ("fish_sardine",    "Ikan Sardine",          "🐟",  25,    70,   30,  "Common"),
    ("fish_common",     "Ikan Biasa",            "🐡",  40,    90,   25,  "Common"),
    ("fish_tropical",   "Ikan Tropis",           "🐠",  100,  220,   14,  "Uncommon"),
    ("fish_squid",      "Cumi-cumi",             "🦑",  150,  300,    9,  "Uncommon"),
    ("fish_octopus",    "Gurita",                "🐙",  250,  420,    6,  "Rare"),
    ("fish_shark",      "Hiu",                   "🦈",  450,  750,    4,  "Rare"),
    ("fish_legendary",  "Ikan Mas Emas ⭐",      "✨", 1500, 3000,    1,  "Legendary"),
]

ANIMAL_TABLE = [
    ("hunt_miss",        "Meleset — Tidak Kena", "💨",   0,     0,   10,  "Gagal"),
    ("hunt_rabbit",      "Kelinci",              "🐇",   60,  130,   30,  "Common"),
    ("hunt_bird",        "Burung Liar",          "🦅",   80,  160,   20,  "Common"),
    ("hunt_deer",        "Rusa",                 "🦌",  220,  400,   14,  "Uncommon"),
    ("hunt_boar",        "Babi Hutan",           "🐗",  280,  480,   10,  "Uncommon"),
    ("hunt_fox",         "Rubah",                "🦊",  350,  600,    6,  "Rare"),
    ("hunt_wolf",        "Serigala",             "🐺",  550,  900,    4,  "Rare"),
    ("hunt_bear",        "Beruang",              "🐻",  900, 1500,    2,  "Legendary"),
    ("hunt_legendary",   "Rusa Mistis 👑",       "🦌", 2500, 4500,    1,  "Legendary"),
]

ORE_TABLE = [
    ("ore_stone",    "Batu Biasa",  "🪨",    10,    35,   30,  "Common"),
    ("ore_coal",     "Batu Bara",   "⬛",    30,    70,   25,  "Common"),
    ("ore_iron",     "Besi",        "🔩",    75,   150,   18,  "Uncommon"),
    ("ore_gold",     "Emas",        "🟡",   200,   380,   12,  "Uncommon"),
    ("ore_emerald",  "Zamrud",      "💚",   450,   750,    7,  "Rare"),
    ("ore_ruby",     "Rubi",        "❤️",   650,  1100,    5,  "Rare"),
    ("ore_diamond",  "Berlian",     "💎",  1300,  2600,    2,  "Legendary"),
    ("ore_mythril",  "Mythril ⭐",  "🔮",  3500,  6000,    1,  "Legendary"),
]


# ══════════════════════════════════════════════════════════════════════════════
#  LOOKUP HELPERS
# ══════════════════════════════════════════════════════════════════════════════

# Daftar semua item yang bisa dijual (kecuali trash/miss)
SELL_PRICES: dict[str, dict] = {}
for _table in [FISH_TABLE, ANIMAL_TABLE, ORE_TABLE]:
    for _id, _name, _emoji, _mn, _mx, *_rest in _table:
        if _mn > 0:
            SELL_PRICES[_id] = {"name": f"{_emoji} {_name}", "min": _mn, "max": _mx}

RARITY_COLORS = {
    "Common":    0x95A5A6,
    "Uncommon":  0x2ECC71,
    "Rare":      0x3498DB,
    "Legendary": 0xF1C40F,
    "Sampah":    0x7F8C8D,
    "Gagal":     0xED4245,
}

RARITIES_ORDER = ["Common", "Uncommon", "Rare", "Legendary"]


def _weighted_choice(table: list, boost_rare: bool = False) -> tuple:
    """Pilih satu item dari tabel dengan sistem bobot. boost_rare menggandakan bobot Rare & Legendary."""
    weights = []
    for entry in table:
        rarity = entry[6]
        mult = 2 if (boost_rare and rarity in ("Rare", "Legendary")) else 1
        weights.append(entry[5] * mult)
    return random.choices(table, weights=weights, k=1)[0]


# ══════════════════════════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════════════════════════

class Sidejob(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: Database = bot.db
        self.BOT_COLOR = bot.config.get("BOT_COLOR", 0x5865F2)

    # ── Error handler (cooldown dll) ──────────────────────────────────────────
    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ):
        if isinstance(error, app_commands.CommandOnCooldown):
            secs = int(error.retry_after)
            await interaction.response.send_message(
                embed=embed(
                    "⏳ Cooldown!",
                    f"Tunggu **{secs} detik** sebelum bisa dipakai lagi.",
                    0xFEE75C,
                ),
                ephemeral=True,
            )
        else:
            raise error

    # ══════════════════════════════════════════════════════════════════════════
    #  /shop
    # ══════════════════════════════════════════════════════════════════════════
    @app_commands.command(name="shop", description="Lihat semua item yang bisa dibeli di toko")
    async def shop(self, interaction: discord.Interaction):
        e = discord.Embed(
            title="🛒 Toko Sidejob",
            description="Gunakan `/buy <item_id> [jumlah]` untuk membeli.",
            color=self.BOT_COLOR,
        )

        # Kelompokkan berdasarkan kategori
        cats: dict[str, list[str]] = {}
        for item_id, data in SHOP.items():
            cat = data["cat"]
            cats.setdefault(cat, [])
            icon = "🔧" if data["type"] == "equipment" else "📦"
            cats[cat].append(
                f"{icon} `{item_id}` — **{data['name']}** — {coins_fmt(data['price'])}\n"
                f"　　{data['desc']}"
            )

        for cat, lines in cats.items():
            e.add_field(name=cat, value="\n".join(lines), inline=False)

        e.set_footer(text="🔧 = Equipment (sekali beli) | 📦 = Consumable (habis pakai)")
        await interaction.response.send_message(embed=e)

    # ══════════════════════════════════════════════════════════════════════════
    #  /buy
    # ══════════════════════════════════════════════════════════════════════════
    @app_commands.command(name="buy", description="Beli item dari toko (gunakan item_id dari /shop)")
    async def buy(
        self,
        interaction: discord.Interaction,
        item: str,
        quantity: int = 1,
    ):
        # Autocomplete didaftarkan di bawah class
        item = item.lower().strip()

        if item not in SHOP:
            return await interaction.response.send_message(
                embed=embed("❌ Item Tidak Ditemukan", f"Cek `/shop` untuk daftar item yang tersedia.\nItem ID kamu: `{item}`", 0xED4245),
                ephemeral=True,
            )

        data = SHOP[item]

        if quantity < 1:
            return await interaction.response.send_message("❌ Jumlah minimal 1.", ephemeral=True)

        # Equipment hanya bisa dibeli 1 dan tidak bisa ditumpuk
        if data["type"] == "equipment":
            if quantity > 1:
                return await interaction.response.send_message(
                    "❌ Equipment hanya bisa dibeli 1x.", ephemeral=True
                )
            already_have = await self.db.has_item(interaction.user.id, interaction.guild_id, item)
            if already_have:
                return await interaction.response.send_message(
                    embed=embed("❌ Sudah Punya!", f"Kamu sudah punya **{data['name']}**!", 0xED4245),
                    ephemeral=True,
                )

        total_cost = data["price"] * quantity
        usr = await self.db.get_user(interaction.user.id, interaction.guild_id)
        balance = usr.get("balance", 0)

        if balance < total_cost:
            kekurangan = total_cost - balance
            return await interaction.response.send_message(
                embed=embed(
                    "❌ Koin Tidak Cukup!",
                    f"Butuh: **{coins_fmt(total_cost)}**\n"
                    f"Punya: **{coins_fmt(balance)}**\n"
                    f"Kurang: **{coins_fmt(kekurangan)}**",
                    0xED4245,
                ),
                ephemeral=True,
            )

        await self.db.set_user(
            interaction.user.id, interaction.guild_id,
            balance=balance - total_cost,
        )
        await self.db.add_item(interaction.user.id, interaction.guild_id, item, quantity)

        await interaction.response.send_message(
            embed=embed(
                "✅ Pembelian Berhasil!",
                f"Kamu membeli **{quantity}x {data['name']}**\n"
                f"Dibayar: **{coins_fmt(total_cost)}**\n"
                f"Sisa saldo: **{coins_fmt(balance - total_cost)}**",
                0x57F287,
            )
        )

    @buy.autocomplete("item")
    async def buy_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(
                name=f"{v['name']} — {coins_fmt(v['price'])} | {v['desc']}",
                value=k,
            )
            for k, v in SHOP.items()
            if current.lower() in k or current.lower() in v["name"].lower()
        ][:25]

    # ══════════════════════════════════════════════════════════════════════════
    #  /inventory
    # ══════════════════════════════════════════════════════════════════════════
    @app_commands.command(name="inventory", description="Lihat semua item di inventory kamu")
    async def inventory(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        inv = await self.db.get_inventory(interaction.user.id, interaction.guild_id)

        if not inv:
            return await interaction.followup.send(
                embed=embed(
                    "🎒 Inventory Kosong",
                    "Belum punya item apapun.\nCoba `/shop` → `/buy` → `/fish`, `/hunt`, atau `/mine`!",
                    0x95A5A6,
                ),
                ephemeral=True,
            )

        e = discord.Embed(title=f"🎒 Inventory {interaction.user.name}", color=self.BOT_COLOR)

        equip_lines = []
        catch_lines = []

        for row in inv:
            iid = row["item_id"]
            qty = row["quantity"]

            if iid in SHOP:
                equip_lines.append(f"{SHOP[iid]['name']} ×{qty}")
            elif iid in SELL_PRICES:
                d = SELL_PRICES[iid]
                equip_lines_or = f"{d['name']} ×{qty} — ~{coins_fmt(d['min'])}~{coins_fmt(d['max'])} each"
                catch_lines.append(equip_lines_or)

        if equip_lines:
            e.add_field(name="🔧 Peralatan", value="\n".join(equip_lines), inline=False)
        if catch_lines:
            e.add_field(
                name="💰 Tangkapan (bisa dijual)",
                value="\n".join(catch_lines[:20]),
                inline=False,
            )

        e.set_footer(text="Gunakan /sell <item> atau /sellall untuk menjual semua")
        await interaction.followup.send(embed=e, ephemeral=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  /fish
    # ══════════════════════════════════════════════════════════════════════════
    @app_commands.command(name="fish", description="Pergi memancing! Butuh: Rod + Umpan")
    @app_commands.checks.cooldown(1, 30.0, key=lambda i: (i.guild_id, i.user.id))
    async def fish(self, interaction: discord.Interaction):
        await interaction.response.defer()

        uid = interaction.user.id
        gid = interaction.guild_id

        # ── Cek alat ──────────────────────────────────────────────────────────
        has_pro_rod   = await self.db.has_item(uid, gid, "pro_rod")
        has_basic_rod = await self.db.has_item(uid, gid, "basic_rod")

        if not has_pro_rod and not has_basic_rod:
            return await interaction.followup.send(
                embed=embed(
                    "❌ Tidak Ada Alat!",
                    "Kamu butuh 🎣 **Rod** untuk memancing!\n"
                    "Beli di `/shop` → `basic_rod` (500 🪙) atau `pro_rod` (2,500 🪙)",
                    0xED4245,
                )
            )

        # ── Cek umpan ─────────────────────────────────────────────────────────
        has_premium_bait = await self.db.has_item(uid, gid, "premium_bait")
        has_bait         = await self.db.has_item(uid, gid, "bait")

        if not has_premium_bait and not has_bait:
            return await interaction.followup.send(
                embed=embed(
                    "❌ Tidak Ada Umpan!",
                    "Kamu butuh 🪱 **Umpan** untuk memancing!\n"
                    "Beli di `/shop` → `bait` (50 🪙) atau `premium_bait` (150 🪙)",
                    0xED4245,
                )
            )

        # ── Konsumsi umpan (premium duluan) ───────────────────────────────────
        boost = False
        if has_premium_bait:
            await self.db.remove_item(uid, gid, "premium_bait", 1)
            boost = True
        else:
            await self.db.remove_item(uid, gid, "bait", 1)

        if has_pro_rod:
            boost = True

        rod_label  = "🎣 Pro Rod"   if has_pro_rod   else "🎣 Basic Rod"
        bait_label = "✨ Umpan Premium" if has_premium_bait else "🪱 Umpan Biasa"

        # ── Roll tangkapan ────────────────────────────────────────────────────
        catch = _weighted_choice(FISH_TABLE, boost_rare=boost)
        item_id, name, emoji, mn, mx, _, rarity = catch

        if item_id == "trash":
            return await interaction.followup.send(
                embed=embed(
                    "🥾 Dapat Sampah!",
                    f"Kamu memancing dengan **{rod_label}** + **{bait_label}**...\n\n"
                    "Dapat **Sampah / Sepatu Lama** 🥾\nLebih beruntung lain kali!",
                    0x7F8C8D,
                )
            )

        sell_val = random.randint(mn, mx)
        await self.db.add_item(uid, gid, item_id, 1)

        color = RARITY_COLORS.get(rarity, 0x95A5A6)
        e = discord.Embed(color=color)
        e.set_author(name=f"🎣 {interaction.user.name} memancing...")
        e.add_field(name="✅ Tangkapan!",  value=f"{emoji} **{name}**", inline=True)
        e.add_field(name="⭐ Raritas",    value=f"**{rarity}**",        inline=True)
        e.add_field(name="💰 Nilai Jual", value=f"~{coins_fmt(sell_val)}", inline=True)
        e.add_field(name="🔧 Alat",       value=f"{rod_label} + {bait_label}", inline=False)
        e.set_footer(text="Jual dengan /sell <item_id> atau /sellall ⏱️ Cooldown: 30 detik")
        await interaction.followup.send(embed=e)

    # ══════════════════════════════════════════════════════════════════════════
    #  /hunt
    # ══════════════════════════════════════════════════════════════════════════
    @app_commands.command(name="hunt", description="Pergi berburu! Butuh: Rifle + Peluru")
    @app_commands.checks.cooldown(1, 45.0, key=lambda i: (i.guild_id, i.user.id))
    async def hunt(self, interaction: discord.Interaction):
        await interaction.response.defer()

        uid = interaction.user.id
        gid = interaction.guild_id

        # ── Cek senjata ───────────────────────────────────────────────────────
        has_pro_rifle   = await self.db.has_item(uid, gid, "pro_rifle")
        has_basic_rifle = await self.db.has_item(uid, gid, "basic_rifle")

        if not has_pro_rifle and not has_basic_rifle:
            return await interaction.followup.send(
                embed=embed(
                    "❌ Tidak Ada Senjata!",
                    "Kamu butuh 🔫 **Rifle** untuk berburu!\n"
                    "Beli di `/shop` → `basic_rifle` (1,000 🪙) atau `pro_rifle` (4,000 🪙)",
                    0xED4245,
                )
            )

        # ── Cek peluru ────────────────────────────────────────────────────────
        has_premium_ammo = await self.db.has_item(uid, gid, "premium_ammo")
        has_ammo         = await self.db.has_item(uid, gid, "ammo")

        if not has_premium_ammo and not has_ammo:
            return await interaction.followup.send(
                embed=embed(
                    "❌ Tidak Ada Peluru!",
                    "Kamu butuh 🔫 **Peluru** untuk berburu!\n"
                    "Beli di `/shop` → `ammo` (75 🪙) atau `premium_ammo` (200 🪙)",
                    0xED4245,
                )
            )

        # ── Konsumsi peluru (premium duluan) ──────────────────────────────────
        boost = False
        if has_premium_ammo:
            await self.db.remove_item(uid, gid, "premium_ammo", 1)
            boost = True
        else:
            await self.db.remove_item(uid, gid, "ammo", 1)

        if has_pro_rifle:
            boost = True

        rifle_label = "🔫 Pro Rifle"      if has_pro_rifle   else "🔫 Basic Rifle"
        ammo_label  = "💥 Peluru Premium" if has_premium_ammo else "🔫 Peluru Biasa"

        # ── Roll buruan ───────────────────────────────────────────────────────
        catch = _weighted_choice(ANIMAL_TABLE, boost_rare=boost)
        item_id, name, emoji, mn, mx, _, rarity = catch

        if item_id == "hunt_miss":
            return await interaction.followup.send(
                embed=embed(
                    "💨 Meleset!",
                    f"Kamu berburu dengan **{rifle_label}** + **{ammo_label}**...\n\n"
                    "Tembakan **meleset**! Tidak dapat apa-apa. Peluru sudah terpakai.",
                    0xED4245,
                )
            )

        sell_val = random.randint(mn, mx)
        await self.db.add_item(uid, gid, item_id, 1)

        color = RARITY_COLORS.get(rarity, 0x95A5A6)
        e = discord.Embed(color=color)
        e.set_author(name=f"🏹 {interaction.user.name} berburu...")
        e.add_field(name="✅ Hasil Buruan!", value=f"{emoji} **{name}**",     inline=True)
        e.add_field(name="⭐ Raritas",       value=f"**{rarity}**",            inline=True)
        e.add_field(name="💰 Nilai Jual",    value=f"~{coins_fmt(sell_val)}", inline=True)
        e.add_field(name="🔧 Alat",          value=f"{rifle_label} + {ammo_label}", inline=False)
        e.set_footer(text="Jual dengan /sell <item_id> atau /sellall ⏱️ Cooldown: 45 detik")
        await interaction.followup.send(embed=e)

    # ══════════════════════════════════════════════════════════════════════════
    #  /mine
    # ══════════════════════════════════════════════════════════════════════════
    @app_commands.command(name="mine", description="Pergi menambang! Butuh: Pickaxe. Dapat 1–3 bijih per tambang")
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: (i.guild_id, i.user.id))
    async def mine(self, interaction: discord.Interaction):
        await interaction.response.defer()

        uid = interaction.user.id
        gid = interaction.guild_id

        # ── Cek pickaxe ───────────────────────────────────────────────────────
        has_pro_pickaxe   = await self.db.has_item(uid, gid, "pro_pickaxe")
        has_basic_pickaxe = await self.db.has_item(uid, gid, "pickaxe")

        if not has_pro_pickaxe and not has_basic_pickaxe:
            return await interaction.followup.send(
                embed=embed(
                    "❌ Tidak Ada Pickaxe!",
                    "Kamu butuh ⛏️ **Pickaxe** untuk menambang!\n"
                    "Beli di `/shop` → `pickaxe` (800 🪙) atau `pro_pickaxe` (3,000 🪙)",
                    0xED4245,
                )
            )

        boost = has_pro_pickaxe
        pickaxe_label = "⛏️ Pro Pickaxe" if has_pro_pickaxe else "⛏️ Basic Pickaxe"

        # ── Roll 1–3 bijih ────────────────────────────────────────────────────
        num_ores = random.randint(1, 3)
        catches  = [_weighted_choice(ORE_TABLE, boost_rare=boost) for _ in range(num_ores)]

        lines = []
        for catch in catches:
            item_id, name, emoji, mn, mx, _, rarity = catch
            val = random.randint(mn, mx)
            await self.db.add_item(uid, gid, item_id, 1)
            lines.append(f"{emoji} **{name}** [{rarity}] — ~{coins_fmt(val)}")

        # Warna embed = raritas terbaik yang didapat
        best_rarity = max(
            (c[6] for c in catches if c[6] in RARITIES_ORDER),
            key=lambda r: RARITIES_ORDER.index(r),
            default="Common",
        )
        color = RARITY_COLORS.get(best_rarity, 0x95A5A6)

        e = discord.Embed(
            title=f"⛏️ {interaction.user.name} menambang...",
            description="\n".join(lines),
            color=color,
        )
        e.add_field(name="🔧 Alat",  value=pickaxe_label,       inline=True)
        e.add_field(name="📦 Dapat", value=f"{num_ores} bijih", inline=True)
        e.set_footer(text="Jual dengan /sell <item_id> atau /sellall ⏱️ Cooldown: 60 detik")
        await interaction.followup.send(embed=e)

    # ══════════════════════════════════════════════════════════════════════════
    #  /sell
    # ══════════════════════════════════════════════════════════════════════════
    @app_commands.command(name="sell", description="Jual item tangkapan tertentu dari inventory")
    async def sell(
        self,
        interaction: discord.Interaction,
        item: str,
        quantity: int = 1,
    ):
        item = item.lower().strip()

        if item not in SELL_PRICES:
            return await interaction.response.send_message(
                embed=embed(
                    "❌ Tidak Bisa Dijual",
                    "Item tidak ditemukan atau tidak bisa dijual.\nCek `/inventory` untuk melihat item kamu.",
                    0xED4245,
                ),
                ephemeral=True,
            )

        if quantity < 1:
            return await interaction.response.send_message("❌ Jumlah minimal 1.", ephemeral=True)

        await interaction.response.defer()

        removed = await self.db.remove_item(interaction.user.id, interaction.guild_id, item, quantity)
        if not removed:
            return await interaction.followup.send(
                embed=embed(
                    "❌ Tidak Cukup!",
                    f"Kamu tidak punya **{quantity}x** item tersebut di inventory!",
                    0xED4245,
                )
            )

        data  = SELL_PRICES[item]
        total = sum(random.randint(data["min"], data["max"]) for _ in range(quantity))
        await self.db.add_balance(interaction.user.id, interaction.guild_id, total)

        await interaction.followup.send(
            embed=embed(
                "💰 Berhasil Dijual!",
                f"Terjual **{quantity}x {data['name']}**\n\nTotal: **{coins_fmt(total)}** 🪙",
                0x57F287,
            )
        )

    @sell.autocomplete("item")
    async def sell_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        # Tampilkan item yang ada di inventory user
        try:
            inv = await self.db.get_inventory(interaction.user.id, interaction.guild_id)
            choices = []
            for row in inv:
                iid = row["item_id"]
                qty = row["quantity"]
                if iid in SELL_PRICES:
                    d = SELL_PRICES[iid]
                    if current.lower() in iid or current.lower() in d["name"].lower():
                        choices.append(
                            app_commands.Choice(
                                name=f"{d['name']} ×{qty} — {coins_fmt(d['min'])}~{coins_fmt(d['max'])} each",
                                value=iid,
                            )
                        )
            return choices[:25]
        except Exception:
            return []

    # ══════════════════════════════════════════════════════════════════════════
    #  /sellall
    # ══════════════════════════════════════════════════════════════════════════
    @app_commands.command(name="sellall", description="Jual semua tangkapan di inventory sekaligus")
    async def sellall(self, interaction: discord.Interaction):
        await interaction.response.defer()

        uid = interaction.user.id
        gid = interaction.guild_id

        inv = await self.db.get_inventory(uid, gid)
        sellable = [(r["item_id"], r["quantity"]) for r in inv if r["item_id"] in SELL_PRICES]

        if not sellable:
            return await interaction.followup.send(
                embed=embed(
                    "❌ Tidak Ada yang Dijual",
                    "Tidak ada tangkapan di inventory kamu!\nCoba `/fish`, `/hunt`, atau `/mine` dulu.",
                    0x95A5A6,
                )
            )

        total_earned = 0
        lines = []

        for item_id, qty in sellable:
            data        = SELL_PRICES[item_id]
            item_total  = sum(random.randint(data["min"], data["max"]) for _ in range(qty))
            await self.db.remove_item(uid, gid, item_id, qty)
            total_earned += item_total
            lines.append(f"{data['name']} ×{qty} → **{coins_fmt(item_total)}**")

        await self.db.add_balance(uid, gid, total_earned)

        e = discord.Embed(
            title="💰 Semua Tangkapan Terjual!",
            description="\n".join(lines[:20]),
            color=0x57F287,
        )
        if len(lines) > 20:
            e.description += f"\n...dan {len(lines) - 20} item lainnya"

        e.add_field(
            name="🏦 Total Pendapatan",
            value=f"**{coins_fmt(total_earned)}** 🪙 masuk ke wallet kamu!",
            inline=False,
        )
        await interaction.followup.send(embed=e)


# ══════════════════════════════════════════════════════════════════════════════
async def setup(bot: commands.Bot):
    await bot.add_cog(Sidejob(bot))
