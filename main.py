"""
AI Coach - Entry Point
Starts both the Telegram bot (polling) and the Strava webhook (FastAPI) in one process.
"""
import asyncio
import threading
import uvicorn
from telegram import Update
from fastapi import FastAPI
from bot.telegram_bot import create_bot
from strava.webhook import router as strava_router
from db.models import init_db

asyncio.set_event_loop(asyncio.new_event_loop())

app = FastAPI(title="AI Coach Webhook Server")
app.include_router(strava_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


def run_fastapi():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info", loop="none")
    
def main():
    # Initialise DB tables
    init_db()

    # Start FastAPI in a background thread
    thread = threading.Thread(target=run_fastapi, daemon=True)
    thread.start()

    # Start Telegram bot in main thread (blocking)
    bot = create_bot()
    bot.run_polling(
    drop_pending_updates=True,
    allowed_updates=Update.ALL_TYPES,
    connect_timeout=30,
    read_timeout=30,
    write_timeout=30,
    pool_timeout=30,
)


if __name__ == "__main__":
    main()
