"""Starting prices and optional demo data so the dashboard isn't empty on stage.

Prices are illustrative placeholders, not live market data. Update them from
the dashboard (or wire in a real price feed) before relying on them.
"""
import random

from . import db

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
    for _ in range(24):
        phone, _, lga, _ = rng.choice(DEMO_FARMERS)
        db.ex("INSERT INTO reports (phone, lga, crop, problem, bags, channel, note, reward, status, created_at)"
              " VALUES (?,?,?,?,?,?,?,?,?,?)",
              (phone, lga, rng.choice(crops), rng.choice(problems), rng.randint(1, 15),
               rng.choice(["ussd", "ussd", "sms", "voice"]), "demo", 100, "advised", db.now()))
