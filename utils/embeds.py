"""
Embed utilities - Quick embed builders and helpers
"""

import discord

BOT_COLOR = 0x5865F2  # Discord blurple


def embed(
    title: str = "",
    desc: str = "",
    color: int = BOT_COLOR,
    footer: str = "",
) -> discord.Embed:
    """Create a quick embed with title, description, color, and optional footer."""
    e = discord.Embed(title=title, description=desc, color=color)
    if footer:
        e.set_footer(text=footer)
    return e
