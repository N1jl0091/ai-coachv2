"""
intervals/client.py
Async HTTP wrapper for the Intervals.icu REST API.
Docs: https://forum.intervals.icu/t/api-access-to-intervals-icu/609
"""
import os
import httpx
from typing import Any

BASE_URL = "https://intervals.icu/api/v1"


class IntervalsClient:
    def __init__(self):
        self.athlete_id = os.environ["INTERVALS_ATHLETE_ID"]
        api_key = os.environ["INTERVALS_API_KEY"]
        self._auth = ("API_KEY", api_key)
        self._headers = {"Content-Type": "application/json"}

    # ── Generic HTTP helpers ──────────────────────────────────────────────────

    async def _get(self, path: str, params: dict = None) -> Any:
        url = f"{BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, auth=self._auth, params=params)
            r.raise_for_status()
            return r.json()

    async def _put(self, path: str, body: dict) -> Any:
        url = f"{BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.put(url, auth=self._auth, json=body)
            r.raise_for_status()
            return r.json()

    async def _post(self, path: str, body: dict) -> Any:
        url = f"{BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, auth=self._auth, json=body)
            r.raise_for_status()
            return r.json()

    async def _delete(self, path: str) -> Any:
        url = f"{BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.delete(url, auth=self._auth)
            r.raise_for_status()
            return r.status_code

    # ── Fitness / wellness ────────────────────────────────────────────────────

    async def get_fitness(self) -> dict:
        """Return latest CTL, ATL, TSB, ramp rate."""
        data = await self._get(f"/athlete/{self.athlete_id}/wellness.json")
        if not data:
            return {}
        latest = data[-1] if isinstance(data, list) else data
        return {
            "ctl": latest.get("ctl"),
            "atl": latest.get("atl"),
            "tsb": latest.get("form"),
            "ramp_rate": latest.get("rampRate"),
            "phase": latest.get("trainingPhase"),
        }

    async def get_wellness(self, oldest: str, newest: str) -> list:
        """
        oldest / newest: ISO dates e.g. '2024-01-01'
        Returns list of daily wellness records.
        """
        return await self._get(
            f"/athlete/{self.athlete_id}/wellness.json",
            params={"oldest": oldest, "newest": newest},
        )

    # ── Activities ────────────────────────────────────────────────────────────

    async def list_activities(self, oldest: str, newest: str) -> list:
        return await self._get(
            f"/athlete/{self.athlete_id}/activities",
            params={"oldest": oldest, "newest": newest},
        )

    async def get_activity(self, activity_id: str) -> dict:
        return await self._get(f"/athlete/{self.athlete_id}/activities/{activity_id}")

    # ── Events (planned workouts) ─────────────────────────────────────────────

    async def get_events(self, oldest: str = None, newest: str = None) -> list:
        from datetime import date, timedelta
        if not oldest:
            oldest = date.today().isoformat()
        if not newest:
            newest = (date.today() + timedelta(days=60)).isoformat()
        return await self._get(
            f"/athlete/{self.athlete_id}/eventsjson",
            params={"oldest": oldest, "newest": newest},
        )

    async def create_event(self, event: dict) -> dict:
        return await self._post(f"/athlete/{self.athlete_id}/eventsjson", event)

    async def update_event(self, event_id: str, updates: dict) -> dict:
        return await self._put(f"/athlete/{self.athlete_id}/eventsjson/{event_id}", updates)

    async def delete_event(self, event_id: str) -> int:
        return await self._delete(f"/athlete/{self.athlete_id}/eventsjson/{event_id}")
