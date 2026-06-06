"""
Economy Cog - balance, daily, work, deposit, withdraw
"""

import discord
from discord import app_commands
from discord.ext import commands
import random
from datetime import datetime, timezone, timedelta

from utils.database import Database
from utils.embeds import embed
from utils.helpers import coins_fmt


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: Database = bot.db

        self.DAILY_COINS  = bot.config["DAILY_COINS"]
        self.WORK_COOLDOWN  = bot.config["WORK_COOLDOWN"]
        self.DAILY_COOLDOWN = bot.config["DAILY_COOLDOWN"]
        self.WORK_JOBS    = bot.config["WORK_JOBS"]
        self.BOT_COLOR    = bot.config["BOT_COLOR"]

    # ─── BALANCE ─────────────────────────────────────────────────────────────
    @app_commands.command(name="balance", description="Check your (or another member's) coin balance")  # FIX: added description
    async def balance(self, interaction: discord.Interaction, member: discord.Member = None):
        await interaction.response.defer()

        m = member or interaction.user
        usr = await self.db.get_user(m.id, interaction.guild_id)

        e = discord.Embed(title=f"💰 {m.name}'s Balance", color=self.BOT_COLOR)
        e.set_thumbnail(url=m.display_avatar.url)
        e.add_field(name="Wallet", value=coins_fmt(usr.get("balance", 0)))
        e.add_field(name="Bank",   value=coins_fmt(usr.get("bank",    0)))
        e.add_field(
            name="Total",
            value=coins_fmt(usr.get("balance", 0) + usr.get("bank", 0)),
        )
        await interaction.followup.send(embed=e)

    # ─── DAILY ───────────────────────────────────────────────────────────────
    @app_commands.command(name="daily", description="Claim your daily coin reward")  # FIX: added description
    async def daily(self, interaction: discord.Interaction):
        await interaction.response.defer()

        usr = await self.db.get_user(interaction.user.id, interaction.guild_id)
        now = datetime.now(timezone.utc)

        if usr.get("last_daily"):
            last = datetime.fromisoformat(usr["last_daily"])
            diff = (now - last).total_seconds()

            if diff < self.DAILY_COOLDOWN:
                remaining = timedelta(seconds=int(self.DAILY_COOLDOWN - diff))
                return await interaction.followup.send(
                    embed=embed("⏳ Already claimed!", f"Come back in **{remaining}**.", 0xFEE75C)
                )

        await self.db.add_balance(interaction.user.id, interaction.guild_id, self.DAILY_COINS)
        await self.db.set_user(
            interaction.user.id, interaction.guild_id,
            last_daily=now.isoformat()
        )

        await interaction.followup.send(
            embed=embed(
                "🎁 Daily Reward!",
                f"You received **{coins_fmt(self.DAILY_COINS)}**!",
                0x57F287,
            )
        )

    # ─── WORK ────────────────────────────────────────────────────────────────
    @app_commands.command(name="work", description="Work to earn coins (1 hour cooldown)")  # FIX: added description
    async def work(self, interaction: discord.Interaction):
        await interaction.response.defer()

        usr = await self.db.get_user(interaction.user.id, interaction.guild_id)
        now = datetime.now(timezone.utc)

        if usr.get("last_work"):
            last = datetime.fromisoformat(usr["last_work"])
            diff = (now - last).total_seconds()

            if diff < self.WORK_COOLDOWN:
                rem = timedelta(seconds=int(self.WORK_COOLDOWN - diff))
                return await interaction.followup.send(
                    embed=embed("⏳ You're tired!", f"Work again in **{rem}**.", 0xFEE75C)
                )

        job, (mn, mx) = random.choice(self.WORK_JOBS)
        earned = random.randint(mn, mx)

        await self.db.add_balance(interaction.user.id, interaction.guild_id, earned)
        await self.db.set_user(
            interaction.user.id, interaction.guild_id,
            last_work=now.isoformat()
        )

        await interaction.followup.send(
            embed=embed(
                "💼 Work Complete!",
                f"You worked as **{job}** and earned **{coins_fmt(earned)}**!",
                0x57F287,
            )
        )

    # ─── DEPOSIT ─────────────────────────────────────────────────────────────
    @app_commands.command(name="deposit", description="Deposit coins from wallet into bank (use 'all' for everything)")  # FIX: added description
    async def deposit(self, interaction: discord.Interaction, amount: str):
        await interaction.response.defer()

        usr = await self.db.get_user(interaction.user.id, interaction.guild_id)
        bal = usr.get("balance", 0)

        if amount.lower() == "all":
            amt = bal
        else:
            try:
                amt = int(amount)
            except ValueError:
                return await interaction.followup.send("❌ Invalid amount. Use a number or `all`.")

        if amt <= 0:
            return await interaction.followup.send("❌ Amount must be positive.")
        if amt > bal:
            return await interaction.followup.send(
                f"❌ You only have {coins_fmt(bal)} in your wallet."
            )

        await self.db.set_user(
            interaction.user.id,
            interaction.guild_id,
            balance=bal - amt,
            bank=usr.get("bank", 0) + amt,
        )

        await interaction.followup.send(
            embed=embed("🏦 Deposited!", f"Deposited **{coins_fmt(amt)}** into your bank!", 0x57F287)
        )

    # ─── WITHDRAW ────────────────────────────────────────────────────────────
    @app_commands.command(name="withdraw", description="Withdraw coins from bank to wallet (use 'all' for everything)")  # FIX: added description
    async def withdraw(self, interaction: discord.Interaction, amount: str):
        await interaction.response.defer()

        usr = await self.db.get_user(interaction.user.id, interaction.guild_id)
        bank = usr.get("bank", 0)

        if amount.lower() == "all":
            amt = bank
        else:
            try:
                amt = int(amount)
            except ValueError:
                return await interaction.followup.send("❌ Invalid amount. Use a number or `all`.")

        if amt <= 0:
            return await interaction.followup.send("❌ Amount must be positive.")
        if amt > bank:
            return await interaction.followup.send(
                f"❌ You only have {coins_fmt(bank)} in your bank."
            )

        await self.db.set_user(
            interaction.user.id,
            interaction.guild_id,
            balance=usr.get("balance", 0) + amt,
            bank=bank - amt,
        )

        await interaction.followup.send(
            embed=embed("🏦 Withdrawn!", f"Withdrew **{coins_fmt(amt)}** to your wallet!", 0x57F287)
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))
