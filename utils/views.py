"""
Discord Views, Buttons, Select Menus - UI Components
"""

import discord
from typing import Optional


class YesNoView(discord.ui.View):
    """Simple Yes / No confirmation view."""

    def __init__(self, *, timeout: float = 30.0):
        super().__init__(timeout=timeout)
        self.result: Optional[bool] = None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success, emoji="✅")
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = True
        self._disable_all()
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger, emoji="❌")
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = False
        self._disable_all()
        await interaction.response.edit_message(view=self)
        self.stop()

    def _disable_all(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def on_timeout(self):
        self._disable_all()


class ConfirmView(discord.ui.View):
    """Confirmation view that only responds to the original author."""

    def __init__(self, author_id: int, *, timeout: float = 30.0):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.result: Optional[bool] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Only the command user can confirm this.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = True
        self._disable_all()
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = False
        self._disable_all()
        await interaction.response.edit_message(view=self)
        self.stop()

    def _disable_all(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def on_timeout(self):
        self._disable_all()
