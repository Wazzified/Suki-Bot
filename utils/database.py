"""
Database Manager - aiosqlite async wrapper
Handles all database operations for Apex Bot
"""

import aiosqlite
import logging
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger("ApexBot")


class Database:
    def __init__(self, db_path: str):
        self.path = db_path
        self.db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        self.db = await aiosqlite.connect(self.path)
        self.db.row_factory = aiosqlite.Row
        await self._init_tables()
        log.info("✅ Database connected: %s", self.path)

    async def _init_tables(self):
        # One executescript call for atomic table creation
        await self.db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id      INTEGER NOT NULL,
                guild_id     INTEGER NOT NULL,
                balance      INTEGER DEFAULT 0,
                bank         INTEGER DEFAULT 0,
                xp           INTEGER DEFAULT 0,
                level        INTEGER DEFAULT 0,
                last_daily   TEXT    DEFAULT NULL,
                last_work    TEXT    DEFAULT NULL,
                last_xp_ts   REAL    DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            );

            CREATE TABLE IF NOT EXISTS inventory (
                user_id  INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                item_id  TEXT    NOT NULL,
                quantity INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, guild_id, item_id)
            );

            CREATE TABLE IF NOT EXISTS warnings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                guild_id    INTEGER NOT NULL,
                mod_id      INTEGER NOT NULL,
                reason      TEXT    NOT NULL,
                created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id         INTEGER PRIMARY KEY,
                welcome_channel  INTEGER DEFAULT NULL,
                goodbye_channel  INTEGER DEFAULT NULL,
                log_channel      INTEGER DEFAULT NULL,
                antilink_enabled INTEGER DEFAULT 0,
                antispam_enabled INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                content    TEXT    NOT NULL,
                remind_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_channels (
                guild_id   INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS antiraid (
                guild_id    INTEGER PRIMARY KEY,
                enabled     INTEGER DEFAULT 0,
                threshold   INTEGER DEFAULT 5,
                interval    INTEGER DEFAULT 10,
                action      TEXT    DEFAULT 'kick',
                log_channel INTEGER DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS autoroles (
                guild_id   INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                role_id    INTEGER NOT NULL,
                PRIMARY KEY (guild_id, role_id)
            );

            CREATE TABLE IF NOT EXISTS suggestions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id   INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                content    TEXT    NOT NULL,
                status     TEXT    DEFAULT 'pending',
                message_id INTEGER DEFAULT NULL,
                channel_id INTEGER DEFAULT NULL,
                created_at TEXT    DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await self.db.commit()

    # ── User helpers ──────────────────────────────────────────────────────────
    async def get_user(self, user_id: int, guild_id: int) -> dict:
        await self.db.execute(
            "INSERT OR IGNORE INTO users (user_id, guild_id) VALUES (?, ?)",
            (user_id, guild_id),
        )
        await self.db.commit()
        async with self.db.execute(
            "SELECT * FROM users WHERE user_id=? AND guild_id=?",
            (user_id, guild_id),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else {}

    async def set_user(self, user_id: int, guild_id: int, **fields):
        if not fields:
            return
        clause = ", ".join(f"{k}=?" for k in fields)
        vals   = list(fields.values()) + [user_id, guild_id]
        await self.db.execute(
            f"UPDATE users SET {clause} WHERE user_id=? AND guild_id=?", vals
        )
        await self.db.commit()

    async def add_balance(self, user_id: int, guild_id: int, amount: int):
        await self.get_user(user_id, guild_id)   # ensure row exists
        await self.db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id=? AND guild_id=?",
            (amount, user_id, guild_id),
        )
        await self.db.commit()

    # ── Inventory helpers ──────────────────────────────────────────────────────
    async def add_item(self, user_id: int, guild_id: int, item_id: str, qty: int = 1):
        await self.db.execute("""
            INSERT INTO inventory (user_id, guild_id, item_id, quantity) VALUES (?,?,?,?)
            ON CONFLICT(user_id, guild_id, item_id)
            DO UPDATE SET quantity = quantity + excluded.quantity
        """, (user_id, guild_id, item_id, qty))
        await self.db.commit()

    async def remove_item(self, user_id: int, guild_id: int, item_id: str, qty: int = 1) -> bool:
        async with self.db.execute(
            "SELECT quantity FROM inventory WHERE user_id=? AND guild_id=? AND item_id=?",
            (user_id, guild_id, item_id),
        ) as cur:
            row = await cur.fetchone()
        if not row or row["quantity"] < qty:
            return False
        new_qty = row["quantity"] - qty
        if new_qty == 0:
            await self.db.execute(
                "DELETE FROM inventory WHERE user_id=? AND guild_id=? AND item_id=?",
                (user_id, guild_id, item_id),
            )
        else:
            await self.db.execute(
                "UPDATE inventory SET quantity=? WHERE user_id=? AND guild_id=? AND item_id=?",
                (new_qty, user_id, guild_id, item_id),
            )
        await self.db.commit()
        return True

    async def has_item(self, user_id: int, guild_id: int, item_id: str) -> bool:
        async with self.db.execute(
            "SELECT 1 FROM inventory WHERE user_id=? AND guild_id=? AND item_id=? AND quantity>0",
            (user_id, guild_id, item_id),
        ) as cur:
            return (await cur.fetchone()) is not None

    async def get_inventory(self, user_id: int, guild_id: int) -> list:
        async with self.db.execute(
            "SELECT item_id, quantity FROM inventory WHERE user_id=? AND guild_id=? AND quantity>0",
            (user_id, guild_id),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    # ── Warning helpers ────────────────────────────────────────────────────────
    async def add_warning(self, user_id: int, guild_id: int, mod_id: int, reason: str) -> int:
        await self.db.execute(
            "INSERT INTO warnings (user_id, guild_id, mod_id, reason) VALUES (?,?,?,?)",
            (user_id, guild_id, mod_id, reason),
        )
        await self.db.commit()
        async with self.db.execute(
            "SELECT COUNT(*) as c FROM warnings WHERE user_id=? AND guild_id=?",
            (user_id, guild_id),
        ) as cur:
            row = await cur.fetchone()
            return row["c"]

    async def get_warnings(self, user_id: int, guild_id: int) -> list:
        async with self.db.execute(
            "SELECT * FROM warnings WHERE user_id=? AND guild_id=? ORDER BY created_at DESC",
            (user_id, guild_id),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def clear_warnings(self, user_id: int, guild_id: int):
        await self.db.execute(
            "DELETE FROM warnings WHERE user_id=? AND guild_id=?",
            (user_id, guild_id),
        )
        await self.db.commit()

    # ── Guild settings ─────────────────────────────────────────────────────────
    async def get_guild(self, guild_id: int) -> dict:
        await self.db.execute(
            "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,)
        )
        await self.db.commit()
        async with self.db.execute(
            "SELECT * FROM guild_settings WHERE guild_id=?", (guild_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else {}

    async def set_guild(self, guild_id: int, **fields):
        if not fields:
            return
        await self.get_guild(guild_id)   # ensure row exists
        clause = ", ".join(f"{k}=?" for k in fields)
        vals   = list(fields.values()) + [guild_id]
        await self.db.execute(
            f"UPDATE guild_settings SET {clause} WHERE guild_id=?", vals
        )
        await self.db.commit()

    # ── Leaderboard ────────────────────────────────────────────────────────────
    async def get_leaderboard(self, guild_id: int, limit: int = 10) -> list:
        async with self.db.execute(
            "SELECT user_id, xp, level FROM users WHERE guild_id=? ORDER BY xp DESC LIMIT ?",
            (guild_id, limit),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    # ── Reminders ──────────────────────────────────────────────────────────────
    async def add_reminder(self, user_id: int, channel_id: int, content: str, remind_at: datetime) -> int:
        cur = await self.db.execute(
            "INSERT INTO reminders (user_id, channel_id, content, remind_at) VALUES (?,?,?,?)",
            (user_id, channel_id, content, remind_at.isoformat()),
        )
        await self.db.commit()
        return cur.lastrowid

    async def get_due_reminders(self) -> list:
        now = datetime.now(timezone.utc).isoformat()
        async with self.db.execute(
            "SELECT * FROM reminders WHERE remind_at <= ?", (now,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def delete_reminder(self, rid: int):
        await self.db.execute("DELETE FROM reminders WHERE id=?", (rid,))
        await self.db.commit()

    async def close(self):
        if self.db:
            await self.db.close()

    # ── Auto Role ──────────────────────────────────────────────────────────────
    async def add_autorole(self, guild_id: int, channel_id: int, message_id: int, role_id: int):
        await self.db.execute("""
            INSERT OR REPLACE INTO autoroles (guild_id, channel_id, message_id, role_id)
            VALUES (?, ?, ?, ?)
        """, (guild_id, channel_id, message_id, role_id))
        await self.db.commit()

    async def remove_autorole(self, guild_id: int, role_id: int) -> bool:
        cur = await self.db.execute(
            "DELETE FROM autoroles WHERE guild_id=? AND role_id=?", (guild_id, role_id)
        )
        await self.db.commit()
        return cur.rowcount > 0

    async def get_autoroles(self, guild_id: int) -> list:
        async with self.db.execute(
            "SELECT * FROM autoroles WHERE guild_id=?", (guild_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def get_autorole_by_message(self, guild_id: int, message_id: int) -> dict:
        async with self.db.execute(
            "SELECT * FROM autoroles WHERE guild_id=? AND message_id=?", (guild_id, message_id)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    # ── Suggestions ────────────────────────────────────────────────────────────
    async def add_suggestion(self, guild_id: int, user_id: int, content: str) -> int:
        cur = await self.db.execute(
            "INSERT INTO suggestions (guild_id, user_id, content) VALUES (?, ?, ?)",
            (guild_id, user_id, content),
        )
        await self.db.commit()
        return cur.lastrowid

    async def get_suggestion(self, suggestion_id: int) -> dict:
        async with self.db.execute(
            "SELECT * FROM suggestions WHERE id=?", (suggestion_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def update_suggestion(self, suggestion_id: int, **fields):
        if not fields:
            return
        clause = ", ".join(f"{k}=?" for k in fields)
        vals   = list(fields.values()) + [suggestion_id]
        await self.db.execute(f"UPDATE suggestions SET {clause} WHERE id=?", vals)
        await self.db.commit()

    async def get_suggestions(self, guild_id: int, status: str = None) -> list:
        if status:
            async with self.db.execute(
                "SELECT * FROM suggestions WHERE guild_id=? AND status=? ORDER BY created_at DESC",
                (guild_id, status),
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]
        async with self.db.execute(
            "SELECT * FROM suggestions WHERE guild_id=? ORDER BY created_at DESC", (guild_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    # ── Anti-Raid ──────────────────────────────────────────────────────────────
    async def set_antiraid(self, guild_id: int, **fields):
        await self.db.execute("""
            INSERT INTO antiraid (guild_id) VALUES (?)
            ON CONFLICT(guild_id) DO NOTHING
        """, (guild_id,))
        if fields:
            clause = ", ".join(f"{k}=?" for k in fields)
            vals   = list(fields.values()) + [guild_id]
            await self.db.execute(f"UPDATE antiraid SET {clause} WHERE guild_id=?", vals)
        await self.db.commit()

    async def get_antiraid(self, guild_id: int) -> dict:
        async with self.db.execute(
            "SELECT * FROM antiraid WHERE guild_id=?", (guild_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else {}

    async def get_all_antiraid(self) -> list:
        async with self.db.execute("SELECT * FROM antiraid WHERE enabled=1") as cur:
            return [dict(r) for r in await cur.fetchall()]

    # ── Chat Channel ───────────────────────────────────────────────────────────
    async def set_chat_channel(self, guild_id: int, channel_id: int):
        await self.db.execute("""
            INSERT INTO chat_channels (guild_id, channel_id) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET channel_id=excluded.channel_id
        """, (guild_id, channel_id))
        await self.db.commit()

    async def get_all_chat_channels(self) -> list:
        async with self.db.execute("SELECT * FROM chat_channels") as cur:
            return [dict(r) for r in await cur.fetchall()]
