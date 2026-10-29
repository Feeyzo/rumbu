# RUMBU 🌾

**Hausa-first USSD, SMS & voice platform on Africa's Talking that helps smallholder farmers cut post-harvest losses and sell at fair prices, no smartphone needed.**

*Rumbu* is Hausa for granary. Built by Team LOGI-Q for the Africa's Talking Agriculture & Food Security Hackathon.

## The problem

A large share of Nigeria's harvest is lost *after* it's grown: weevils, moisture and mould, rodents, rot, and distress selling at low prices right after harvest. Most farmers in Northern Nigeria use basic phones, read Hausa (if they read at all), and are skipped by app-only, English-only agri-tech.

## What RUMBU does

| Farmer need | Channel | Africa's Talking API |
|---|---|---|
| Market prices with a hold-or-sell hint | USSD, SMS (`FARASHI MASARA`), voice | USSD, SMS, Voice |
| Sell produce and get matched to a buyer automatically | USSD, buyers via SMS (`BUY MAIZE 20 50000`) | USSD, SMS |
| Report a storage problem and get advice | USSD, SMS (`MATSALA masarata ta jike`), voice note | USSD, SMS, Voice |
| Get paid for reporting (₦100 airtime, once a day) | automatic | **Airtime** |
| Storage advice per crop | USSD, voice, SMS | USSD, Voice, SMS |
| Rain alerts to cover drying produce | SMS, triggered by Open-Meteo forecast | SMS |
| Hausa voice line for farmers who can't read | IVR with keypad menu and voice recording | Voice |

**The data loop:** every report is paid in airtime, so farmers become a live sensor network. The dashboard turns those reports into a post-harvest loss early-warning map by LGA and crop, which governments, NGOs and input companies can use (and pay for).

## Business model

- Commission on each buyer–farmer match
- Paid data dashboards for agencies, NGOs, insurers and input companies
- Sponsored storage products (e.g. PICS hermetic bags) recommended in advice

## Run it locally

```bash
pip install -r requirements.txt
cp .env.example .env      # leave AT_API_KEY blank for dry-run mode
python app.py
```

- Dashboard: http://localhost:5000
- Phone simulator (USSD + SMS): http://localhost:5000/simulator
- Tests: `python -m pytest -q`

In **dry-run mode** nothing is sent; every SMS and airtime reward shows in the dashboard's live feed and the simulator inbox. Add Africa's Talking credentials to send for real.

## Connect to Africa's Talking

1. Deploy (Render/Railway use the `Procfile`) or run `ngrok http 5000` and set `PUBLIC_URL`.
2. In the AT dashboard (sandbox or live), set these callback URLs:

| Service | Callback URL |
|---|---|
| USSD | `https://<your-url>/ussd` |
| SMS (incoming messages) | `https://<your-url>/sms/incoming` |
| Voice | `https://<your-url>/voice` |
| SMS delivery / airtime status | `https://<your-url>/events` |

3. Test with the AT simulator at https://simulator.africastalking.com (sandbox).

### Hausa voice prompts

AT has no Hausa text-to-speech, so the voice line plays recorded MP3s from `static/audio/` when present (`ha_welcome.mp3`, `ha_crop.mp3`, `ha_record.mp3`, `ha_recorded.mp3`, `ha_sent_sms.mp3`, `ha_invalid.mp3`). Record them in your own voices; until then it falls back to `<Say>`. Prompt scripts are in `rumbu/voice.py`.

## USSD menu (Hausa / English)

```
New user: language → name → LGA → registered (welcome SMS)

1. Farashin kasuwa / Market prices      → crop → price + trend advice
2. Sayar da amfanin gona / Sell         → crop → bags → price (0 = market) → auto-match
3. Rahoton matsala / Report a problem   → crop → problem → bags → airtime + advice SMS
4. Shawarar ajiya / Storage advice      → crop → tip (also by SMS)
5. Taimako ta murya / Voice help        → voice line number
6. Harshe / Language
```

Hausa text deliberately avoids hooked letters (ɓ ɗ ƙ) so it stays in the GSM-7 alphabet: no broken USSD screens and no doubled SMS cost.

## Project layout

```
app.py              Flask routes: AT callbacks, dashboard, simulator
rumbu/content.py    All Hausa/English text, crops, LGAs, advice
rumbu/ussd.py       USSD menu
rumbu/sms.py        Two-way SMS commands
rumbu/voice.py      Voice IVR (GetDigits, Record, Play/Say)
rumbu/services.py   Prices, marketplace matching, reports, rewards, text triage
rumbu/at.py         Africa's Talking SDK wrapper with dry-run mode
rumbu/weather.py    Open-Meteo rain alerts
rumbu/seed.py       Starting prices and demo data
tests/              End-to-end tests for every channel
```

## Notes before a real launch

- Prices in `seed.py` are illustrative placeholders; update them from the dashboard or connect a real price feed.
- Have a native speaker review the Hausa wording and agronomic advice with an extension officer.
- The dashboard has no login yet; add auth before exposing it publicly.
- Next step: plug a Hausa speech-to-text model into `services.classify` to triage voice notes automatically.
