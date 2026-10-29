"""Rain alerts: checks Open-Meteo (free, no API key) for each LGA with farmers
and SMSes everyone there when rain is likely, so they cover drying produce."""

import requests

from . import at, db
from .content import LGAS, t

THRESHOLD = 60  # % chance of rain


def forecast(lat, lon):
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "daily": "precipitation_probability_max",
                "forecast_days": 3, "timezone": "Africa/Lagos"},
        timeout=10,
    )
    r.raise_for_status()
    d = r.json()["daily"]
    return list(zip(d["time"], d["precipitation_probability_max"]))


def alert_lga(lga_key, when):
    farmers = db.q("SELECT phone, lang FROM farmers WHERE lga=?", (lga_key,))
    name = next(n for k, n, _, _ in LGAS if k == lga_key)
    for f in farmers:
        at.send_sms(f["phone"], t("rain_alert", f["lang"], lga=name, when=when))
    return len(farmers)


def check_all():
    """Returns a list of (lga, day, chance, farmers alerted)."""
    results = []
    for key, name, lat, lon in LGAS:
        if not db.q("SELECT 1 FROM farmers WHERE lga=? LIMIT 1", (key,)):
            continue
        try:
            days = forecast(lat, lon)
        except Exception as e:
            results.append((name, "-", f"error: {e}", 0))
            continue
        rainy = [(d, p) for d, p in days if p is not None and p >= THRESHOLD]
        if rainy:
            day, chance = rainy[0]
            when = day
            results.append((name, day, chance, alert_lga(key, when)))
        else:
            results.append((name, days[0][0] if days else "-", max((p or 0) for _, p in days) if days else 0, 0))
    return results
