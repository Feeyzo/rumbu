"""Hausa voice line (IVR) for farmers who can't read.

Africa's Talking has no Hausa text-to-speech, so every prompt is a recording
of a real person. The team records them in the admin "Voice prompts" studio
(saved to static/audio/<lang>_<key>.wav). Until a prompt is recorded the call
falls back to <Say> with the written text.
"""
import os
from xml.sax.saxutils import escape

from . import at, db, services
from .content import CROPS, STORAGE_TIPS, crop_name

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "audio")
AUDIO_EXTS = (".wav", ".mp3")

PROMPTS = {
    "welcome": {
        "label": "Greeting and main menu (plays when the call is answered)",
        "ha": "Barka da zuwa RUMBU. Danna daya don shawarar ajiya. Danna biyu don bayyana matsalar amfanin gonarka. Danna uku don farashin kasuwa.",
        "en": "Welcome to RUMBU. Press 1 for storage advice. Press 2 to describe a problem with your harvest. Press 3 for market prices.",
    },
    "crop": {
        "label": "Choose a crop",
        "ha": "Danna daya masara, biyu dawa, uku gero, hudu shinkafa, biyar wake, shida gyada, bakwai tumatir.",
        "en": "Press 1 maize, 2 sorghum, 3 millet, 4 rice, 5 beans, 6 groundnut, 7 tomato.",
    },
    "record": {
        "label": "Before recording a voice note",
        "ha": "Bayan kara, fadi matsalar da kake gani a amfanin gonarka. Danna kare idan ka gama.",
        "en": "After the beep, describe the problem with your harvest. Press hash when done.",
    },
    "recorded": {
        "label": "After the voice note is saved",
        "ha": "Mun karbi sakonka. Jami'in gona zai saurara, kuma za a turo maka shawara ta SMS. Na gode.",
        "en": "We have your message. An extension officer will listen and send advice by SMS. Thank you.",
    },
    "price_sms": {
        "label": "Market price (the number itself goes by SMS)",
        "ha": "Mun tura maka farashin kasuwa na yau ta SMS. Duba sakonka. Na gode.",
        "en": "We have sent today's market price to you by SMS. Please check your messages. Thank you.",
    },
    "sent_sms": {
        "label": "End of storage advice",
        "ha": "Mun kuma tura maka wannan ta SMS. Na gode.",
        "en": "We have also sent this to you by SMS. Thank you.",
    },
    "invalid": {
        "label": "Wrong key pressed",
        "ha": "Ban gane ba. Sake kira.",
        "en": "Sorry, invalid choice. Please call again.",
    },
}
for _key, _ha, _en, _u in CROPS:
    PROMPTS[f"tip_{_key}"] = {"label": f"Storage advice: {_en}", **STORAGE_TIPS[_key]}


def audio_file(key, lang):
    """Filename of the recording for this prompt, or None."""
    for ext in AUDIO_EXTS:
        name = f"{lang}_{key}{ext}"
        if os.path.exists(os.path.join(AUDIO_DIR, name)):
            return name
    return None


def _say(key, lang, base):
    fname = audio_file(key, lang)
    if fname:
        return f'<Play url="{escape(base)}static/audio/{fname}"/>'
    return f"<Say>{escape(PROMPTS[key][lang])}</Say>"


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
        if step == "storage":
            at.send_sms(phone, "RUMBU: " + STORAGE_TIPS[crop][lang])
            return _xml(_say(f"tip_{crop}", lang, base) + _say("sent_sms", lang, base))
        at.send_sms(phone, "RUMBU: " + services.price_text(crop, lang))
        db.log_message("in", "voice", phone, f"price request: {crop_name(crop, 'en')}", "answered")
        return _xml(_say("price_sms", lang, base))

    if step == "recorded":
        url = form.get("recordingUrl", "")
        # Saved for an agronomist to listen to in Operations; the reply goes
        # back as SMS. Plug a Hausa speech-to-text model into services.classify
        # to automate triage.
        services.create_report(phone, None, "voice_note", 0, channel="voice",
                               note="Voice note - awaiting review", recording_url=url)
        return _xml(_say("recorded", lang, base))

    return _xml(_say("invalid", lang, base))
