"""
db/profile.py
Read and write athlete profiles in Postgres.
"""
from datetime import date
from typing import Optional
from db.models import SessionLocal, AthleteProfile


def get_profile(telegram_id: str) -> Optional[AthleteProfile]:
    with SessionLocal() as db:
        return db.query(AthleteProfile).filter_by(telegram_id=telegram_id).first()


def save_profile(telegram_id: str, data: dict) -> AthleteProfile:
    """Create or fully replace a profile."""
    with SessionLocal() as db:
        profile = db.query(AthleteProfile).filter_by(telegram_id=telegram_id).first()
        if not profile:
            profile = AthleteProfile(telegram_id=telegram_id)
            db.add(profile)

        profile.name = data.get("name")
        profile.age = data.get("age")
        profile.sports = data.get("sports", [])
        profile.primary_sport = data.get("primary_sport")
        profile.available_days = data.get("available_days", [])
        profile.hours_per_week = data.get("hours_per_week")
        profile.goal_event = data.get("goal_event")

        goal_date = data.get("goal_date")
        if isinstance(goal_date, str) and goal_date:
            try:
                profile.goal_date = date.fromisoformat(goal_date)
            except ValueError:
                profile.goal_date = None
        else:
            profile.goal_date = goal_date

        profile.goal_type = data.get("goal_type", "finish")
        profile.goal_time_target = data.get("goal_time_target")
        profile.current_injuries = data.get("current_injuries", [])
        profile.limiters = data.get("limiters", [])
        profile.preferred_long_day = data.get("preferred_long_day", "sunday")
        profile.preferred_intensity = data.get("preferred_intensity", "mixed")
        profile.experience_level = data.get("experience_level", "intermediate")
        profile.equipment = data.get("equipment", {})
        profile.email = data.get("email")

        db.commit()
        db.refresh(profile)
        return profile


def patch_profile(telegram_id: str, updates: dict) -> Optional[AthleteProfile]:
    """Update specific fields only. Used by AI tool calls."""
    with SessionLocal() as db:
        profile = db.query(AthleteProfile).filter_by(telegram_id=telegram_id).first()
        if not profile:
            return None

        allowed_fields = {
            "current_injuries", "limiters", "available_days",
            "hours_per_week", "goal_event", "goal_time_target",
            "preferred_intensity", "experience_level",
        }
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(profile, field, value)

        db.commit()
        db.refresh(profile)
        return profile


def get_profile_by_intervals_athlete_id(intervals_id: str) -> Optional[AthleteProfile]:
    """
    For multi-athlete setups: look up telegram profile by Intervals athlete ID.
    Requires adding an intervals_athlete_id column to the schema (extension point).
    For now, returns None and relies on the env var fallback.
    """
    return None
