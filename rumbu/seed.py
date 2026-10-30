"""Starting prices and optional demo data so the dashboard isn't empty on stage.

Prices are illustrative placeholders, not live market data. Update them from
the dashboard (or wire in a real price feed) before relying on them.
"""
import os
import random
from datetime import datetime, timedelta, timezone

from . import db

DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "rumbu2026")
DEMO_USERS = [
    # email, name, org, phone, role
    ("admin@rumbu.ng", "RUMBU Ops", "RUMBU / LOGI-Q", "+2348000000000", "admin"),
    ("partner@rumbu.ng", "Fatima Yusuf", "Kano State Ministry of Agriculture (demo)", "+2348000000010", "partner"),
    ("buyer@rumbu.ng", "Dawanau Grains Ltd", "Dawanau Grains Ltd", "+2348090000001", "buyer"),
]

# crop: (market, current price, price a month ago)  NGN per 100kg bag / tomato basket
PRICES = {
    "maize": ("Dawanau", 48000, 44000),
    "sorghum": ("Dawanau", 45000, 46000),
    "millet": ("Dawanau", 50000, 47000),
    "rice": ("Dawanau", 60000, 58000),
    "cowpea": ("Dawanau", 95000, 88000),
    "groundnut": ("Dawanau", 80000, 82000),
    "tomato": ("Kano", 25000, 38000),
}

DEMO_FARMERS = [
    ("+2348030000001", "Malam Sani", "dawakin_tofa", "ha"),
    ("+2348030000002", "Hajiya Lami", "wudil", "ha"),
    ("+2348030000003", "Musa Garba", "bichi", "ha"),
    ("+2348030000004", "Aisha Bello", "rano", "en"),
    ("+2348030000005", "Ibrahim Kura", "kura", "ha"),
    ("+2348030000006", "Halima Gaya", "gaya", "ha"),
]

DEMO_BUYERS = [
    ("Dawanau Grains Ltd", "+2348090000001", "maize", 200, 50000),
    ("Kano Feed Mills", "+2348090000002", "sorghum", 100, 46000),
    ("Arewa Agro Aggregators", "+2348090000003", "cowpea", 50, 96000),
]


def seed_prices():
    for crop, (market, price, prev) in PRICES.items():
        if not db.get_price(crop):
            db.ex("INSERT INTO prices (crop, market, price, prev_price, updated_at) VALUES (?,?,?,?,?)",
                  (crop, market, price, prev, db.now()))


def seed_demo_users():
    from .auth import create_user
    for email, name, org, phone, role in DEMO_USERS:
        if not db.q("SELECT 1 FROM users WHERE email=?", (email,), one=True):
            create_user(email, DEMO_PASSWORD, name, role, org, phone)
    buyer = db.q("SELECT id FROM users WHERE email='buyer@rumbu.ng'", one=True)
    db.ex("UPDATE buyers SET user_id=? WHERE phone='+2348090000001' AND user_id IS NULL", (buyer["id"],))


def seed_admin_from_env():
    """Create the first real admin from ADMIN_EMAIL / ADMIN_PASSWORD if set."""
    email, pw = os.environ.get("ADMIN_EMAIL"), os.environ.get("ADMIN_PASSWORD")
    if email and pw and not db.q("SELECT 1 FROM users WHERE email=?", (email.lower(),), one=True):
        from .auth import create_user
        create_user(email, pw, "Admin", "admin", "RUMBU")


def seed_demo():
    if db.q("SELECT 1 FROM farmers LIMIT 1"):
        return
    rng = random.Random(7)
    for phone, name, lga, lang in DEMO_FARMERS:
        db.add_farmer(phone, name, lga, lang)
    for b in DEMO_BUYERS:
        db.ex("INSERT INTO buyers (name, phone, crop, bags, max_price, created_at) VALUES (?,?,?,?,?,?)",
              (*b, db.now()))
    problems = ["insects", "insects", "moisture", "moisture", "moisture", "rodents", "rot"]
    crops = ["maize", "maize", "sorghum", "cowpea", "millet", "groundnut", "tomato"]
    today = datetime.now(timezone.utc)
    for i in range(40):
        phone, _, lga, _ = rng.choice(DEMO_FARMERS)
        # spread over the last four weeks, getting busier as harvest comes in
        when = today - timedelta(days=int(27 * (1 - (i / 40) ** 0.7)), hours=rng.randint(1, 20))
        db.ex("INSERT INTO reports (phone, lga, crop, problem, bags, channel, note, reward, status, created_at)"
              " VALUES (?,?,?,?,?,?,?,?,?,?)",
              (phone, lga, rng.choice(crops), rng.choice(problems), rng.randint(1, 15),
               rng.choice(["ussd", "ussd", "sms", "voice"]), "demo", 100, "advised",
               when.isoformat(timespec="seconds")))
    # open farmer listings for the buyer portal (priced above current buyer limits so they stay open)
    for phone, crop, bags, ask in [
        ("+2348030000003", "millet", 25, 51000),
        ("+2348030000005", "maize", 12, 55000),
        ("+2348030000002", "groundnut", 40, 0),
        ("+2348030000006", "rice", 15, 62000),
        ("+2348030000004", "cowpea", 8, 99000),
    ]:
        db.ex("INSERT INTO listings (phone, crop, bags, ask_price, created_at) VALUES (?,?,?,?,?)",
              (phone, crop, bags, ask, db.now()))
    # two farmer messages waiting for an agronomist, to demo the reply flow
    for phone, lga, crop, problem, channel, note in [
        ("+2348030000005", "kura", None, "voice_note", "voice", "Voice note - awaiting review"),
        ("+2348030000002", "wudil", "maize", "other", "sms",
         "masarata tana canza launi ta yi baki a cikin buhu"),
    ]:
        db.ex("INSERT INTO reports (phone, lga, crop, problem, bags, channel, note, reward, status, created_at)"
              " VALUES (?,?,?,?,?,?,?,?,?,?)", (phone, lga, crop, problem, 0, channel, note, 100, "new", db.now()))
    # a few completed sales so the marketplace has history
    from . import services
    services.create_listing("+2348030000001", "maize", 20, 0)
    services.create_listing("+2348030000003", "sorghum", 30, 44000)
    services.create_listing("+2348030000004", "cowpea", 10, 95000)
