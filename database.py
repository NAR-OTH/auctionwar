"""
إدارة قاعدة البيانات SQLite
كل البيانات مرتبطة بـ group_id لدعم عدة كروبات
"""

import sqlite3
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = "auction_war.db"


@contextmanager
def get_db():
    """مدير السياق للاتصال بقاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"خطأ في قاعدة البيانات: {e}")
        raise
    finally:
        conn.close()


def init_db():
    """إنشاء جداول قاعدة البيانات"""
    with get_db() as conn:
        cursor = conn.cursor()

        # ── جدول الكروبات ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_id     INTEGER PRIMARY KEY,
                group_name   TEXT,
                game_active  INTEGER DEFAULT 0,
                attack_locked INTEGER DEFAULT 0,
                join_locked  INTEGER DEFAULT 0,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── جدول التيمات ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id     INTEGER NOT NULL,
                team_name    TEXT NOT NULL,
                leader_id    INTEGER,
                leader_name  TEXT,
                treasury     INTEGER DEFAULT 0,
                honor_points INTEGER DEFAULT 0,
                active       INTEGER DEFAULT 1,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups(group_id),
                UNIQUE(group_id, team_name)
            )
        """)

        # ── جدول اللاعبين ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                group_id     INTEGER NOT NULL,
                username     TEXT,
                full_name    TEXT,
                team_id      INTEGER,
                coins        INTEGER DEFAULT 100,
                last_work    TIMESTAMP,
                last_attack  TIMESTAMP,
                total_work   INTEGER DEFAULT 0,
                joined_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups(group_id),
                FOREIGN KEY (team_id) REFERENCES teams(id),
                UNIQUE(user_id, group_id)
            )
        """)

        # ── جدول المزادات ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auctions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id     INTEGER NOT NULL,
                item_name    TEXT NOT NULL,
                item_type    TEXT NOT NULL,
                item_desc    TEXT,
                base_price   INTEGER NOT NULL,
                current_bid  INTEGER NOT NULL,
                winner_team  INTEGER,
                winner_name  TEXT,
                bidder_id    INTEGER,
                status       TEXT DEFAULT 'active',
                message_id   INTEGER,
                ends_at      TIMESTAMP,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups(group_id)
            )
        """)

        # ── جدول المزايدات ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bids (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                auction_id   INTEGER NOT NULL,
                team_id      INTEGER NOT NULL,
                user_id      INTEGER NOT NULL,
                amount       INTEGER NOT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (auction_id) REFERENCES auctions(id),
                FOREIGN KEY (team_id) REFERENCES teams(id)
            )
        """)

        # ── جدول الأصوات للقيادة ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leader_votes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id     INTEGER NOT NULL,
                team_id      INTEGER NOT NULL,
                voter_id     INTEGER NOT NULL,
                candidate_id INTEGER NOT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(group_id, team_id, voter_id)
            )
        """)

        # ── جدول تأثيرات الأيتمات النشطة ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_effects (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id     INTEGER NOT NULL,
                team_id      INTEGER NOT NULL,
                effect_type  TEXT NOT NULL,
                item_name    TEXT,
                expires_at   TIMESTAMP NOT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── جدول سجل الهجمات ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attack_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id     INTEGER NOT NULL,
                attacker_team INTEGER NOT NULL,
                defender_team INTEGER NOT NULL,
                stolen_amount INTEGER DEFAULT 0,
                result       TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        logger.info("✅ تم إنشاء جداول قاعدة البيانات")


# ══════════════════════════════════════════
#  دوال مساعدة - الكروبات
# ══════════════════════════════════════════

def ensure_group(group_id: int, group_name: str = ""):
    """تأكد من وجود الكروب في قاعدة البيانات"""
    with get_db() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO groups (group_id, group_name, game_active)
            VALUES (?, ?, 1)
        """, (group_id, group_name))
        conn.execute("""
            UPDATE groups SET group_name = ? WHERE group_id = ?
        """, (group_name, group_id))


def get_group(group_id: int):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM groups WHERE group_id = ?", (group_id,)
        ).fetchone()


def set_group_flag(group_id: int, flag: str, value: int):
    """تغيير إعداد في الكروب (attack_locked, join_locked, game_active)"""
    with get_db() as conn:
        conn.execute(f"UPDATE groups SET {flag} = ? WHERE group_id = ?", (value, group_id))


# ══════════════════════════════════════════
#  دوال مساعدة - اللاعبون
# ══════════════════════════════════════════

def get_or_create_player(user_id: int, group_id: int, username: str, full_name: str):
    with get_db() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO players (user_id, group_id, username, full_name)
            VALUES (?, ?, ?, ?)
        """, (user_id, group_id, username, full_name))
        conn.execute("""
            UPDATE players SET username = ?, full_name = ?
            WHERE user_id = ? AND group_id = ?
        """, (username, full_name, user_id, group_id))
        return conn.execute(
            "SELECT * FROM players WHERE user_id = ? AND group_id = ?",
            (user_id, group_id)
        ).fetchone()


def get_player(user_id: int, group_id: int):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM players WHERE user_id = ? AND group_id = ?",
            (user_id, group_id)
        ).fetchone()


def update_player_coins(user_id: int, group_id: int, amount: int):
    with get_db() as conn:
        conn.execute("""
            UPDATE players SET coins = MAX(0, coins + ?)
            WHERE user_id = ? AND group_id = ?
        """, (amount, user_id, group_id))


def update_last_work(user_id: int, group_id: int):
    with get_db() as conn:
        conn.execute("""
            UPDATE players SET last_work = CURRENT_TIMESTAMP, total_work = total_work + 1
            WHERE user_id = ? AND group_id = ?
        """, (user_id, group_id))


def update_last_attack(user_id: int, group_id: int):
    with get_db() as conn:
        conn.execute("""
            UPDATE players SET last_attack = CURRENT_TIMESTAMP
            WHERE user_id = ? AND group_id = ?
        """, (user_id, group_id))


# ══════════════════════════════════════════
#  دوال مساعدة - التيمات
# ══════════════════════════════════════════

def create_team(group_id: int, team_name: str, leader_id: int, leader_name: str) -> bool:
    try:
        with get_db() as conn:
            cursor = conn.execute("""
                INSERT INTO teams (group_id, team_name, leader_id, leader_name)
                VALUES (?, ?, ?, ?)
            """, (group_id, team_name, leader_id, leader_name))
            team_id = cursor.lastrowid
            # اجعل المؤسس عضواً في التيم
            conn.execute("""
                UPDATE players SET team_id = ? WHERE user_id = ? AND group_id = ?
            """, (team_id, leader_id, group_id))
        return True
    except sqlite3.IntegrityError:
        return False


def get_team(team_id: int):
    with get_db() as conn:
        return conn.execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()


def get_team_by_name(group_id: int, team_name: str):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM teams WHERE group_id = ? AND team_name = ? AND active = 1",
            (group_id, team_name)
        ).fetchone()


def get_group_teams(group_id: int):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM teams WHERE group_id = ? AND active = 1 ORDER BY honor_points DESC",
            (group_id,)
        ).fetchall()


def get_team_members(team_id: int):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM players WHERE team_id = ?", (team_id,)
        ).fetchall()


def join_team(user_id: int, group_id: int, team_id: int) -> bool:
    with get_db() as conn:
        # تحقق من عدد الأعضاء
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM players WHERE team_id = ?", (team_id,)
        ).fetchone()["cnt"]
        from config import MAX_TEAM_MEMBERS
        if count >= MAX_TEAM_MEMBERS:
            return False
        conn.execute(
            "UPDATE players SET team_id = ? WHERE user_id = ? AND group_id = ?",
            (team_id, user_id, group_id)
        )
    return True


def update_treasury(team_id: int, amount: int):
    with get_db() as conn:
        conn.execute("""
            UPDATE teams SET treasury = MAX(0, treasury + ?) WHERE id = ?
        """, (amount, team_id))


def update_honor(team_id: int, points: int):
    with get_db() as conn:
        conn.execute("""
            UPDATE teams SET honor_points = honor_points + ? WHERE id = ?
        """, (points, team_id))


def is_team_leader(user_id: int, group_id: int) -> tuple:
    """يرجع (True, team) إذا كان القائد، وإلا (False, None)"""
    with get_db() as conn:
        team = conn.execute("""
            SELECT * FROM teams WHERE group_id = ? AND leader_id = ? AND active = 1
        """, (group_id, user_id)).fetchone()
    return (True, team) if team else (False, None)


# ══════════════════════════════════════════
#  دوال مساعدة - المزادات
# ══════════════════════════════════════════

def create_auction(group_id: int, item: dict, ends_at) -> int:
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO auctions (group_id, item_name, item_type, item_desc, base_price, current_bid, ends_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (group_id, item["name"], item["type"], item["description"],
              item["base_price"], item["base_price"], ends_at))
        return cursor.lastrowid


def get_active_auction(group_id: int):
    with get_db() as conn:
        return conn.execute("""
            SELECT * FROM auctions
            WHERE group_id = ? AND status = 'active'
            ORDER BY created_at DESC LIMIT 1
        """, (group_id,)).fetchone()


def place_bid(auction_id: int, team_id: int, user_id: int, amount: int, team_name: str) -> bool:
    with get_db() as conn:
        auction = conn.execute(
            "SELECT * FROM auctions WHERE id = ? AND status = 'active'", (auction_id,)
        ).fetchone()
        if not auction:
            return False
        from config import AUCTION_MIN_INCREMENT
        if amount < auction["current_bid"] + AUCTION_MIN_INCREMENT:
            return False
        # تحقق من رصيد الخزينة
        team = conn.execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()
        if not team or team["treasury"] < amount:
            return False

        conn.execute("""
            INSERT INTO bids (auction_id, team_id, user_id, amount)
            VALUES (?, ?, ?, ?)
        """, (auction_id, team_id, user_id, amount))
        conn.execute("""
            UPDATE auctions SET current_bid = ?, winner_team = ?, winner_name = ?, bidder_id = ?
            WHERE id = ?
        """, (amount, team_id, team_name, user_id, auction_id))
    return True


def close_auction(auction_id: int):
    with get_db() as conn:
        conn.execute("""
            UPDATE auctions SET status = 'closed' WHERE id = ?
        """, (auction_id,))
        auction = conn.execute(
            "SELECT * FROM auctions WHERE id = ?", (auction_id,)
        ).fetchone()
        if auction and auction["winner_team"]:
            # اخصم المبلغ من خزينة الفائز
            conn.execute("""
                UPDATE teams SET treasury = MAX(0, treasury - ?)
                WHERE id = ?
            """, (auction["current_bid"], auction["winner_team"]))
            # أضف تأثير الأيتم
            from datetime import datetime, timedelta
            expires = datetime.now() + timedelta(hours=24)
            conn.execute("""
                INSERT INTO active_effects (group_id, team_id, effect_type, item_name, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (auction["group_id"], auction["winner_team"],
                  auction["item_type"], auction["item_name"], expires))
        return auction


def set_auction_message_id(auction_id: int, message_id: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE auctions SET message_id = ? WHERE id = ?", (message_id, auction_id)
        )


# ══════════════════════════════════════════
#  دوال مساعدة - التأثيرات
# ══════════════════════════════════════════

def has_effect(team_id: int, effect_type: str) -> bool:
    with get_db() as conn:
        result = conn.execute("""
            SELECT COUNT(*) as cnt FROM active_effects
            WHERE team_id = ? AND effect_type = ? AND expires_at > CURRENT_TIMESTAMP
        """, (team_id, effect_type)).fetchone()
    return result["cnt"] > 0


def get_team_effects(team_id: int):
    with get_db() as conn:
        return conn.execute("""
            SELECT * FROM active_effects
            WHERE team_id = ? AND expires_at > CURRENT_TIMESTAMP
        """, (team_id,)).fetchall()
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id     INTEGER NOT NULL,
                team_name    TEXT NOT NULL,
                leader_id    INTEGER,
                leader_name  TEXT,
                treasury     INTEGER DEFAULT 0,
                honor_points INTEGER DEFAULT 0,
                active       INTEGER DEFAULT 1,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups(group_id),
                UNIQUE(group_id, team_name)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                group_id    INTEGER NOT NULL,
                username    TEXT,
                full_name   TEXT,
                team_id     INTEGER,
                coins       INTEGER DEFAULT 100,
                last_work   TIMESTAMP,
                last_attack TIMESTAMP,
                total_work  INTEGER DEFAULT 0,
                joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups(group_id),
                FOREIGN KEY (team_id) REFERENCES teams(id),
                UNIQUE(user_id, group_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auctions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id    INTEGER NOT NULL,
                item_name   TEXT NOT NULL,
                item_type   TEXT NOT NULL,
                item_desc   TEXT,
                base_price  INTEGER NOT NULL,
                current_bid INTEGER NOT NULL,
                winner_team INTEGER,
                winner_name TEXT,
                bidder_id   INTEGER,
                status      TEXT DEFAULT 'active',
                message_id  INTEGER,
                ends_at     TIMESTAMP,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups(group_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bids (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                auction_id INTEGER NOT NULL,
                team_id    INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                amount     INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (auction_id) REFERENCES auctions(id),
                FOREIGN KEY (team_id) REFERENCES teams(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leader_votes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id     INTEGER NOT NULL,
                team_id      INTEGER NOT NULL,
                voter_id     INTEGER NOT NULL,
                candidate_id INTEGER NOT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(group_id, team_id, voter_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_effects (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id    INTEGER NOT NULL,
                team_id     INTEGER NOT NULL,
                effect_type TEXT NOT NULL,
                item_name   TEXT,
                expires_at  TIMESTAMP NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attack_log (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id      INTEGER NOT NULL,
                attacker_team INTEGER NOT NULL,
                defender_team INTEGER NOT NULL,
                stolen_amount INTEGER DEFAULT 0,
                result        TEXT,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ تم إنشاء جداول قاعدة البيانات")


def ensure_group(group_id: int, group_name: str = ""):
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO groups (group_id, group_name, game_active) VALUES (?, ?, 1)", (group_id, group_name))
        conn.execute("UPDATE groups SET group_name = ? WHERE group_id = ?", (group_name, group_id))


def get_group(group_id: int):
    with get_db() as conn:
        return conn.execute("SELECT * FROM groups WHERE group_id = ?", (group_id,)).fetchone()


def set_group_flag(group_id: int, flag: str, value: int):
    with get_db() as conn:
        conn.execute(f"UPDATE groups SET {flag} = ? WHERE group_id = ?", (value, group_id))


def get_or_create_player(user_id: int, group_id: int, username: str, full_name: str):
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO players (user_id, group_id, username, full_name) VALUES (?, ?, ?, ?)", (user_id, group_id, username, full_name))
        conn.execute("UPDATE players SET username = ?, full_name = ? WHERE user_id = ? AND group_id = ?", (username, full_name, user_id, group_id))
        return conn.execute("SELECT * FROM players WHERE user_id = ? AND group_id = ?", (user_id, group_id)).
