import sqlite3
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)
DB_PATH = "auction_war.db"


@contextmanager
def get_db():
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
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_id      INTEGER PRIMARY KEY,
                group_name    TEXT,
                game_active   INTEGER DEFAULT 0,
                attack_locked INTEGER DEFAULT 0,
                join_locked   INTEGER DEFAULT 0,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
