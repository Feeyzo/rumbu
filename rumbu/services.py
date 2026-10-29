"""Core logic shared by the USSD, SMS and voice channels."""
import os
from datetime import datetime, timezone

from . import at, db
from .content import ADVICE, crop_name, crop_unit, find_crop, lga_name, t

REWARD = int(os.environ.get("REPORT_REWARD_NGN", "100"))


# ---------- prices ----------
def price_text(crop, lang):
    p = db.get_price(crop)
    if not p:
        return t("invalid", lang)
    line = t("price_line", lang, crop=crop_name(crop, lang), price=p["price"],
             unit=crop_unit(crop, lang), market=p["market"])
    prev = p["prev_price"] or p["price"]
    pct = round((p["price"] - prev) * 100 / prev) if prev else 0
    if pct >= 5:
        trend = t("price_up", lang, pct=pct)
    elif pct <= -5:
        trend = t("price_down", lang, pct=abs(pct))
    else:
        trend = t("price_flat", lang)
    return f"{line}\n{trend}"


# ---------- marketplace ----------
def _market_price(crop):
    p = db.get_price(crop)
    return p["price"] if p else 0


def _do_match(listing, buyer):
    price = listing["ask_price"] or _market_price(listing["crop"])
    bags = min(listing["bags"], buyer["bags"])
    db.ex("INSERT INTO matches (listing_id, buyer_id, crop, bags, price, created_at) VALUES (?,?,?,?,?,?)",
          (listing["id"], buyer["id"], listing["crop"], bags, price, db.now()))
    db.ex("UPDATE listings SET status='matched' WHERE id=?", (listing["id"],))
    left = buyer["bags"] - bags
    if left > 0:
        db.ex("UPDATE buyers SET bags=? WHERE id=?", (left, buyer["id"]))
    else:
        db.ex("UPDATE buyers SET status='matched' WHERE id=?", (buyer["id"],))

    farmer = db.get_farmer(listing["phone"]) or {"name": "Manomi", "lga": "", "lang": "ha"}
    flang = farmer["lang"]
    at.send_sms(listing["phone"], t("match_farmer", flang, buyer=buyer["name"], bags=bags,
                                    crop=crop_name(listing["crop"], flang), price=price,
                                    buyer_phone=buyer["phone"]))
    at.send_sms(buyer["phone"], t("match_buyer", "en", farmer=farmer["name"], lga=lga_name(farmer["lga"]),
                                  bags=bags, crop=crop_name(listing["crop"], "en"), price=price,
                                  farmer_phone=listing["phone"]))
    return True


def _effective_price(listing):
    return listing["ask_price"] or _market_price(listing["crop"])


def create_listing(phone, crop, bags, ask_price):
    lid = db.ex("INSERT INTO listings (phone, crop, bags, ask_price, created_at) VALUES (?,?,?,?,?)",
                (db.normalize_phone(phone), crop, bags, ask_price, db.now()))
    listing = db.q("SELECT * FROM listings WHERE id=?", (lid,), one=True)
    buyers = db.q("SELECT * FROM buyers WHERE crop=? AND status='open' ORDER BY max_price DESC", (crop,))
    for b in buyers:
        if b["max_price"] >= _effective_price(listing):
            return _do_match(listing, b)
    return False


def create_buyer(name, phone, crop, bags, max_price):
    bid = db.ex("INSERT INTO buyers (name, phone, crop, bags, max_price, created_at) VALUES (?,?,?,?,?,?)",
                (name, db.normalize_phone(phone), crop, bags, max_price, db.now()))
    matched = 0
    for listing in db.q("SELECT * FROM listings WHERE crop=? AND status='open' ORDER BY created_at", (crop,)):
        buyer = db.q("SELECT * FROM buyers WHERE id=?", (bid,), one=True)
        if buyer["status"] != "open":
            break
        if buyer["max_price"] >= _effective_price(listing):
            _do_match(listing, buyer)
            matched += 1
    return bid, matched


# ---------- loss reports ----------
def _rewarded_today(phone):
    today = datetime.now(timezone.utc).date().isoformat()
    row = db.q("SELECT COUNT(*) n FROM reports WHERE phone=? AND reward>0 AND created_at LIKE ?",
               (db.normalize_phone(phone), today + "%"), one=True)
    return row["n"] > 0


def create_report(phone, crop, problem, bags=0, channel="ussd", note="", recording_url=None):
    """Save a loss report, pay the airtime reward (once a day) and SMS advice."""
    phone = db.normalize_phone(phone)
    farmer = db.get_farmer(phone) or {"lga": "unknown", "lang": "ha"}
    lang = farmer["lang"]
    reward = 0 if _rewarded_today(phone) or REWARD <= 0 else REWARD
    rid = db.ex(
        "INSERT INTO reports (phone, lga, crop, problem, bags, channel, note, recording_url, reward, created_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (phone, farmer["lga"], crop, problem, bags, channel, note, recording_url, reward, db.now()),
    )
    if reward:
        if at.send_airtime(phone, reward).startswith("error"):
            db.ex("UPDATE reports SET reward=0 WHERE id=?", (rid,))
            reward = 0
    if problem in ADVICE:
        at.send_sms(phone, t("advice_sms", lang, crop=crop_name(crop, lang) if crop else "RUMBU",
                             advice=ADVICE[problem][lang]))
    return rid, reward


# ---------- free-text triage (SMS and voice transcripts) ----------
KEYWORDS = {
    "insects": ["kwari", "kwaro", "gara", "tsutsa", "weevil", "insect", "bug", "worm", "pest"],
    "moisture": ["danshi", "jike", "fumfuna", "ruwa", "mould", "mold", "wet", "damp", "moist", "fungus"],
    "rodents": ["bera", "beraye", "kusu", "rat", "rats", "mice", "mouse", "rodent"],
    "rot": ["rube", "rubewa", "lalace", "rot", "rotten", "rotting", "spoil"],
}


def classify(text):
    """Return (problem, crop) guessed from Hausa or English free text."""
    words = [w.strip(".,!?") for w in (text or "").lower().split()]
    crop = next((c for c in (find_crop(w) for w in words) if c), None)
    for problem, keys in KEYWORDS.items():
        if any(any(w.startswith(k) for k in keys) for w in words):
            return problem, crop
    return "other", crop
