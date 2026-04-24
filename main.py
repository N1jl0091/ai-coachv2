"""
AI Coach - Entry Point
Starts both the Telegram bot (polling) and the Strava webhook (FastAPI) in one process.
"""
import asyncio
import threading
import uvicorn
from fastapi import FastAPI
from bot.telegram_bot import create_bot
from strava.webhook import router as strava_router
from db.models import init_db

app = FastAPI(title="AI Coach Webhook Server")
app.include_router(strava_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


def main():
    # Initialise DB tables
    init_db()

    # Start FastAPI in a background thread
    thread = threading.Thread(target=run_fastapi, daemon=True)
    thread.start()

    # Start Telegram bot in main thread (blocking)
    bot = create_bot()
    bot.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
