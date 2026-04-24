"""
strava/analysis.py
Pulls the completed activity from Intervals (richer data than Strava direct),
runs AI analysis, sends email.
"""
import asyncio
from datetime import date, timedelta
from intervals.client import IntervalsClient
from intervals.workouts import _simplify_activity
from coach.ai import analyse_activity
from coach.context_builder import build_context
from notifications.resend_client import send_analysis_email
from db.profile import get_profile_by_intervals_athlete_id


async def handle_activity_event(strava_athlete_id: str, strava_activity_id: int):
    """
    Background task: fetch activity from Intervals, analyse, email the athlete.
    Note: We look up the profile via the Intervals athlete ID stored in env
    (single-athlete setup). For multi-athlete, extend the DB schema to map IDs.
    """
    import os
    intervals_athlete_id = os.environ.get("INTERVALS_ATHLETE_ID")

    # Fetch last 2 days of activities from Intervals to find the new one
    client = IntervalsClient()
    oldest = (date.today() - timedelta(days=2)).isoformat()
    newest = date.today().isoformat()

    activities = await client.list_activities(oldest=oldest, newest=newest)
    if not activities:
        return

    # Take the most recent activity (just synced)
    activity = _simplify_activity(activities[-1])

    # Build context — use env athlete ID for single-athlete setup
    # For multi-athlete: look up telegram_id from strava_athlete_id mapping
    telegram_id = os.environ.get("TELEGRAM_ATHLETE_ID", "")
    profile_dict, snapshot = await build_context(telegram_id)

    if not profile_dict:
        return  # No profile, skip

    email = profile_dict.get("email")
    name = profile_dict.get("name", "Athlete")
    if not email:
        return

    analysis = await analyse_activity(activity, profile_dict, snapshot)

    activity_name = activity.get("name", "Workout")
    activity_date = activity.get("date", date.today().isoformat())
    subject = f"📊 {activity_name} — {activity_date}"

    await send_analysis_email(
        to_email=email,
        to_name=name,
        subject=subject,
        analysis_text=analysis,
        activity=activity,
    )
