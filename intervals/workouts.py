"""
intervals/workouts.py
Create, edit, move, and delete workouts on the Intervals.icu calendar.
Also: fetch recent completed and planned workouts.
"""
from datetime import date, timedelta
from intervals.client import IntervalsClient

_SPORT_MAP = {
    "run": "Run",
    "running": "Run",
    "ride": "Ride",
    "cycling": "Ride",
    "bike": "Ride",
    "swim": "Swim",
    "swimming": "Swim",
    "strength": "WeightTraining",
    "gym": "WeightTraining",
    "walk": "Walk",
    "hike": "Hike",
}


def _normalise_sport(sport: str) -> str:
    return _SPORT_MAP.get(sport.lower(), sport)


async def get_recent_workouts(client: IntervalsClient, days: int = 7) -> list:
    """Return completed workouts from the last N days, simplified."""
    oldest = (date.today() - timedelta(days=days)).isoformat()
    newest = date.today().isoformat()
    raw = await client.list_activities(oldest=oldest, newest=newest)
    return [_simplify_activity(a) for a in (raw or [])]


async def get_planned_workouts(client: IntervalsClient, days: int = 7) -> list:
    """Return upcoming planned events/workouts for the next N days."""
    oldest = date.today().isoformat()
    newest = (date.today() + timedelta(days=days)).isoformat()
    raw = await client.get_events(oldest=oldest, newest=newest)
    return [_simplify_event(e) for e in (raw or []) if e.get("category") == "WORKOUT"]


async def create_workout(
    date: str,
    sport: str,
    name: str,
    description: str = "",
    duration_seconds: int = None,
    target_tss: float = None,
) -> dict:
    client = IntervalsClient()
    payload = {
        "start_date_local": f"{date}T06:00:00",
        "type": _normalise_sport(sport),
        "name": name,
        "description": description,
        "category": "WORKOUT",
    }
    if duration_seconds:
        payload["moving_time"] = duration_seconds
    if target_tss:
        payload["workout_doc"] = {"tss": target_tss}

    result = await client.create_event(payload)
    return {"success": True, "id": result.get("id"), "name": name, "date": date}


async def update_workout(
    workout_id: str,
    name: str = None,
    description: str = None,
    duration_seconds: int = None,
    target_tss: float = None,
) -> dict:
    client = IntervalsClient()
    updates = {}
    if name:
        updates["name"] = name
    if description:
        updates["description"] = description
    if duration_seconds:
        updates["moving_time"] = duration_seconds
    if target_tss:
        updates["workout_doc"] = {"tss": target_tss}

    result = await client.update_event(workout_id, updates)
    return {"success": True, "id": workout_id}


async def move_workout(workout_id: str, new_date: str) -> dict:
    client = IntervalsClient()
    result = await client.update_event(
        workout_id, {"start_date_local": f"{new_date}T06:00:00"}
    )
    return {"success": True, "id": workout_id, "new_date": new_date}


async def delete_workout(workout_id: str) -> dict:
    client = IntervalsClient()
    await client.delete_event(workout_id)
    return {"success": True, "id": workout_id}


def _simplify_activity(a: dict) -> dict:
    return {
        "id": a.get("id"),
        "date": a.get("start_date_local", "")[:10],
        "name": a.get("name"),
        "sport": a.get("type"),
        "duration_min": round((a.get("moving_time") or 0) / 60),
        "tss": a.get("icu_training_load"),
        "avg_hr": a.get("average_heartrate"),
        "avg_power": a.get("average_watts"),
        "distance_km": round((a.get("distance") or 0) / 1000, 1),
    }


def _simplify_event(e: dict) -> dict:
    start = e.get("start_date_local", "")
    return {
        "id": e.get("id"),
        "date": start[:10] if start else None,
        "name": e.get("name"),
        "sport": e.get("type"),
        "duration_min": round((e.get("moving_time") or 0) / 60),
        "description": e.get("description", ""),
        "target_tss": (e.get("workout_doc") or {}).get("tss"),
    }
