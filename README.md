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

## Who uses it

| Who | How they get in | What they do |
|---|---|---|
| **Farmers** | Dial the USSD code. Their phone number is their account; no website. | Prices, selling, reporting problems, storage advice, voice help |
| **Buyers / aggregators** | Sign up on the website (`/signup`) | Post buy requests, browse and buy farmer listings, see matched farmers' numbers |
| **Partners** (government, NGOs, insurers) | Account created by an admin | Read-only loss insights: map by LGA, bags at risk by crop, weekly trend, anonymised CSV |
| **RUMBU team / agronomists** (admin) | Account created by an admin, or from `ADMIN_EMAIL` | Operations: reply to voice notes, rain alerts, prices, buyers, user accounts |

Pages: `/` landing, `/login`, `/signup`, `/buyer`, `/partner`, `/admin`, `/admin/users`, `/simulator`.

With `SEED_DEMO=1` the login page shows one-click demo accounts (password `rumbu2026`, or `DEMO_PASSWORD`):
`admin@rumbu.ng`, `partner@rumbu.ng`, `buyer@rumbu.ng`. **Set `SEED_DEMO=0` for real use.**

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

- Landing page: http://localhost:5000 (log in from there with a demo account)
- Phone simulator (USSD + SMS): http://localhost:5000/simulator
- Tests: `python -m pytest -q`

In **dry-run mode** nothing is sent; every SMS and airtime reward shows in the operations feed and the simulator inbox. Add Africa's Talking credentials to send for real.

## Settings

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | **Set this in production.** Signs login cookies; without it everyone is logged out on each restart. |
| `AT_USERNAME`, `AT_API_KEY` | Africa's Talking credentials (`sandbox` for testing). Blank = dry-run. |
| `AT_SENDER_ID`, `AT_VOICE_NUMBER` | Optional SMS sender ID and the voice line number shown to farmers |
| `PUBLIC_URL` | Public HTTPS address, used in voice callbacks |
| `USSD_CODE` | Code shown on the website, e.g. `*384*7867#` |
| `SEED_DEMO` | `1` loads demo farmers, reports, buyers and demo logins |
| `DEMO_PASSWORD` | Password for the demo logins |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Creates the first real admin on start-up |
| `SIMULATOR` | `1` keeps the public phone simulator on. Turn off (`0`) in production: it can read any number's messages. |
| `REPORT_REWARD_NGN` | Airtime per report (default 100, once a day per farmer) |

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

### Hausa voice line

Farmers who can't read call the helpline: press 1 for storage advice, 2 to leave a voice note, 3 for prices (sent by SMS). Voice notes land in **Operations** marked "Needs reply" for an agronomist to listen to and answer by SMS.

Africa's Talking has no Hausa text-to-speech, so every prompt is a real recording:

1. Log in as admin and open **Voice prompts** (`/admin/voice`).
2. Press **Record**, read the Hausa script, press **Stop**. It saves as a small WAV the call plays with `<Play>`.
3. Unrecorded prompts fall back to `<Say>` with the written text.
4. On Render's free plan files are wiped on redeploy, so **Download all recordings**, unzip into the repo (it creates `static/audio/`) and push.

To demo without an Africa's Talking voice number, use **Call helpline** in the phone simulator. It runs the exact same voice XML in the browser, plays your recordings, and records a voice note from your microphone.

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
app.py              Flask routes: AT callbacks, landing, login, buyer/partner/admin areas, simulator
rumbu/auth.py       Accounts, roles, password hashing
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
- Set `SEED_DEMO=0`, `SIMULATOR=0` and a strong `SECRET_KEY`, and create your admin with `ADMIN_EMAIL`/`ADMIN_PASSWORD`.
- SQLite is fine for a pilot; move to Postgres before many concurrent users (Render's free disk resets on redeploy).
- Next step: plug a Hausa speech-to-text model into `services.classify` to triage voice notes automatically.
