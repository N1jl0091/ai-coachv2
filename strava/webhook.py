"""
strava/webhook.py
FastAPI router for the Strava webhook.
Strava sends a GET for verification and a POST on every activity event.
"""
import os
import asyncio
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from strava.analysis import handle_activity_event

router = APIRouter(prefix="/strava")

VERIFY_TOKEN = os.environ.get("STRAVA_VERIFY_TOKEN", "ai_coach_verify")


@router.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    hub_mode = params.get("hub.mode")
    hub_challenge = params.get("hub.challenge")
    hub_verify_token = params.get("hub.verify_token")

    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return {"hub.challenge": hub_challenge}
    raise HTTPException(status_code=403, detail="Verification failed")
    
@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """Strava calls this on every activity event."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Only handle activity creates (aspect_type: "create", object_type: "activity")
    if (
        payload.get("object_type") == "activity"
        and payload.get("aspect_type") == "create"
    ):
        activity_id = payload.get("object_id")
        athlete_id = str(payload.get("owner_id"))
        background_tasks.add_task(handle_activity_event, athlete_id, activity_id)

    # Always return 200 immediately so Strava doesn't retry
    return {"status": "ok"}
