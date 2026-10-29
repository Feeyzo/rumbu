import os

from flask import Flask, Response, jsonify, redirect, render_template, request, url_for

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from rumbu import at, db, seed, services, sms, ussd, voice, weather
from rumbu.content import CROPS, LGAS, PROBLEMS, crop_name, lga_name, problem_name

app = Flask(__name__)

db.init()
seed.seed_prices()
if os.environ.get("SEED_DEMO", "1") == "1":
    seed.seed_demo()


def public_base():
    return (os.environ.get("PUBLIC_URL") or request.host_url).rstrip("/") + "/"


# ---------------- Africa's Talking callbacks ----------------
@app.post("/ussd")
def ussd_callback():
    reply = ussd.handle(request.values.get("phoneNumber", ""), request.values.get("text", ""))
    return Response(reply, mimetype="text/plain")


@app.post("/sms/incoming")
def sms_callback():
    sms.handle(request.values.get("from", ""), request.values.get("text", ""))
    return "", 200


@app.post("/voice")
def voice_callback():
    xml = voice.handle(request.values, request.args.get("step"), public_base())
    return Response(xml, mimetype="application/xml")


@app.post("/events")  # delivery reports / airtime status callbacks
def events_callback():
    return "", 200


# ---------------- Dashboard ----------------
def stats():
    one = lambda sql: db.q(sql, one=True)["n"] or 0
    return {
        "farmers": one("SELECT COUNT(*) n FROM farmers"),
        "reports": one("SELECT COUNT(*) n FROM reports"),
        "bags_at_risk": one("SELECT SUM(bags) n FROM reports"),
        "bags_listed": one("SELECT SUM(bags) n FROM listings WHERE status='open'"),
        "matches": one("SELECT COUNT(*) n FROM matches"),
        "trade_value": one("SELECT SUM(bags*price) n FROM matches"),
        "airtime": one("SELECT SUM(reward) n FROM reports"),
        "sms": one("SELECT COUNT(*) n FROM messages WHERE direction='out' AND channel='sms'"),
    }


@app.get("/")
def dashboard():
    heat = {}
    for r in db.q("SELECT lga, problem, COUNT(*) n FROM reports GROUP BY lga, problem"):
        heat.setdefault(r["lga"], {})[r["problem"]] = r["n"]
    maxheat = max([n for row in heat.values() for n in row.values()] or [1])
    by_crop = db.q("SELECT crop, SUM(bags) bags, COUNT(*) n FROM reports WHERE crop IS NOT NULL "
                   "GROUP BY crop ORDER BY bags DESC")
    reports = db.q("SELECT r.*, f.name FROM reports r LEFT JOIN farmers f ON f.phone=r.phone "
                   "ORDER BY r.id DESC LIMIT 25")
    listings = db.q("SELECT l.*, f.name, f.lga FROM listings l LEFT JOIN farmers f ON f.phone=l.phone "
                    "ORDER BY l.id DESC LIMIT 20")
    buyers = db.q("SELECT * FROM buyers ORDER BY id DESC LIMIT 20")
    matches = db.q("SELECT m.*, b.name buyer, f.name farmer FROM matches m "
                   "LEFT JOIN buyers b ON b.id=m.buyer_id LEFT JOIN listings l ON l.id=m.listing_id "
                   "LEFT JOIN farmers f ON f.phone=l.phone ORDER BY m.id DESC LIMIT 20")
    prices = db.q("SELECT * FROM prices")
    return render_template(
        "dashboard.html", s=stats(), heat=heat, maxheat=maxheat, by_crop=by_crop, reports=reports,
        listings=listings, buyers=buyers, matches=matches, prices=prices, LGAS=LGAS, PROBLEMS=PROBLEMS,
        CROPS=CROPS, crop_name=crop_name, lga_name=lga_name, problem_name=problem_name,
        live=at.live(), flash=request.args.get("msg"),
    )


@app.get("/api/feed")
def api_feed():
    msgs = db.q("SELECT * FROM messages ORDER BY id DESC LIMIT 15")
    return jsonify(stats=stats(), messages=msgs)


@app.post("/admin/alert")
def admin_alert():
    lga = request.form["lga"]
    when = request.form.get("when") or "gobe / tomorrow"
    n = weather.alert_lga(lga, when)
    return redirect(url_for("dashboard", msg=f"Rain alert sent to {n} farmers in {lga_name(lga)}"))


@app.post("/admin/weather")
def admin_weather():
    results = weather.check_all()
    sent = sum(r[3] for r in results)
    summary = "; ".join(f"{r[0]} {r[2]}%" for r in results)
    return redirect(url_for("dashboard", msg=f"Forecast checked ({summary}). Alerts sent: {sent}"))


@app.post("/admin/buyer")
def admin_buyer():
    f = request.form
    _, matched = services.create_buyer(f["name"], f["phone"], f["crop"], int(f["bags"]), int(f["max_price"]))
    return redirect(url_for("dashboard", msg=f"Buyer saved. Matched with {matched} listing(s)."))


@app.post("/admin/price")
def admin_price():
    db.set_price(request.form["crop"], int(request.form["price"]))
    return redirect(url_for("dashboard", msg="Price updated"))


@app.post("/admin/reply")
def admin_reply():
    r = db.q("SELECT * FROM reports WHERE id=?", (int(request.form["report_id"]),), one=True)
    if r:
        at.send_sms(r["phone"], "RUMBU: " + request.form["message"])
        db.ex("UPDATE reports SET status='advised' WHERE id=?", (r["id"],))
    return redirect(url_for("dashboard", msg="Advice sent by SMS"))


# ---------------- Phone simulator (for demos without a live shortcode) ----------------
@app.get("/simulator")
def simulator():
    return render_template("simulator.html")


@app.get("/api/messages")
def api_messages():
    phone = db.normalize_phone(request.args.get("phone", ""))
    return jsonify(db.q("SELECT * FROM messages WHERE phone=? AND direction='out' ORDER BY id DESC LIMIT 20",
                        (phone,)))


@app.get("/health")
def health():
    return {"ok": True, "live": at.live()}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
