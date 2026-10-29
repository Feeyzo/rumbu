"""Hausa voice line (IVR) for farmers who can't read.

Africa's Talking has no Hausa text-to-speech, so each prompt plays a
recorded MP3 from static/audio/<lang>_<key>.mp3 when it exists, and falls
back to <Say> text otherwise. Record the Hausa prompts in your own voices.
"""
import os
from xml.sax.saxutils import escape

from . import at, db, services
from .content import CROPS, STORAGE_TIPS

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "audio")

PROMPTS = {
    "welcome": {
        "ha": "Barka da zuwa RUMBU. Danna daya don shawarar ajiya. Danna biyu don bayyana matsalar amfanin gonarka. Danna uku don farashin kasuwa.",
        "en": "Welcome to RUMBU. Press 1 for storage advice. Press 2 to describe a problem with your harvest. Press 3 for market prices.",
    },
    "crop": {
        "ha": "Danna daya masara, biyu dawa, uku gero, hudu shinkafa, biyar wake, shida gyada, bakwai tumatir.",
        "en": "Press 1 maize, 2 sorghum, 3 millet, 4 rice, 5 beans, 6 groundnut, 7 tomato.",
    },
    "record": {
        "ha": "Bayan kara, fadi matsalar da kake gani a amfanin gonarka. Danna kare idan ka gama.",
        "en": "After the beep, describe the problem with your harvest. Press hash when done.",
    },
    "recorded": {
        "ha": "Mun karbi sakonka. Za a turo maka shawara ta SMS. Na gode.",
        "en": "We have your message. Advice will come by SMS. Thank you.",
    },
    "sent_sms": {
        "ha": "Mun kuma tura maka wannan ta SMS. Na gode.",
        "en": "We have also sent this to you by SMS. Thank you.",
    },
    "invalid": {"ha": "Ban gane ba. Sake kira.", "en": "Sorry, invalid choice. Please call again."},
}


def _say(key, lang, base, text=None):
    fname = f"{lang}_{key}.mp3"
    if text is None and os.path.exists(os.path.join(AUDIO_DIR, fname)):
        return f'<Play url="{escape(base)}static/audio/{fname}"/>'
    return f"<Say>{escape(text or PROMPTS[key][lang])}</Say>"


def _xml(body):
    return f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>'


def _digits(key, lang, base, step, n=1):
    return (f'<GetDigits timeout="20" numDigits="{n}" finishOnKey="#" callbackUrl="{escape(base)}voice?step={step}">'
            f"{_say(key, lang, base)}</GetDigits>")


def handle(form, step, base):
    phone = form.get("callerNumber", "")
    if form.get("isActive") == "0":
        db.log_message("in", "voice", phone,
                       f"call ended ({form.get('durationInSeconds', '?')}s)", "completed")
        return ""
    farmer = db.get_farmer(phone)
    lang = farmer["lang"] if farmer else "ha"
    digits = form.get("dtmfDigits", "")

    if not step:
        db.log_message("in", "voice", phone, "incoming call", "answered")
        return _xml(_digits("welcome", lang, base, "menu"))

    if step == "menu":
        if digits == "1":
            return _xml(_digits("crop", lang, base, "storage"))
        if digits == "2":
            return _xml(_say("record", lang, base) +
                        f'<Record finishOnKey="#" maxLength="60" trimSilence="true" playBeep="true" '
                        f'callbackUrl="{escape(base)}voice?step=recorded"/>')
        if digits == "3":
            return _xml(_digits("crop", lang, base, "price"))
        return _xml(_say("invalid", lang, base))

    if step in ("storage", "price"):
        try:
            crop = CROPS[int(digits) - 1][0]
        except (ValueError, IndexError):
            return _xml(_say("invalid", lang, base))
        text = STORAGE_TIPS[crop][lang] if step == "storage" else services.price_text(crop, lang)
        at.send_sms(phone, "RUMBU: " + text)
        return _xml(_say(None, lang, base, text=text) + _say("sent_sms", lang, base))

    if step == "recorded":
        url = form.get("recordingUrl", "")
        # Saved for an agronomist to listen to on the dashboard; the reply goes
        # back as SMS. Plug a Hausa speech-to-text model into services.classify
        # to automate triage.
        services.create_report(phone, None, "voice_note", 0, channel="voice",
                               note="Voice note - awaiting review", recording_url=url)
        return _xml(_say("recorded", lang, base))

    return _xml(_say("invalid", lang, base))


