"""
Chatbot AI Cog - Bot ngobrol pakai Claude AI
Commands:
  /chat      - Ngobrol dengan AI
  /chatsetup - Set channel khusus chatbot (auto reply tanpa command)
  /chatreset - Reset riwayat percakapan
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import aiohttp
import json
import logging

from utils.embeds import embed

log = logging.getLogger("ApexBot")

# System prompt untuk bot
SYSTEM_PROMPT = """Kamu adalah Suki Bot, asisten AI Discord yang ramah, lucu, dan helpful.
Kamu dibuat oleh developer menggunakan Python dan discord.py dengan AI dari Groq.
Kamu bisa menjawab pertanyaan apapun — mulai dari sains, teknologi, sejarah, hiburan, tips, hingga ngobrol santai.
Jawab dalam Bahasa Indonesia yang santai, friendly, dan sedikit bercanda.
Jangan terlalu panjang, maksimal 3-4 kalimat per jawaban.
Kalau tidak tahu jawabannya, jujur saja bilang tidak tahu."""

# Model Groq yang tersedia gratis:
# - llama-3.3-70b-versatile  (paling pintar, recommended)
# - llama3-8b-8192           (lebih cepat, lebih ringan)
# - mixtral-8x7b-32768       (alternatif)
GROQ_MODEL = "llama-3.3-70b-versatile"


class Chatbot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = bot.db
        self.BOT_COLOR = bot.config.get("BOT_COLOR", 0x57F287)

        # Riwayat per user: {user_id: [{"role": "user/assistant", "content": "..."}]}
        self._history: dict[int, list] = {}

        # Channel khusus chatbot per guild: {guild_id: channel_id}
        self._chat_channels: dict[int, int] = {}

    async def cog_load(self):
        """Load chat channel configs dari DB."""
        try:
            configs = await self.db.get_all_chat_channels()
            for cfg in configs:
                self._chat_channels[cfg["guild_id"]] = cfg["channel_id"]
        except Exception as e:
            log.warning(f"Chatbot: failed to load configs: {e}")

    async def _ask_claude(self, user_id: int, pesan: str) -> str:
        """Kirim pesan ke Groq API (GRATIS) dan return balasan."""
        import os
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            return "GROQ_API_KEY belum diset di file .env! Daftar gratis di console.groq.com"

        if user_id not in self._history:
            self._history[user_id] = []

        self._history[user_id].append({"role": "user", "content": pesan})

        if len(self._history[user_id]) > 10:
            self._history[user_id] = self._history[user_id][-10:]

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self._history[user_id]

        payload = {
            "model": GROQ_MODEL,
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.8,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {groq_key}",
                        "Accept-Encoding": "gzip, deflate",  # FIX: hindari Brotli encoding
                    },
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15),  # FIX: 15 detik cukup, tidak perlu 30
                ) as resp:
                    data = await resp.json()

                    if resp.status == 401:
                        return "GROQ_API_KEY salah atau tidak valid! Cek file .env kamu."
                    if resp.status == 429:
                        return "Terlalu banyak request ke AI! Tunggu sebentar ya 😅"
                    if resp.status != 200:
                        log.error(f"Groq API error {resp.status}: {data}")
                        return "Maaf, aku lagi error nih! Coba lagi nanti ya 😅"

                    # FIX: validasi response structure sebelum akses
                    choices = data.get("choices", [])
                    if not choices:
                        log.error(f"Groq empty response: {data}")
                        return "Maaf, AI tidak memberikan respon. Coba lagi ya!"

                    reply = choices[0]["message"]["content"].strip()
                    if not reply:
                        return "Maaf, AI memberikan respon kosong. Coba lagi ya!"

                    self._history[user_id].append({"role": "assistant", "content": reply})
                    return reply

        except aiohttp.ClientConnectorError:
            return "Tidak bisa terhubung ke Groq API. Cek koneksi internet bot ya!"
        except asyncio.TimeoutError:
            # FIX: hapus pesan user dari history kalau timeout agar tidak spam
            if self._history.get(user_id):
                self._history[user_id].pop()
            return "Maaf, AI terlalu lama merespon (>15 detik)! Coba lagi ya 😅"
        except Exception as e:
            log.error(f"Chatbot error: {e}")
            return "Maaf, aku lagi gangguan nih! Coba lagi nanti 🙏"

    # ── /chat ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="chat", description="Ngobrol dengan Suki Bot AI!")
    async def chat(self, interaction: discord.Interaction, pesan: str):
        await interaction.response.defer()

        reply = await self._ask_claude(interaction.user.id, pesan)

        e = discord.Embed(color=self.BOT_COLOR)
        e.add_field(name=f"💬 {interaction.user.name}", value=pesan,  inline=False)
        e.add_field(name="🤖 Suki Bot",                value=reply[:1024], inline=False)
        e.set_thumbnail(url=self.bot.user.display_avatar.url)

        await interaction.followup.send(embed=e)

    # ── /chatsetup ────────────────────────────────────────────────────────────
    @app_commands.command(name="chatsetup", description="Set channel khusus chatbot — bot auto reply di channel ini")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def chatsetup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        await self.db.set_chat_channel(interaction.guild_id, channel.id)
        self._chat_channels[interaction.guild_id] = channel.id

        await interaction.followup.send(
            embed=embed(
                "✅ Chat Channel Diset!",
                f"Bot akan auto reply semua pesan di {channel.mention}.\n"
                "Tidak perlu pakai command `/chat` lagi di channel tersebut!",
                0x57F287,
            ),
            ephemeral=True,
        )

    # ── /chatreset ────────────────────────────────────────────────────────────
    @app_commands.command(name="chatreset", description="Reset riwayat percakapan kamu dengan bot")
    async def chatreset(self, interaction: discord.Interaction):
        self._history.pop(interaction.user.id, None)
        await interaction.response.send_message(
            embed=embed("🔄 Riwayat Direset!", "Percakapan kamu dengan bot sudah dihapus. Mulai fresh!", 0x57F287),
            ephemeral=True,
        )

    # ── EVENT: auto reply di chat channel ─────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return

        chat_ch = self._chat_channels.get(message.guild.id)
        if not chat_ch or message.channel.id != chat_ch:
            return
        if message.content.startswith("/"):
            return
        if not message.content.strip():
            return

        # FIX: bungkus dengan try/except agar tidak stuck "thinking" jika error
        try:
            async with message.channel.typing():
                reply = await self._ask_claude(message.author.id, message.content)
            await message.reply(reply)
        except discord.Forbidden:
            pass  # Bot tidak bisa reply di channel ini
        except Exception as err:
            log.error(f"Chatbot on_message error: {err}")
            try:
                await message.reply("Maaf, aku lagi error nih! Coba lagi nanti 😅")
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Chatbot(bot))
