import csv
import io
import os
import secrets
from datetime import datetime, timedelta, timezone

from flask import (Flask, Response, abort, flash, g, jsonify, redirect, render_template, request,
                   session, url_for)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from rumbu import at, auth, db, seed, services, sms, ussd, voice, weather
from rumbu.content import CROPS, LGAS, PROBLEMS, crop_name, lga_name, problem_name

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_HTTPONLY=True,
                  PERMANENT_SESSION_LIFETIME=timedelta(days=7))

DEMO = os.environ.get("SEED_DEMO", "1") == "1"
SIMULATOR = os.environ.get("SIMULATOR", "1") == "1"
USSD_CODE = os.environ.get("USSD_CODE", "*384*7867#")

db.init()
seed.seed_prices()
seed.seed_admin_from_env()
if DEMO:
    seed.seed_demo()
    seed.seed_demo_users()

# Africa's Talking posts to these; they can't carry our CSRF token.
AT_PATHS = {"/ussd", "/sms/incoming", "/voice", "/events"}


@app.before_request
def before():
    auth.load_user()
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(24)
    if request.method == "POST" and request.path not in AT_PATHS:
        if request.form.get("csrf") != session["csrf"]:
            abort(400, "Form expired. Go back, refresh the page and try again.")


@app.context_processor
def inject():
    return dict(user=g.get("user"), csrf=session.get("csrf"), live=at.live(), demo=DEMO,
                simulator=SIMULATOR, ussd_code=USSD_CODE, CROPS=CROPS, LGAS=LGAS, PROBLEMS=PROBLEMS,
                crop_name=crop_name, lga_name=lga_name, problem_name=problem_name)


@app.template_filter("naira")
def naira(n):
    return "₦{:,}".format(int(n or 0))


def public_base():
    return (os.environ.get("PUBLIC_URL") or request.host_url).rstrip("/") + "/"


# ================= Africa's Talking callbacks =================
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


# ================= Shared data =================
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
        "lgas": one("SELECT COUNT(DISTINCT lga) n FROM farmers"),
    }


def insights():
    heat = {}
    for r in db.q("SELECT lga, problem, COUNT(*) n FROM reports GROUP BY lga, problem"):
        heat.setdefault(r["lga"], {})[r["problem"]] = r["n"]
    maxheat = max([n for row in heat.values() for n in row.values()] or [1])
    by_crop = db.q("SELECT crop, SUM(bags) bags, COUNT(*) n FROM reports WHERE crop IS NOT NULL "
                   "GROUP BY crop ORDER BY bags DESC")
    by_channel = db.q("SELECT channel, COUNT(*) n FROM reports GROUP BY channel ORDER BY n DESC")
    today = datetime.now(timezone.utc).date()
    weeks = []
    for w in range(3, -1, -1):
        start = today - timedelta(days=7 * w + 6)
        end = today - timedelta(days=7 * w)
        n = db.q("SELECT COUNT(*) n, COALESCE(SUM(bags),0) b FROM reports WHERE substr(created_at,1,10) BETWEEN ? AND ?",
                 (start.isoformat(), end.isoformat()), one=True)
        weeks.append({"label": start.strftime("%d %b"), "n": n["n"], "bags": n["b"]})
    prices = db.q("SELECT * FROM prices")
    for p in prices:
        p["pct"] = round((p["price"] - p["prev_price"]) * 100 / p["prev_price"]) if p["prev_price"] else 0
    hotspots = sorted(((lga, sum(v.values())) for lga, v in heat.items()), key=lambda x: -x[1])[:3]
    return dict(heat=heat, maxheat=maxheat, by_crop=by_crop, by_channel=by_channel, weeks=weeks,
                prices=prices, hotspots=hotspots)


# ================= Public pages =================
@app.get("/")
def landing():
    from rumbu.content import crop_menu, problem_menu, t
    # The hero phone plays the real Hausa menus a farmer sees.
    screens = [
        {"key": "", "text": t("main_menu", "ha")},
        {"key": "1", "text": t("choose_crop", "ha") + "\n" + crop_menu("ha")},
        {"key": "1", "text": services.price_text("maize", "ha")},
        {"key": "", "text": t("main_menu", "ha")},
        {"key": "3", "text": t("choose_crop", "ha") + "\n" + crop_menu("ha")},
        {"key": "1", "text": t("choose_problem", "ha") + "\n" + problem_menu("ha")},
        {"key": "2", "text": t("ask_bags_affected", "ha")},
        {"key": "6", "text": t("report_thanks", "ha", reward=services.REWARD)},
    ]
    return render_template("landing.html", s=stats(), prices=insights()["prices"], screens=screens)


@app.get("/api/public-stats")
def public_stats():
    s = stats()
    return jsonify({k: s[k] for k in ("farmers", "reports", "bags_at_risk", "matches", "trade_value", "airtime")})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = auth.authenticate(request.form.get("email"), request.form.get("password"))
        if u:
            auth.login(u)
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else auth.home_for(u))
        flash("That email and password don't match an account.")
    return render_template("login.html", demo_users=seed.DEMO_USERS if DEMO else [],
                           demo_password=seed.DEMO_PASSWORD)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        f = request.form
        if len(f.get("password", "")) < 8:
            flash("Use a password of at least 8 characters.")
        else:
            try:
                uid = auth.create_user(f["email"], f["password"], f["name"], "buyer", f.get("org", ""), f["phone"])
                auth.login({"id": uid})
                flash("Account created. Post what you want to buy and we'll match you with farmers.")
                return redirect(url_for("buyer_portal"))
            except ValueError as e:
                flash(str(e))
    return render_template("signup.html")


@app.post("/logout")
def logout():
    auth.logout()
    return redirect(url_for("landing"))


@app.get("/app")
def app_home():
    if not g.user:
        return redirect(url_for("login"))
    return redirect(auth.home_for(g.user))


# ================= Buyer portal =================
@app.get("/buyer")
@auth.require("buyer")
def buyer_portal():
    uid = g.user["id"]
    requests_ = db.q("SELECT * FROM buyers WHERE user_id=? ORDER BY id DESC", (uid,))
    matches = db.q(
        "SELECT m.*, f.name farmer, f.phone farmer_phone, f.lga FROM matches m "
        "JOIN buyers b ON b.id=m.buyer_id LEFT JOIN listings l ON l.id=m.listing_id "
        "LEFT JOIN farmers f ON f.phone=l.phone WHERE b.user_id=? ORDER BY m.id DESC", (uid,))
    listings = db.q(
        "SELECT l.*, f.name farmer, f.lga FROM listings l LEFT JOIN farmers f ON f.phone=l.phone "
        "WHERE l.status='open' ORDER BY l.id DESC")
    for l in listings:
        l["price"] = l["ask_price"] or (db.get_price(l["crop"]) or {}).get("price", 0)
    spent = sum(m["bags"] * m["price"] for m in matches)
    return render_template("buyer.html", requests=requests_, matches=matches, listings=listings, spent=spent,
                           prices=insights()["prices"])


@app.post("/buyer/request")
@auth.require("buyer")
def buyer_request():
    f = request.form
    try:
        bags, max_price = int(f["bags"]), int(f["max_price"])
        assert bags > 0 and max_price > 0 and f["crop"] in {c[0] for c in CROPS}
    except (ValueError, KeyError, AssertionError):
        flash("Enter a crop, the number of bags and your maximum price per bag.")
        return redirect(url_for("buyer_portal"))
    name = g.user["org"] or g.user["name"]
    _, matched = services.create_buyer(name, g.user["phone"], f["crop"], bags, max_price, user_id=g.user["id"])
    flash(f"Request posted. Matched with {matched} farmer listing(s) so far; farmers get an SMS with your number."
          if matched else "Request posted. We'll SMS you as soon as a farmer lists matching produce.")
    return redirect(url_for("buyer_portal"))


@app.post("/buyer/buy/<int:listing_id>")
@auth.require("buyer")
def buyer_buy(listing_id):
    ok = services.buy_listing(listing_id, g.user)
    flash("Bought. The farmer has been sent your number by SMS; their number is in your matches."
          if ok else "That listing was just taken by another buyer.")
    return redirect(url_for("buyer_portal"))


# ================= Partner insights =================
@app.get("/partner")
@auth.require("partner")
def partner_insights():
    return render_template("partner.html", s=stats(), **insights())


@app.get("/partner/export.csv")
@auth.require("partner")
def partner_export():
    rows = db.q("SELECT created_at, lga, crop, problem, bags, channel FROM reports ORDER BY created_at")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "lga", "crop", "problem", "bags_affected", "channel"])
    for r in rows:
        w.writerow([r["created_at"][:10], lga_name(r["lga"]), crop_name(r["crop"], "en") if r["crop"] else "",
                    problem_name(r["problem"], "en") if r["problem"] != "voice_note" else "Voice note",
                    r["bags"], r["channel"]])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=rumbu-loss-reports.csv"})


# ================= Admin console =================
@app.get("/admin")
@auth.require("admin")
def admin_console():
    reports = db.q("SELECT r.*, f.name FROM reports r LEFT JOIN farmers f ON f.phone=r.phone "
                   "ORDER BY (r.status='new' AND r.problem IN ('voice_note','other')) DESC, r.id DESC LIMIT 40")
    listings = db.q("SELECT l.*, f.name, f.lga FROM listings l LEFT JOIN farmers f ON f.phone=l.phone "
                    "ORDER BY l.id DESC LIMIT 20")
    buyers = db.q("SELECT * FROM buyers ORDER BY id DESC LIMIT 20")
    matches = db.q("SELECT m.*, b.name buyer, f.name farmer FROM matches m "
                   "LEFT JOIN buyers b ON b.id=m.buyer_id LEFT JOIN listings l ON l.id=m.listing_id "
                   "LEFT JOIN farmers f ON f.phone=l.phone ORDER BY m.id DESC LIMIT 20")
    pending = sum(1 for r in reports if r["status"] == "new" and r["problem"] in ("voice_note", "other"))
    return render_template("admin.html", s=stats(), reports=reports, listings=listings, buyers=buyers,
                           matches=matches, pending=pending, **insights())


@app.get("/api/feed")
@auth.require("admin")
def api_feed():
    msgs = db.q("SELECT * FROM messages ORDER BY id DESC LIMIT 15")
    return jsonify(stats=stats(), messages=msgs)


@app.post("/admin/alert")
@auth.require("admin")
def admin_alert():
    lga = request.form["lga"]
    n = weather.alert_lga(lga, request.form.get("when") or "gobe / tomorrow")
    flash(f"Rain alert sent to {n} farmers in {lga_name(lga)}.")
    return redirect(url_for("admin_console"))


@app.post("/admin/weather")
@auth.require("admin")
def admin_weather():
    results = weather.check_all()
    sent = sum(r[3] for r in results)
    summary = "; ".join(f"{r[0]} {r[2]}%" for r in results)
    flash(f"Forecast checked ({summary}). Alerts sent: {sent}.")
    return redirect(url_for("admin_console"))


@app.post("/admin/buyer")
@auth.require("admin")
def admin_buyer():
    f = request.form
    _, matched = services.create_buyer(f["name"], f["phone"], f["crop"], int(f["bags"]), int(f["max_price"]))
    flash(f"Buyer saved. Matched with {matched} listing(s).")
    return redirect(url_for("admin_console"))


@app.post("/admin/price")
@auth.require("admin")
def admin_price():
    db.set_price(request.form["crop"], int(request.form["price"]))
    flash(f"{crop_name(request.form['crop'], 'en')} price updated.")
    return redirect(url_for("admin_console"))


@app.post("/admin/reply")
@auth.require("admin")
def admin_reply():
    r = db.q("SELECT * FROM reports WHERE id=?", (int(request.form["report_id"]),), one=True)
    if r:
        at.send_sms(r["phone"], "RUMBU: " + request.form["message"])
        db.ex("UPDATE reports SET status='advised' WHERE id=?", (r["id"],))
        flash("Advice sent by SMS.")
    return redirect(url_for("admin_console"))


@app.route("/admin/users", methods=["GET", "POST"])
@auth.require("admin")
def admin_users():
    if request.method == "POST":
        f = request.form
        try:
            if len(f.get("password", "")) < 8:
                raise ValueError("Use a temporary password of at least 8 characters.")
            auth.create_user(f["email"], f["password"], f["name"], f["role"], f.get("org", ""), f.get("phone", ""))
            flash(f"{f['role'].title()} account created for {f['email']}. Share the password with them directly.")
        except ValueError as e:
            flash(str(e))
        return redirect(url_for("admin_users"))
    users = db.q("SELECT id, email, name, org, role, created_at FROM users ORDER BY role, id")
    farmers = db.q("SELECT f.*, (SELECT COUNT(*) FROM reports r WHERE r.phone=f.phone) reports "
                   "FROM farmers f ORDER BY created_at DESC")
    return render_template("users.html", users=users, farmers=farmers)


# ================= Phone simulator (demo) =================
@app.get("/simulator")
def simulator():
    if not SIMULATOR:
        abort(404)
    return render_template("simulator.html")


@app.get("/api/messages")
def api_messages():
    if not SIMULATOR:
        abort(404)
    phone = db.normalize_phone(request.args.get("phone", ""))
    return jsonify(db.q("SELECT * FROM messages WHERE phone=? AND direction='out' ORDER BY id DESC LIMIT 20",
                        (phone,)))


@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", title="Not available for your account",
                           message="This page belongs to a different type of account."), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", title="Page not found",
                           message="Check the address, or go back to the home page."), 404


@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", title="Couldn't submit that form", message=e.description), 400


@app.get("/health")
def health():
    return {"ok": True, "live": at.live()}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
