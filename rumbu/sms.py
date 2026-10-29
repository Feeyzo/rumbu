"""Two-way SMS commands (Hausa or English keywords).

  FARASHI MASARA / PRICE MAIZE          -> market price + trend
  MATSALA masara ta yi kwari / HELP ... -> AI triage, advice, airtime reward
  SAYA MASARA 20 50000 / BUY MAIZE 20 50000 -> buyer request, auto-match
"""
from . import at, db, services
from .content import crop_name, t

PRICE = {"farashi", "price", "prices"}
HELP = {"matsala", "help", "taimako", "problem"}
BUY = {"saya", "buy"}


def handle(phone, text):
    phone = db.normalize_phone(phone)
    db.log_message("in", "sms", phone, text, "received")
    farmer = db.get_farmer(phone)
    words = (text or "").strip().split()
    cmd = words[0].lower() if words else ""
    lang = farmer["lang"] if farmer else ("en" if cmd in {"price", "prices", "help", "problem", "buy"} else "ha")

    if cmd in PRICE and len(words) > 1:
        from .content import find_crop
        crop = find_crop(words[1])
        reply = services.price_text(crop, lang) if crop else t("sms_help", lang)
        at.send_sms(phone, "RUMBU: " + reply)
        return reply

    if cmd in HELP and len(words) > 1:
        problem, crop = services.classify(" ".join(words[1:]))
        _, reward = services.create_report(phone, crop, problem, 0, channel="sms", note=" ".join(words[1:]))
        if reward:
            at.send_sms(phone, t("report_thanks", lang, reward=reward))
        return problem

    if cmd in BUY and len(words) >= 3:
        from .content import find_crop
        crop = find_crop(words[1])
        try:
            bags = int(words[2])
            max_price = int(words[3].replace(",", "")) if len(words) > 3 else 10**9
        except ValueError:
            crop = None
        if crop:
            name = farmer["name"] if farmer else f"Buyer {phone[-4:]}"
            at.send_sms(phone, t("buyer_saved", lang, bags=bags, crop=crop_name(crop, lang)))
            services.create_buyer(name, phone, crop, bags, max_price)
            return "buyer"

    at.send_sms(phone, t("sms_help", lang))
    return "help"
