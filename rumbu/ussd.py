"""USSD menu. Africa's Talking sends the whole session history in `text`
joined by '*', e.g. "2*1*10*0" = Sell > Maize > 10 bags > market price."""
import os

from . import at, db, services
from .content import CROPS, LGAS, PROBLEMS, crop_menu, crop_name, lga_menu, problem_menu, t


def con(body):
    return "CON " + body


def end(body):
    return "END " + body


def _pick(value, items):
    """Turn a menu number into the matching item, or None."""
    try:
        i = int(value)
    except (TypeError, ValueError):
        return None
    return items[i - 1] if 1 <= i <= len(items) else None


def _int(value, lo=0, hi=100000000):
    try:
        n = int(str(value).replace(",", "").strip())
    except ValueError:
        return None
    return n if lo <= n <= hi else None


def handle(phone, text):
    parts = text.split("*") if text else []
    farmer = db.get_farmer(phone)
    if not farmer:
        return _register(phone, parts)
    return _menu(phone, farmer, parts)


def _register(phone, parts):
    n = len(parts)
    if n == 0:
        return con(t("welcome_new", "ha"))
    lang = {"1": "ha", "2": "en"}.get(parts[0])
    if not lang:
        return end(t("invalid", "ha"))
    if n == 1:
        return con(t("ask_name", lang))
    name = parts[1].strip()[:40] or "Manomi"
    if n == 2:
        return con(t("ask_lga", lang) + "\n" + lga_menu())
    lga = _pick(parts[2], LGAS)
    if not lga:
        return end(t("invalid", lang))
    db.add_farmer(phone, name, lga[0], lang)
    at.send_sms(phone, t("welcome_sms", lang, name=name))
    return end(t("registered", lang, name=name))


def _menu(phone, farmer, parts):
    lang = farmer["lang"]
    n = len(parts)
    if n == 0:
        return con(t("main_menu", lang))
    choice = parts[0]
    bad = end(t("invalid", lang))

    # 1. Market prices
    if choice == "1":
        if n == 1:
            return con(t("choose_crop", lang) + "\n" + crop_menu(lang))
        crop = _pick(parts[1], CROPS)
        return end(services.price_text(crop[0], lang)) if crop else bad

    # 2. Sell produce
    if choice == "2":
        if n == 1:
            return con(t("choose_crop", lang) + "\n" + crop_menu(lang))
        crop = _pick(parts[1], CROPS)
        if not crop:
            return bad
        if n == 2:
            return con(t("ask_bags", lang))
        bags = _int(parts[2], 1, 100000)
        if not bags:
            return bad
        if n == 3:
            return con(t("ask_price", lang))
        price = _int(parts[3])
        if price is None:
            return bad
        matched = services.create_listing(phone, crop[0], bags, price)
        msg = t("listed", lang, bags=bags, crop=crop_name(crop[0], lang))
        if matched:
            msg += "\n" + t("listed_matched", lang)
        return end(msg)

    # 3. Report a loss problem (earns airtime)
    if choice == "3":
        if n == 1:
            return con(t("choose_crop", lang) + "\n" + crop_menu(lang))
        crop = _pick(parts[1], CROPS)
        if not crop:
            return bad
        if n == 2:
            return con(t("choose_problem", lang) + "\n" + problem_menu(lang))
        problem = _pick(parts[2], PROBLEMS)
        if not problem:
            return bad
        if n == 3:
            return con(t("ask_bags_affected", lang))
        bags = _int(parts[3], 0, 100000)
        if bags is None:
            return bad
        _, reward = services.create_report(phone, crop[0], problem[0], bags, channel="ussd")
        return end(t("report_thanks", lang, reward=reward) if reward else t("report_thanks_noreward", lang))

    # 4. Storage advice
    if choice == "4":
        if n == 1:
            return con(t("choose_crop", lang) + "\n" + crop_menu(lang))
        crop = _pick(parts[1], CROPS)
        if not crop:
            return bad
        from .content import STORAGE_TIPS
        tip = STORAGE_TIPS[crop[0]][lang]
        at.send_sms(phone, "RUMBU: " + tip)
        return end(tip)

    # 5. Voice help line
    if choice == "5":
        return end(t("voice_help", lang, number=os.environ.get("AT_VOICE_NUMBER", "+234 RUMBU")))

    # 6. Language
    if choice == "6":
        if n == 1:
            return con(t("choose_lang", lang))
        new = {"1": "ha", "2": "en"}.get(parts[1])
        if not new:
            return bad
        db.set_lang(phone, new)
        return end(t("lang_saved", new))

    return bad
