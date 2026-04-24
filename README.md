# AI Coach — Setup Guide

Your personal AI endurance coach. Connects Intervals.icu, Telegram, Strava, and Claude into one system: chat with your coach, get your calendar adjusted, and receive a post-workout email after every session.

---

## What you need to set up (your part)

Everything in the code is done. You just need to create accounts, get API keys, and deploy. This guide goes step by step.

**Accounts required:**
1. Telegram (you probably have this)
2. Anthropic (Claude API)
3. Intervals.icu (training data)
4. Strava (activity sync trigger)
5. Railway (hosting)
6. Resend (email delivery)
7. GitHub (code repo + auto-deploy)

---

## Step 1 — Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g. "My AI Coach") and a username ending in `bot` (e.g. `myaicoach_bot`)
4. BotFather will give you a token like: `7123456789:AAHdqTcvCHhvQj0F1ZbgABCdef...`
5. Copy it → this is your `TELEGRAM_BOT_TOKEN`

**Find your Telegram user ID:**
1. Search for **@userinfobot** on Telegram
2. Send it `/start`
3. It replies with your user ID (a number like `123456789`)
4. Copy it → this is your `TELEGRAM_ATHLETE_ID`

---

## Step 2 — Get your Anthropic API key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an account or sign in
3. Go to **API Keys** → **Create Key**
4. Copy the key → `ANTHROPIC_API_KEY`

> You'll need to add a payment method. The bot uses claude-sonnet-4 — roughly $0.003 per message. Light use costs pennies per day.

---

## Step 3 — Set up Intervals.icu

1. Go to [intervals.icu](https://intervals.icu) and sign in (or create an account)
2. Connect your Garmin / Wahoo / Polar under **Settings → Integrations**
3. **Get your Athlete ID:**
   - Look at the URL when logged in: `https://intervals.icu/athlete/i12345/...`
   - The `i12345` part is your athlete ID → `INTERVALS_ATHLETE_ID`
4. **Get your API key:**
   - Go to **Settings → Developer Settings → API Key**
   - Generate one and copy it → `INTERVALS_API_KEY`

---

## Step 4 — Set up Strava (for post-workout emails)

> Skip this step if you don't want activity analysis emails. The Telegram bot works without it.

1. Go to [strava.com/settings/api](https://www.strava.com/settings/api)
2. Create an application:
   - App name: "AI Coach" (anything)
   - Website: your Railway URL (you can fill this in later — use `http://localhost` for now)
   - Authorization callback domain: your Railway domain (fill in later)
3. Note your **Client ID** and **Client Secret** → `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`
4. Choose a verify token (any random string, e.g. `ai_coach_verify`) → `STRAVA_VERIFY_TOKEN`

**You'll register the actual webhook after deploying to Railway (Step 7).**

---

## Step 5 — Set up Resend (email)

1. Go to [resend.com](https://resend.com) and create a free account
2. **Add your domain** (or use the free `@resend.dev` test domain):
   - Free tier: send from `onboarding@resend.dev` — works for testing
   - For a real domain: go to **Domains → Add Domain** and add the DNS records they give you
3. Go to **API Keys → Create API Key**
4. Copy it → `RESEND_API_KEY`
5. Set `RESEND_FROM_EMAIL` to your verified sender (e.g. `coach@yourdomain.com` or `onboarding@resend.dev`)

---

## Step 6 — Deploy to Railway

### 6a — Push code to GitHub

1. Create a new GitHub repository (private is fine)
2. Push this project to it:
   ```bash
   cd ai-coach
   git init
   git add .
   git commit -m "initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/ai-coach.git
   git push -u origin main
   ```

### 6b — Create Railway project

1. Go to [railway.app](https://railway.app) and sign up / log in
2. Click **New Project → Deploy from GitHub repo**
3. Authorise Railway to access your GitHub, then select your `ai-coach` repo
4. Railway will detect the Python project and start a deploy (it will fail until you add env vars)

### 6c — Add a Postgres database

1. In your Railway project, click **New → Database → PostgreSQL**
2. Railway automatically sets `DATABASE_URL` in your service — nothing else to do

### 6d — Add environment variables

1. Click on your service → **Variables**
2. Add each of these (Railway also has a raw editor for pasting them all at once):

```
TELEGRAM_BOT_TOKEN=         ← from Step 1
TELEGRAM_ATHLETE_ID=        ← from Step 1
ANTHROPIC_API_KEY=          ← from Step 2
INTERVALS_API_KEY=          ← from Step 3
INTERVALS_ATHLETE_ID=       ← from Step 3
STRAVA_CLIENT_ID=           ← from Step 4
STRAVA_CLIENT_SECRET=       ← from Step 4
STRAVA_VERIFY_TOKEN=        ← from Step 4 (whatever you chose)
RESEND_API_KEY=             ← from Step 5
RESEND_FROM_EMAIL=          ← from Step 5
```

> `DATABASE_URL` is injected automatically by Railway — do NOT set it manually.

3. Save variables → Railway will redeploy automatically

### 6e — Get your Railway URL

1. Click on your service → **Settings → Domains**
2. Click **Generate Domain** — you'll get something like `ai-coach-production.up.railway.app`
3. Copy it — you need it for Step 7

---

## Step 7 — Register the Strava webhook

Once your Railway service is running, register the webhook so Strava sends activity events to it.

Run this curl command (replace the values):

```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -F client_id=YOUR_STRAVA_CLIENT_ID \
  -F client_secret=YOUR_STRAVA_CLIENT_SECRET \
  -F callback_url=https://YOUR_RAILWAY_DOMAIN/strava/webhook \
  -F verify_token=ai_coach_verify
```

Strava will call your `/strava/webhook` endpoint to verify it. If it responds with `200 OK`, you'll get back a subscription ID. Done.

> **Test it:** Go for a run or ride, upload to Strava/Garmin. Within a few minutes you should get an analysis email.

---

## Step 8 — Test the bot

1. Open Telegram and search for your bot username
2. Send `/start` → you should see the welcome message
3. Send `/setup` → walk through the onboarding questions
4. Once set up, send `/status` → should show your current CTL/ATL/TSB from Intervals
5. Try a free message: _"What should I do today?"_

---

## Local development

```bash
# Clone and install
git clone https://github.com/YOUR_USERNAME/ai-coach.git
cd ai-coach
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up local Postgres
# Option A: Docker
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password -e POSTGRES_DB=aicoach postgres:16

# Copy and fill in env vars
cp .env.example .env
# Edit .env with your values

# Load env vars and run
export $(cat .env | grep -v ^# | xargs)
python main.py
```

---

## Project structure

```
ai-coach/
├── main.py                  ← entry point (starts bot + webhook server)
├── bot/
│   ├── telegram_bot.py      ← message routing
│   ├── commands.py          ← /start /setup /profile /status
│   └── session.py           ← per-session chat history (in-memory)
├── coach/
│   ├── ai.py                ← Claude API calls, tool use
│   ├── system_prompt.py     ← coach personality
│   └── context_builder.py   ← assembles Intervals + profile context
├── intervals/
│   ├── client.py            ← Intervals.icu API wrapper
│   ├── workouts.py          ← create / edit / move / delete workouts
│   └── wellness.py          ← sleep, HRV, resting HR, steps
├── strava/
│   ├── webhook.py           ← FastAPI endpoint
│   └── analysis.py          ← pulls activity, runs analysis
├── email/
│   └── resend_client.py     ← sends HTML email via Resend
├── db/
│   ├── models.py            ← SQLAlchemy AthleteProfile model
│   └── profile.py           ← read / write / patch profile
├── .env.example             ← template — copy to .env
├── requirements.txt
├── Procfile
└── railway.toml
```

---

## How it works

**Every Telegram message:**
1. Bot receives message
2. Intervals.icu data pulled in parallel (CTL/ATL/TSB, workouts, wellness)
3. Athlete profile loaded from Postgres
4. Everything assembled into the Claude context
5. Claude replies as your coach
6. If Claude decides to modify the calendar, it calls tools (create/move/delete workouts on Intervals) — always confirming with you first

**Every Strava activity upload:**
1. Strava fires a webhook to Railway
2. Activity data pulled from Intervals (richer than Strava's own data)
3. Claude generates a 200-300 word analysis
4. Email sent via Resend

---

## Troubleshooting

**Bot doesn't respond:**
- Check Railway logs for errors
- Verify `TELEGRAM_BOT_TOKEN` is set correctly
- Make sure the Railway service is running (green in dashboard)

**"No Intervals data" in responses:**
- Double-check `INTERVALS_ATHLETE_ID` (include the `i` prefix, e.g. `i12345`)
- Verify `INTERVALS_API_KEY` — test it: `curl -u API_KEY:your_key https://intervals.icu/api/v1/athlete/i12345/wellness.json`

**Strava webhook not triggering:**
- Verify the webhook was registered successfully (Step 7)
- Check that your Railway domain is correct and the service is live
- Check Railway logs for `/strava/webhook` POST requests

**Email not arriving:**
- Check spam folder
- Verify domain is verified in Resend dashboard
- Check Resend logs at [resend.com/emails](https://resend.com/emails)

**Database errors on startup:**
- `DATABASE_URL` not set — Railway should inject this automatically if you added the Postgres plugin
- Tables are created automatically on startup via `init_db()`

---

## Costs (rough estimates for personal use)

| Service | Free tier | Typical personal use |
|---|---|---|
| Railway | $5/month hobby plan | ~$5/month |
| Anthropic | Pay per use | ~$1-5/month |
| Resend | 3,000 emails/month free | Free |
| Intervals.icu | Free tier available | Free |
| Strava | Free | Free |

**Total: ~$6-10/month**
