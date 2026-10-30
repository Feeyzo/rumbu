import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.environ.get("RUMBU_DB", os.path.join(os.path.dirname(__file__), "..", "rumbu.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS farmers (
    phone TEXT PRIMARY KEY, name TEXT, lga TEXT, lang TEXT DEFAULT 'ha', created_at TEXT
);
CREATE TABLE IF NOT EXISTS prices (
    crop TEXT PRIMARY KEY, market TEXT, price INTEGER, prev_price INTEGER, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT, crop TEXT, bags INTEGER,
    ask_price INTEGER, status TEXT DEFAULT 'open', created_at TEXT
);
CREATE TABLE IF NOT EXISTS buyers (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, crop TEXT, bags INTEGER,
    max_price INTEGER, status TEXT DEFAULT 'open', created_at TEXT
);
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT, listing_id INTEGER, buyer_id INTEGER, crop TEXT,
    bags INTEGER, price INTEGER, created_at TEXT
);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT, lga TEXT, crop TEXT, problem TEXT,
    bags INTEGER, channel TEXT, note TEXT, recording_url TEXT, reward INTEGER DEFAULT 0,
    status TEXT DEFAULT 'new', created_at TEXT
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, name TEXT, org TEXT, phone TEXT,
    role TEXT, password_hash TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, direction TEXT, channel TEXT, phone TEXT,
    body TEXT, status TEXT, created_at TEXT
);
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with conn() as c:
        c.executescript(SCHEMA)
        cols = [r[1] for r in c.execute("PRAGMA table_info(buyers)")]
        if "user_id" not in cols:
            c.execute("ALTER TABLE buyers ADD COLUMN user_id INTEGER")


def q(sql, args=(), one=False):
    with conn() as c:
        rows = c.execute(sql, args).fetchall()
    rows = [dict(r) for r in rows]
    return (rows[0] if rows else None) if one else rows


def ex(sql, args=()):
    with conn() as c:
        cur = c.execute(sql, args)
        return cur.lastrowid


def normalize_phone(phone):
    p = "".join(ch for ch in (phone or "") if ch.isdigit() or ch == "+")
    if p.startswith("0") and len(p) == 11:
        return "+234" + p[1:]
    if p.startswith("234"):
        return "+" + p
    return p


# ---- farmers ----
def get_farmer(phone):
    return q("SELECT * FROM farmers WHERE phone=?", (normalize_phone(phone),), one=True)


def add_farmer(phone, name, lga, lang):
    ex(
        "INSERT OR REPLACE INTO farmers (phone, name, lga, lang, created_at) VALUES (?,?,?,?,?)",
        (normalize_phone(phone), name, lga, lang, now()),
    )


def set_lang(phone, lang):
    ex("UPDATE farmers SET lang=? WHERE phone=?", (lang, normalize_phone(phone)))


# ---- prices ----
def get_price(crop):
    return q("SELECT * FROM prices WHERE crop=?", (crop,), one=True)


def set_price(crop, price, market=None):
    old = get_price(crop)
    if old:
        ex(
            "UPDATE prices SET prev_price=price, price=?, market=COALESCE(?, market), updated_at=? WHERE crop=?",
            (price, market, now(), crop),
        )
    else:
        ex(
            "INSERT INTO prices (crop, market, price, prev_price, updated_at) VALUES (?,?,?,?,?)",
            (crop, market or "Dawanau", price, price, now()),
        )


# ---- messages log ----
def log_message(direction, channel, phone, body, status):
    ex(
        "INSERT INTO messages (direction, channel, phone, body, status, created_at) VALUES (?,?,?,?,?,?)",
        (direction, channel, normalize_phone(phone), body, status, now()),
    )
