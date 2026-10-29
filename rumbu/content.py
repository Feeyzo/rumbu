"""All farmer-facing text and reference data.

Hausa strings avoid the hooked letters (b' d' k') on purpose: USSD and SMS use
the GSM-7 alphabet, and special characters either break the menu or double the
SMS cost. Have a native speaker review wording before a real launch.
"""

# key, Hausa name, English name, unit
CROPS = [
    ("maize", "Masara", "Maize", "bag"),
    ("sorghum", "Dawa", "Sorghum", "bag"),
    ("millet", "Gero", "Millet", "bag"),
    ("rice", "Shinkafa", "Rice (paddy)", "bag"),
    ("cowpea", "Wake", "Beans (cowpea)", "bag"),
    ("groundnut", "Gyada", "Groundnut", "bag"),
    ("tomato", "Tumatir", "Tomato", "basket"),
]

# key, display name, latitude, longitude (approximate LGA centres, Kano State)
LGAS = [
    ("municipal", "Kano Municipal", 12.00, 8.52),
    ("dawakin_tofa", "Dawakin Tofa", 12.10, 8.33),
    ("wudil", "Wudil", 11.81, 8.84),
    ("bichi", "Bichi", 12.23, 8.24),
    ("rano", "Rano", 11.55, 8.58),
    ("gaya", "Gaya", 11.86, 9.00),
    ("kura", "Kura", 11.77, 8.43),
    ("tudun_wada", "Tudun Wada", 11.25, 8.40),
]

# key, Hausa label, English label
PROBLEMS = [
    ("insects", "Kwari", "Insects / weevils"),
    ("moisture", "Danshi / fumfuna", "Moisture / mould"),
    ("rodents", "Beraye", "Rats / rodents"),
    ("rot", "Rubewa", "Rotting"),
    ("other", "Wani abu", "Something else"),
]

ADVICE = {
    "insects": {
        "ha": "Shanya hatsin a rana ka tankade shi. Ajiye a buhun PICS (leda uku) a rufe sosai. Kada ka hada sabo da tsoho.",
        "en": "Sun-dry and sieve the grain. Store in PICS triple-layer bags, sealed tight. Don't mix new and old stock.",
    },
    "moisture": {
        "ha": "Shanya shi a kan tabarma ko leda, ba a kasa ba, har ya bushe kalau. Ajiye buhuna a kan katako, nesa da bango.",
        "en": "Dry on a tarpaulin, not bare ground, until fully dry. Stack bags on wooden pallets, away from walls.",
    },
    "rodents": {
        "ha": "Daga buhuna daga kasa, toshe ramukan bango, kuma kiyaye wurin ajiya da tsabta.",
        "en": "Raise bags off the floor, seal holes in the walls, and keep the store clean.",
    },
    "rot": {
        "ha": "Ware wanda ya rube nan take don kada ya bata saura. Sayar da mai kyau da wuri ko ka shanya shi.",
        "en": "Remove rotten produce at once so it doesn't spread. Sell good stock early or dry it.",
    },
    "other": {
        "ha": "Jami'in gona zai kira ka nan ba da jimawa ba.",
        "en": "An extension officer will call you shortly.",
    },
}

STORAGE_TIPS = {
    "maize": {
        "ha": "Masara: shanya ta sosai kafin ajiya. Ajiye a buhun PICS a kan katako, nesa da bango.",
        "en": "Maize: dry well before storing (about 13% moisture). Use PICS bags on pallets, away from walls.",
    },
    "sorghum": {
        "ha": "Dawa: shanya ta, ka tankade, ka ajiye a buhun PICS a wuri mai iska.",
        "en": "Sorghum: dry, sieve, and store in PICS bags in an airy store.",
    },
    "millet": {
        "ha": "Gero: ajiye shi a buhun PICS ko rumbu mai rufi. Duba shi kowane mako.",
        "en": "Millet: store in PICS bags or a covered granary. Check it every week.",
    },
    "rice": {
        "ha": "Shinkafa: shanya ta sosai, ajiye a wuri mai iska, kada ta taba kasa.",
        "en": "Rice paddy: dry well, store in an airy place, never on bare ground.",
    },
    "cowpea": {
        "ha": "Wake: ajiye a buhun PICS leda uku, a rufe sosai. Yana kashe kwari ba tare da magani ba.",
        "en": "Beans: PICS triple-layer bags, sealed tight. This kills weevils with no chemicals.",
    },
    "groundnut": {
        "ha": "Gyada: shanya ta sosai don hana fumfuna. Kada ka ajiye ta da danshi.",
        "en": "Groundnut: dry fully to prevent mould and aflatoxin. Never store it damp.",
    },
    "tomato": {
        "ha": "Tumatir: kada ka cika kwando. Sayar cikin kwana 3, ko ka shanya shi.",
        "en": "Tomato: don't overpack baskets. Sell within 3 days, or sun-dry it.",
    },
}

T = {
    "welcome_new": {
        "ha": "Barka da zuwa RUMBU!\nWelcome to RUMBU!\n1. Hausa\n2. English",
        "en": "Barka da zuwa RUMBU!\nWelcome to RUMBU!\n1. Hausa\n2. English",
    },
    "ask_name": {"ha": "Rubuta sunanka:", "en": "Enter your name:"},
    "ask_lga": {"ha": "Zabi karamar hukumarka:", "en": "Choose your LGA:"},
    "registered": {
        "ha": "Na gode {name}! An yi maka rajista a RUMBU. Sake danna lambar don farawa.",
        "en": "Thank you {name}! You are registered on RUMBU. Dial again to start.",
    },
    "welcome_sms": {
        "ha": "Barka {name}! Kana cikin RUMBU. Tura FARASHI MASARA don farashi, ko MATSALA da bayani don taimako.",
        "en": "Welcome {name}! You're on RUMBU. Text PRICE MAIZE for prices, or HELP with your problem for advice.",
    },
    "main_menu": {
        "ha": "RUMBU\n1. Farashin kasuwa\n2. Sayar da amfanin gona\n3. Rahoton matsala\n4. Shawarar ajiya\n5. Taimako ta murya\n6. Harshe",
        "en": "RUMBU\n1. Market prices\n2. Sell produce\n3. Report a problem\n4. Storage advice\n5. Voice help\n6. Language",
    },
    "choose_crop": {"ha": "Zabi amfanin gona:", "en": "Choose crop:"},
    "choose_problem": {"ha": "Mene ne matsalar?", "en": "What is the problem?"},
    "ask_bags": {"ha": "Buhu nawa?", "en": "How many bags?"},
    "ask_bags_affected": {"ha": "Buhu nawa abin ya shafa?", "en": "How many bags are affected?"},
    "ask_price": {
        "ha": "Farashi na buhu daya (N)?\n0 = farashin kasuwa",
        "en": "Price per bag (N)?\n0 = market price",
    },
    "price_line": {
        "ha": "{crop}: N{price:,} kowane {unit} a {market}.",
        "en": "{crop}: N{price:,} per {unit} at {market}.",
    },
    "price_up": {
        "ha": "Farashi ya tashi {pct}% a wata daya. Idan ajiyarka tana da kyau, jira kafin ka sayar.",
        "en": "Up {pct}% this month. If your storage is good, waiting may pay.",
    },
    "price_down": {
        "ha": "Farashi ya sauka {pct}% a wata daya. Yi la'akari da sayarwa yanzu.",
        "en": "Down {pct}% this month. Consider selling soon.",
    },
    "price_flat": {"ha": "Farashi bai canza sosai ba.", "en": "Price is steady."},
    "listed": {
        "ha": "An saka buhu {bags} na {crop} a kasuwa. Za mu tura maka SMS idan an samu mai saye.",
        "en": "Listed {bags} bags of {crop}. We'll SMS you when a buyer is found.",
    },
    "listed_matched": {
        "ha": "An samu mai saye nan take! Duba SMS dinka.",
        "en": "Buyer found already! Check your SMS.",
    },
    "match_farmer": {
        "ha": "RUMBU: An samu mai saye! {buyer} zai saya buhu {bags} na {crop} a N{price:,}. Kira: {buyer_phone}",
        "en": "RUMBU: Buyer found! {buyer} will buy {bags} bags of {crop} at N{price:,}. Call: {buyer_phone}",
    },
    "report_thanks": {
        "ha": "Na gode! Za ka samu katin N{reward} da shawara ta SMS.",
        "en": "Thank you! You'll get N{reward} airtime and advice by SMS.",
    },
    "report_thanks_noreward": {
        "ha": "Na gode! Za ka samu shawara ta SMS.",
        "en": "Thank you! Advice is coming by SMS.",
    },
    "advice_sms": {"ha": "RUMBU shawara ({crop}): {advice}", "en": "RUMBU advice ({crop}): {advice}"},
    "voice_help": {
        "ha": "Kira {number} don jin shawara da Hausa, ko ka bar sakon murya game da matsalarka.",
        "en": "Call {number} to hear advice in Hausa, or leave a voice note about your problem.",
    },
    "choose_lang": {"ha": "1. Hausa\n2. English", "en": "1. Hausa\n2. English"},
    "lang_saved": {"ha": "An canza harshe zuwa Hausa.", "en": "Language changed to English."},
    "invalid": {"ha": "Zabin bai dace ba. Sake gwadawa.", "en": "Invalid choice. Please try again."},
    "sms_help": {
        "ha": "RUMBU: Tura\nFARASHI MASARA - farashi\nMATSALA + bayani - shawara\nSAYA MASARA 20 50000 - mai saye",
        "en": "RUMBU: Text\nPRICE MAIZE - prices\nHELP + your problem - advice\nBUY MAIZE 20 50000 - for buyers",
    },
    "buyer_saved": {
        "ha": "RUMBU: An karbi bukatarka ta buhu {bags} na {crop}. Za mu sanar da kai idan an samu manomi.",
        "en": "RUMBU: Request saved for {bags} bags of {crop}. We'll text you when a farmer matches.",
    },
    "match_buyer": {
        "ha": "RUMBU: Manomi {farmer} ({lga}) yana da buhu {bags} na {crop} a N{price:,}. Kira: {farmer_phone}",
        "en": "RUMBU: Farmer {farmer} ({lga}) has {bags} bags of {crop} at N{price:,}/bag. Call: {farmer_phone}",
    },
    "rain_alert": {
        "ha": "RUMBU: Ana sa ran ruwan sama a {lga} ({when}). Rufe amfanin gonarka da leda, ka daga buhuna daga kasa.",
        "en": "RUMBU: Rain expected in {lga} ({when}). Cover your harvest and raise bags off the ground.",
    },
}

UNIT_HA = {"bag": "buhu", "basket": "kwando"}


def t(key, lang, **kw):
    lang = lang if lang in ("ha", "en") else "ha"
    return T[key][lang].format(**kw)


def crop_name(key, lang):
    for k, ha, en, _ in CROPS:
        if k == key:
            return ha if lang == "ha" else en
    return key


def crop_unit(key, lang):
    for k, _, _, unit in CROPS:
        if k == key:
            return UNIT_HA[unit] if lang == "ha" else unit
    return "bag"


def lga_name(key):
    for k, name, _, _ in LGAS:
        if k == key:
            return name
    return key


def problem_name(key, lang):
    for k, ha, en in PROBLEMS:
        if k == key:
            return ha if lang == "ha" else en
    return key


def numbered(items):
    return "\n".join(f"{i}. {label}" for i, label in enumerate(items, 1))


def crop_menu(lang):
    return numbered([ha if lang == "ha" else en for _, ha, en, _ in CROPS])


def problem_menu(lang):
    return numbered([ha if lang == "ha" else en for _, ha, en in PROBLEMS])


def lga_menu():
    return numbered([name for _, name, _, _ in LGAS])


def find_crop(word):
    """Match a Hausa or English crop word, e.g. 'masara' or 'maize'."""
    w = (word or "").strip().lower()
    aliases = {"beans": "cowpea", "wake": "cowpea", "paddy": "rice", "tumatur": "tomato"}
    if w in aliases:
        return aliases[w]
    for k, ha, en, _ in CROPS:
        if w in (k, ha.lower(), en.lower().split(" ")[0]):
            return k
    # Hausa adds possessive endings: "masarata" = my maize, "gyadarsa" = his groundnut
    for k, ha, en, _ in CROPS:
        if len(w) > len(ha) and w.startswith(ha.lower()):
            return k
    return None
