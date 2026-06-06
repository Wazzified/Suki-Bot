import logging
from discord.ext import commands

log = logging.getLogger("ApexBot")

async def load_cogs(bot: commands.Bot):
    cogs = [
        "economy", "moderation", "profile", "leaderboard",
        "reminders", "admin", "sidejob", "casino",
        "autorole", "transfer", "games", "chatbot",
    ]
    for cog in cogs:
        try:
            await bot.load_extension(f"bot.cogs.{cog}")
            log.info(f"✅ Loaded cog: {cog}")
        except Exception as e:
            log.error(f"❌ Failed to load cog {cog}: {e}")
