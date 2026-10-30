"""End-to-end tests of every channel in dry-run mode. Run: python -m pytest -q"""
import os
import tempfile

os.environ["RUMBU_DB"] = tempfile.mktemp(suffix=".db")
os.environ["SEED_DEMO"] = "1"
os.environ.pop("AT_API_KEY", None)

import app as rumbu_app  # noqa: E402
from rumbu import db, services  # noqa: E402

client = rumbu_app.app.test_client()
PHONE = "08031112222"


def dial(text, phone=PHONE):
    r = client.post("/ussd", data={"sessionId": "t", "serviceCode": "*384#", "phoneNumber": phone, "text": text})
    return r.get_data(as_text=True)


def sms_to(phone):
    return [m["body"] for m in db.q("SELECT body FROM messages WHERE phone=? AND channel='sms' ORDER BY id",
                                     (db.normalize_phone(phone),))]


def test_registration():
    assert dial("").startswith("CON Barka da zuwa RUMBU")
    assert "sunanka" in dial("1")
    assert "Bichi" in dial("1*Sani")
    assert dial("1*Sani*4").startswith("END Na gode Sani")
    f = db.get_farmer(PHONE)
    assert f["lga"] == "bichi" and f["lang"] == "ha" and f["phone"] == "+2348031112222"
    assert any("Barka Sani" in m for m in sms_to(PHONE))


def test_main_menu_and_prices():
    assert "Farashin kasuwa" in dial("")
    out = dial("1*1")
    assert out.startswith("END Masara: N48,000") and "tashi" in out
    assert "sauka" in dial("1*7")  # tomato price falling -> sell soon


def test_report_pays_airtime_once_a_day():
    out = dial("3*1*2*5")
    assert "katin N100" in out
    assert any("Shanya" in m for m in sms_to(PHONE))
    assert db.q("SELECT COUNT(*) n FROM messages WHERE phone='+2348031112222' AND channel='airtime'", one=True)["n"] == 1
    out2 = dial("3*1*1*2")
    assert "katin" not in out2  # no second reward the same day


def test_sell_matches_buyer():
    out = dial("2*1*30*0")  # maize, 30 bags, market price 48,000 <= buyer max 50,000
    assert "An samu mai saye" in out
    assert any("Dawanau Grains" in m for m in sms_to(PHONE))
    assert any("Sani" in m for m in sms_to("+2348090000001"))


def test_sell_too_expensive_stays_open():
    out = dial("2*2*5*90000")
    assert "An saka" in out and "An samu" not in out


def test_storage_and_language():
    assert "PICS" in dial("4*5")
    assert dial("6*2") == "END Language changed to English."
    assert "Market prices" in dial("")
    assert dial("9").startswith("END Invalid")


def test_sms_commands():
    p = "+2348035550000"
    client.post("/sms/incoming", data={"from": p, "text": "PRICE MAIZE"})
    assert any("Maize: N48,000" in m for m in sms_to(p))
    client.post("/sms/incoming", data={"from": p, "text": "MATSALA masarata ta jike da ruwa"})
    r = db.q("SELECT * FROM reports WHERE phone=? ORDER BY id DESC", (p,), one=True)
    assert r["problem"] == "moisture" and r["crop"] == "maize"
    client.post("/sms/incoming", data={"from": p, "text": "BUY SORGHUM 10 47000"})
    assert db.q("SELECT * FROM buyers WHERE phone=?", (p,), one=True)["crop"] == "sorghum"


def test_classifier():
    assert services.classify("weevils in my beans") == ("insects", "cowpea")
    assert services.classify("beraye suna cin gyada") == ("rodents", "groundnut")


def test_voice_flow():
    base = {"sessionId": "v1", "callerNumber": PHONE, "isActive": "1"}
    x = client.post("/voice", data=base).get_data(as_text=True)
    assert "<GetDigits" in x and "voice?step=menu" in x
    x = client.post("/voice?step=menu", data={**base, "dtmfDigits": "1"}).get_data(as_text=True)
    assert "step=storage" in x
    x = client.post("/voice?step=storage", data={**base, "dtmfDigits": "5"}).get_data(as_text=True)
    assert "PICS" in x
    x = client.post("/voice?step=menu", data={**base, "dtmfDigits": "2"}).get_data(as_text=True)
    assert "<Record" in x
    client.post("/voice?step=recorded", data={**base, "recordingUrl": "https://example.com/r.mp3"})
    r = db.q("SELECT * FROM reports WHERE channel='voice' ORDER BY id DESC", one=True)
    assert r["recording_url"] == "https://example.com/r.mp3"
    assert client.post("/voice", data={**base, "isActive": "0"}).status_code == 200


def csrf(c):
    c.get("/")
    with c.session_transaction() as sess:
        return sess["csrf"]


def logged_in(email):
    c = rumbu_app.app.test_client()
    r = c.post("/login", data={"email": email, "password": "rumbu2026", "csrf": csrf(c)})
    assert r.status_code == 302
    return c


def test_public_pages():
    assert b"Rumbu a wayarka" in client.get("/").data
    assert b"Phone simulator" in client.get("/simulator").data
    assert client.get("/login").status_code == 200
    assert client.get("/admin").status_code == 302  # needs login
    assert client.get("/api/public-stats").json["farmers"] >= 7
    assert client.get("/api/feed").status_code == 302  # phone numbers are admin-only


def test_login_redirects_by_role():
    c = rumbu_app.app.test_client()
    token = csrf(c)
    assert c.post("/login", data={"email": "admin@rumbu.ng", "password": "wrong", "csrf": token}).status_code == 200
    for email, home in [("admin@rumbu.ng", "/admin"), ("partner@rumbu.ng", "/partner"), ("buyer@rumbu.ng", "/buyer")]:
        c = rumbu_app.app.test_client()
        r = c.post("/login", data={"email": email, "password": "rumbu2026", "csrf": csrf(c)})
        assert r.headers["Location"].endswith(home)


def test_csrf_required():
    c = logged_in("admin@rumbu.ng")
    assert c.post("/admin/price", data={"crop": "maize", "price": "1"}).status_code == 400


def test_roles_are_separated():
    buyer = logged_in("buyer@rumbu.ng")
    assert buyer.get("/admin").status_code == 403
    assert buyer.get("/partner").status_code == 403
    partner = logged_in("partner@rumbu.ng")
    assert partner.get("/buyer").status_code == 403
    assert partner.get("/partner").status_code == 200
    csv_text = partner.get("/partner/export.csv").get_data(as_text=True)
    assert csv_text.startswith("date,lga,crop") and "+234" not in csv_text  # anonymised
    admin = logged_in("admin@rumbu.ng")
    for page in ("/admin", "/admin/users", "/buyer", "/partner"):
        assert admin.get(page).status_code == 200


def test_admin_actions():
    admin = logged_in("admin@rumbu.ng")
    t = csrf(admin)
    assert admin.post("/admin/alert", data={"lga": "bichi", "when": "gobe", "csrf": t}).status_code == 302
    assert any("ruwan sama" in m or "Rain expected" in m for m in sms_to(PHONE))
    admin.post("/admin/price", data={"crop": "millet", "price": "52000", "csrf": t})
    assert db.get_price("millet")["price"] == 52000
    r = admin.post("/admin/users", data={"role": "partner", "name": "NGO", "org": "Food NGO", "email": "ngo@example.org",
                                         "password": "longenough", "csrf": t})
    assert r.status_code == 302 and db.q("SELECT role FROM users WHERE email='ngo@example.org'", one=True)["role"] == "partner"


def test_buyer_signup_request_and_buy():
    c = rumbu_app.app.test_client()
    r = c.post("/signup", data={"name": "Bala", "org": "Bala Grains", "phone": "08061234567",
                                "email": "bala@example.org", "password": "longenough", "csrf": csrf(c)})
    assert r.headers["Location"].endswith("/buyer")
    t = csrf(c)
    page = c.get("/buyer").get_data(as_text=True)
    assert "Listed by farmers today" in page
    listing = db.q("SELECT * FROM listings WHERE status='open' AND crop='rice'", one=True)
    c.post(f"/buyer/buy/{listing['id']}", data={"csrf": t})
    assert db.q("SELECT status FROM listings WHERE id=?", (listing["id"],), one=True)["status"] == "matched"
    assert any("Bala Grains" in m for m in sms_to(listing["phone"]))
    assert "+2348030000006" in c.get("/buyer").get_data(as_text=True)  # farmer's number now visible
    # a second buy of the same listing fails cleanly
    c.post(f"/buyer/buy/{listing['id']}", data={"csrf": t})
    assert db.q("SELECT COUNT(*) n FROM matches WHERE listing_id=?", (listing["id"],), one=True)["n"] == 1
    c.post("/buyer/request", data={"crop": "millet", "bags": "10", "max_price": "60000", "csrf": t})
    assert db.q("SELECT * FROM matches WHERE crop='millet'", one=True) is not None


def _wav(seconds=0.5, rate=16000):
    import io, struct, wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(struct.pack("<h", 1000) * int(seconds * rate))
    buf.seek(0)
    return buf


def test_voice_studio_and_playback(tmp_path, monkeypatch):
    from rumbu import voice
    monkeypatch.setattr(voice, "AUDIO_DIR", str(tmp_path))
    admin = logged_in("admin@rumbu.ng")
    t = csrf(admin)
    assert b"Voice prompts" in admin.get("/admin/voice").data
    # bad upload is rejected
    r = admin.post("/admin/voice/ha/welcome", data={"csrf": t, "audio": (io_bytes(b"not audio"), "x.wav")},
                   content_type="multipart/form-data")
    assert r.status_code == 400
    r = admin.post("/admin/voice/ha/welcome", data={"csrf": t, "audio": (_wav(), "p.wav")},
                   content_type="multipart/form-data")
    assert r.status_code == 200 and (tmp_path / "ha_welcome.wav").exists()
    assert admin.post("/admin/voice/ha/../../x", data={"csrf": t}).status_code == 404
    # the call now plays the recording instead of reading text
    x = client.post("/voice", data={"sessionId": "v9", "callerNumber": "+2348099999999", "isActive": "1"}).get_data(as_text=True)
    assert '<Play url="' in x and "static/audio/ha_welcome.wav" in x
    # storage advice plays the crop's own tip prompt; unrecorded ones fall back to <Say>
    x = client.post("/voice?step=storage", data={"callerNumber": "+2348099999999", "isActive": "1", "dtmfDigits": "1"}).get_data(as_text=True)
    assert "<Say>" in x and "Masara" in x
    assert admin.get("/admin/voice.zip").headers["Content-Type"] == "application/zip"
    admin.post("/admin/voice/ha/welcome/delete", data={"csrf": t})
    assert not (tmp_path / "ha_welcome.wav").exists()


def test_simulator_voice_note_reaches_admin():
    c = rumbu_app.app.test_client()
    t = csrf(c)
    r = c.post("/simulator/recording", data={"csrf": t, "audio": (_wav(), "n.wav")}, content_type="multipart/form-data")
    url = r.json["recordingUrl"]
    assert "/static/recordings/sim-" in url
    c.post("/voice?step=recorded", data={"callerNumber": PHONE, "isActive": "1", "recordingUrl": url})
    admin = logged_in("admin@rumbu.ng")
    assert url in admin.get("/admin").get_data(as_text=True)


def io_bytes(b):
    import io
    return io.BytesIO(b)
