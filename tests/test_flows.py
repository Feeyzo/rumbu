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


def test_dashboard_pages():
    assert b"early-warning" in client.get("/").data
    assert b"simulator" in client.get("/simulator").data.lower()
    assert client.get("/api/feed").json["stats"]["farmers"] >= 7
    r = client.post("/admin/alert", data={"lga": "bichi", "when": "gobe"})
    assert r.status_code == 302
    assert any("ruwan sama" in m for m in sms_to(PHONE)) or any("Rain expected" in m for m in sms_to(PHONE))
