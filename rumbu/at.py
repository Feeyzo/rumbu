"""Thin wrapper around the Africa's Talking SDK.

With AT_USERNAME and AT_API_KEY set, messages and airtime go out for real
(use username "sandbox" for the sandbox). Without them RUMBU runs in dry-run
mode: everything is logged to the dashboard but nothing leaves the server,
which is handy for demos without credit.

In live mode every send runs in a background thread, so a USSD screen is
answered straight away instead of waiting on SMS and airtime API calls
(Africa's Talking drops a USSD session that doesn't answer within seconds).
"""
import logging
import os
import threading

from . import db

log = logging.getLogger("rumbu.at")

_sms = None
_airtime = None
_lock = threading.Lock()


def live():
    return bool(os.environ.get("AT_USERNAME") and os.environ.get("AT_API_KEY"))


def _init():
    global _sms, _airtime
    with _lock:
        if _sms is None and live():
            import africastalking

            africastalking.initialize(os.environ["AT_USERNAME"], os.environ["AT_API_KEY"])
            _sms = africastalking.SMS
            _airtime = africastalking.Airtime


def _background(fn):
    t = threading.Thread(target=fn, daemon=True)
    t.start()
    return t


def _sms_status(resp):
    """'sent', or the first recipient's error. The API reports failures in the body, not as exceptions."""
    try:
        recips = resp["SMSMessageData"]["Recipients"]
        bad = [r for r in recips if r.get("status") not in ("Success", "Sent", "Queued")]
        if not recips:
            return "error: " + str(resp["SMSMessageData"].get("Message", "no recipients"))[:100]
        return f"error: {bad[0].get('status')}" if bad else "sent"
    except (KeyError, TypeError):
        return "sent"


def _airtime_status(resp):
    try:
        if resp.get("errorMessage") not in (None, "None"):
            return "error: " + str(resp["errorMessage"])[:100]
        r = (resp.get("responses") or [{}])[0]
        if r.get("status") == "Failed" or r.get("errorMessage") not in (None, "None"):
            return "error: " + str(r.get("errorMessage"))[:100]
        return "sent"
    except (AttributeError, TypeError):
        return "sent"


def send_sms(phones, message):
    if isinstance(phones, str):
        phones = [phones]
    phones = [db.normalize_phone(p) for p in phones if p]
    if not phones:
        return
    if not live():
        for p in phones:
            db.log_message("out", "sms", p, message, "dry-run")
        return

    def work():
        try:
            _init()
            sender = os.environ.get("AT_SENDER_ID") or None
            status = _sms_status(_sms.send(message, phones, sender_id=sender))
        except Exception as e:
            log.exception("SMS failed")
            status = f"error: {e}"[:120]
        for p in phones:
            db.log_message("out", "sms", p, message, status)

    _background(work)


def test_sms(phone, message="RUMBU test message. Idan ka ga wannan, SMS yana aiki."):
    """Send one SMS synchronously and return (status, raw response) for troubleshooting."""
    phone = db.normalize_phone(phone)
    if not live():
        return "dry-run", "AT_USERNAME and AT_API_KEY are not set on the server, so nothing is sent."
    try:
        _init()
        sender = os.environ.get("AT_SENDER_ID") or None
        resp = _sms.send(message, [phone], sender_id=sender)
        status = _sms_status(resp)
    except Exception as e:
        resp, status = repr(e), f"error: {e}"[:120]
    db.log_message("out", "sms", phone, message, status)
    return status, str(resp)[:600]


def send_airtime(phone, amount, currency="NGN", on_fail=None):
    """Send an airtime reward. `on_fail` runs if Africa's Talking rejects it."""
    phone = db.normalize_phone(phone)
    if not live():
        db.log_message("out", "airtime", phone, f"{currency} {amount} airtime reward", "dry-run")
        return "dry-run"

    def work():
        try:
            _init()
            status = _airtime_status(_airtime.send(phone_number=phone, amount=amount, currency_code=currency))
        except Exception as e:
            log.exception("Airtime failed")
            status = f"error: {e}"[:120]
        db.log_message("out", "airtime", phone, f"{currency} {amount} airtime reward", status)
        if status.startswith("error") and on_fail:
            on_fail()

    _background(work)
    return "queued"
