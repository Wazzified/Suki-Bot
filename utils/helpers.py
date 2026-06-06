"""
Helper functions - XP calculations, formatting, image generation, etc.
"""

import io
import os
import re
from datetime import timedelta
from typing import Optional

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PILLOW_OK = True
except ImportError:
    PILLOW_OK = False


# ─── XP & Leveling ────────────────────────────────────────────────────────────
def xp_for_level(lvl: int) -> int:
    """Calculate total XP required to reach a level."""
    return int(100 * (lvl ** 1.5))


def level_from_xp(xp: int) -> int:
    """Calculate level from total XP (with level cap guard)."""
    lvl = 0
    while lvl < 1000 and xp >= xp_for_level(lvl + 1):
        lvl += 1
    return lvl


# ─── Formatting ───────────────────────────────────────────────────────────────
def coins_fmt(n: int) -> str:
    """Format coins for display."""
    return f"🪙 {n:,}"


def parse_duration(s: str) -> Optional[timedelta]:
    """
    Parse duration string like '10m', '2h', '1d', '1d2h30m15s'.
    Returns None if invalid.
    """
    m = re.fullmatch(r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", s.strip().lower())
    if not m or not any(m.groups()):
        return None
    d, h, mi, sec = (int(g or 0) for g in m.groups())
    td = timedelta(days=d, hours=h, minutes=mi, seconds=sec)
    return td if td.total_seconds() > 0 else None


# ─── Pillow Image Generators ──────────────────────────────────────────────────

def _draw_rounded_rect(draw, xy, radius, fill):
    """Helper to draw rounded rectangles with Pillow."""
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    draw.ellipse([x1, y1, x1 + radius * 2, y1 + radius * 2], fill=fill)
    draw.ellipse([x2 - radius * 2, y1, x2, y1 + radius * 2], fill=fill)
    draw.ellipse([x1, y2 - radius * 2, x1 + radius * 2, y2], fill=fill)
    draw.ellipse([x2 - radius * 2, y2 - radius * 2, x2, y2], fill=fill)


def _load_font(size: int, bold: bool = False):
    """Load cross-platform TrueType font with fallback to default."""
    paths = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'Bold' if bold else ''}.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def generate_rank_card(
    avatar_bytes: bytes,
    username: str,
    level: int,
    current_xp: int,
    needed_xp: int,
    rank: int,
) -> bytes:
    """Generate a rank card PNG using Pillow. Runs in executor."""
    if not PILLOW_OK:
        raise ImportError("Pillow is required for image generation")

    # Canvas
    W, H = 800, 200
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bg   = Image.new("RGBA", (W, H))
    d    = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / H
        r = int(25 + t * 18)
        g = int(10 + t * 8)
        b = int(55 + t * 35)
        d.line([(0, y), (W, y)], fill=(r, g, b, 255))
    card.paste(bg)

    draw = ImageDraw.Draw(card)

    # Avatar circle
    try:
        av_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((148, 148))
        mask   = Image.new("L", (148, 148), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 148, 148), fill=255)
        av_img.putalpha(mask)
        # Border ring
        draw.ellipse((24, 26, 176, 174), fill=(88, 101, 242))
        card.paste(av_img, (26, 28), av_img)
    except Exception:
        draw.ellipse((26, 28, 174, 172), fill=(88, 101, 242))

    # Fonts
    f_big  = _load_font(30, bold=True)
    f_med  = _load_font(20)
    f_sm   = _load_font(15)

    # Username
    draw.text((200, 35),  username[:24],         font=f_big, fill=(255, 255, 255))
    draw.text((200, 75),  f"Level {level}",      font=f_med, fill=(163, 148, 220))
    draw.text((680, 35),  f"#{rank}",            font=f_med, fill=(253, 203, 88))

    # XP bar background
    bx, by, bw, bh = 200, 118, 570, 20
    _draw_rounded_rect(draw, (bx, by, bx + bw, by + bh), 10, (55, 35, 90))

    # XP bar fill
    pct    = min(current_xp / max(needed_xp, 1), 1.0)
    filled = int(bw * pct)
    if filled > 0:
        _draw_rounded_rect(draw, (bx, by, bx + filled, by + bh), 10, (88, 101, 242))

    # XP text
    draw.text((200, 145), f"{current_xp:,} / {needed_xp:,} XP", font=f_sm, fill=(180, 165, 230))

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def generate_welcome_card(
    avatar_bytes: bytes,
    username: str,
    guild_name: str,
    member_count: int,
) -> bytes:
    """Generate a welcome card PNG using Pillow. Runs in executor."""
    if not PILLOW_OK:
        raise ImportError("Pillow is required for image generation")

    W, H = 900, 300
    img  = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(img)

    # Gradient background
    for y in range(H):
        t = y / H
        r = int(18 + t * 12)
        g = int(8  + t * 5)
        b = int(48 + t * 40)
        draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

    # Decorative circles
    draw.ellipse((-60, -60, 220, 220), outline=(88, 101, 242, 60), width=4)
    draw.ellipse((680, 140, 980, 420), outline=(88, 101, 242, 40), width=4)

    # Avatar
    try:
        av = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((160, 160))
        m  = Image.new("L", (160, 160), 0)
        ImageDraw.Draw(m).ellipse((0, 0, 160, 160), fill=255)
        av.putalpha(m)
        draw.ellipse((55, 65, 235, 235), fill=(88, 101, 242))
        img.paste(av, (60, 70), av)
    except Exception:
        draw.ellipse((60, 70, 230, 230), fill=(88, 101, 242))

    f_wel = _load_font(40, bold=True)
    f_nm  = _load_font(32, bold=True)
    f_sub = _load_font(20)

    draw.text((265, 65),  "WELCOME!",                          font=f_wel, fill=(253, 203, 88))
    draw.text((265, 120), username[:26],                        font=f_nm,  fill=(255, 255, 255))
    draw.text((265, 168), f"to {guild_name}",                  font=f_sub, fill=(163, 148, 220))
    draw.text((265, 200), f"You are member #{member_count:,}", font=f_sub, fill=(130, 120, 180))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()
