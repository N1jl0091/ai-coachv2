"""
coach/context_builder.py
Pulls Intervals.icu data + athlete profile in parallel before every AI call.
"""
import asyncio
from db.profile import get_profile
from intervals.client import IntervalsClient
from intervals.wellness import get_wellness_snapshot
from intervals.workouts import get_recent_workouts, get_planned_workouts


async def build_context(telegram_id: str) -> tuple[dict, dict]:
    """
    Returns (profile_dict, intervals_snapshot_dict).
    Runs API calls in parallel for low latency.
    """
    profile = get_profile(telegram_id)
    profile_dict = _profile_to_dict(profile) if profile else {}

    client = IntervalsClient()

    fitness_task = asyncio.create_task(client.get_fitness())
    wellness_task = asyncio.create_task(get_wellness_snapshot(client))
    recent_task = asyncio.create_task(get_recent_workouts(client, days=7))
    planned_task = asyncio.create_task(get_planned_workouts(client, days=7))
    events_task = asyncio.create_task(client.get_events())

    fitness, wellness, recent, planned, events = await asyncio.gather(
        fitness_task, wellness_task, recent_task, planned_task, events_task,
        return_exceptions=True,
    )

    snapshot = {
        "fitness": fitness if not isinstance(fitness, Exception) else {},
        "wellness": wellness if not isinstance(wellness, Exception) else {},
        "recent_workouts": recent if not isinstance(recent, Exception) else [],
        "planned_workouts": planned if not isinstance(planned, Exception) else [],
        "events": events if not isinstance(events, Exception) else [],
    }

    return profile_dict, snapshot


async def build_quick_status(telegram_id: str) -> str:
    """Used by /status command — returns a formatted status string."""
    profile_dict, snapshot = await build_context(telegram_id)
    name = profile_dict.get("name", "Athlete")
    fitness = snapshot.get("fitness", {})
    wellness = snapshot.get("wellness", {})
    planned = snapshot.get("planned_workouts", [])

    ctl = fitness.get("ctl", "?")
    atl = fitness.get("atl", "?")
    tsb = fitness.get("tsb", "?")

    sleep_entries = wellness.get("sleep", [])
    last_sleep = sleep_entries[-1] if sleep_entries else {}
    sleep_str = (
        f"{last_sleep.get('hours')}h (quality {last_sleep.get('quality')}/5)"
        if last_sleep else "No data"
    )

    today_plan = planned[0] if planned else None
    plan_str = (
        f"{today_plan.get('sport')} — {today_plan.get('name')} (~{today_plan.get('duration_min')}min)"
        if today_plan else "Rest day / nothing planned"
    )

    # Form interpretation
    if isinstance(tsb, (int, float)):
        if tsb > 10:
            form_label = "✅ Fresh"
        elif tsb > -10:
            form_label = "🟡 Neutral"
        elif tsb > -25:
            form_label = "🟠 Tired"
        else:
            form_label = "🔴 Very fatigued"
    else:
        form_label = "Unknown"

    return (
        f"*{name}'s Status*\n\n"
        f"*Fitness (CTL):* {ctl}\n"
        f"*Fatigue (ATL):* {atl}\n"
        f"*Form (TSB):* {tsb} — {form_label}\n\n"
        f"*Last night's sleep:* {sleep_str}\n\n"
        f"*Today's plan:* {plan_str}"
    )


def _profile_to_dict(profile) -> dict:
    if profile is None:
        return {}
    return {
        "name": profile.name,
        "age": profile.age,
        "sports": profile.sports,
        "primary_sport": profile.primary_sport,
        "available_days": profile.available_days,
        "hours_per_week": profile.hours_per_week,
        "goal_event": profile.goal_event,
        "goal_date": str(profile.goal_date) if profile.goal_date else None,
        "goal_type": profile.goal_type,
        "goal_time_target": profile.goal_time_target,
        "current_injuries": profile.current_injuries,
        "limiters": profile.limiters,
        "preferred_long_day": profile.preferred_long_day,
        "preferred_intensity": profile.preferred_intensity,
        "experience_level": profile.experience_level,
        "equipment": profile.equipment,
        "email": profile.email,
    }
