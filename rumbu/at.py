"""Thin wrapper around the Africa's Talking SDK.

With AT_USERNAME and AT_API_KEY set, messages and airtime go out for real
(use username "sandbox" for the sandbox). Without them RUMBU runs in dry-run
mode: everything is logged to the dashboard but nothing leaves the server,
which is handy for demos without credit.
"""
import logging
import os

from . import db

log = logging.getLogger("rumbu.at")

_sms = None
_airtime = None


def live():
    return bool(os.environ.get("AT_USERNAME") and os.environ.get("AT_API_KEY"))


def _init():
    global _sms, _airtime
    if _sms is None and live():
        import africastalking

        africastalking.initialize(os.environ["AT_USERNAME"], os.environ["AT_API_KEY"])
        _sms = africastalking.SMS
        _airtime = africastalking.Airtime


def send_sms(phones, message):
    if isinstance(phones, str):
        phones = [phones]
    phones = [db.normalize_phone(p) for p in phones if p]
    if not phones:
        return
    status = "dry-run"
    if live():
        try:
            _init()
            sender = os.environ.get("AT_SENDER_ID") or None
            _sms.send(message, phones, sender_id=sender)
            status = "sent"
        except Exception as e:  # keep the USSD session alive even if SMS fails
            log.exception("SMS failed")
            status = f"error: {e}"[:120]
    for p in phones:
        db.log_message("out", "sms", p, message, status)


def send_airtime(phone, amount, currency="NGN"):
    phone = db.normalize_phone(phone)
    status = "dry-run"
    if live():
        try:
            _init()
            _airtime.send(phone_number=phone, amount=amount, currency_code=currency)
            status = "sent"
        except Exception as e:
            log.exception("Airtime failed")
            status = f"error: {e}"[:120]
    db.log_message("out", "airtime", phone, f"{currency} {amount} airtime reward", status)
    return status
