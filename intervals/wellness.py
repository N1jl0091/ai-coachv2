"""
intervals/wellness.py
Pull sleep, HRV, resting HR, steps, weight from Intervals.icu wellness endpoint.
"""
from datetime import date, timedelta
from intervals.client import IntervalsClient


async def get_wellness_snapshot(client: IntervalsClient) -> dict:
    """Return 7 days of wellness data, cleaned and structured."""
    oldest = (date.today() - timedelta(days=7)).isoformat()
    newest = date.today().isoformat()

    raw = await client.get_wellness(oldest=oldest, newest=newest)
    if not raw:
        return {}

    records = raw if isinstance(raw, list) else [raw]

    sleep_data = []
    hrv_values = []
    rhr_values = []
    steps_values = []
    weight_values = []

    for r in records:
        d = r.get("id") or r.get("date")  # date field varies

        hours = r.get("sleepSecs", 0) / 3600 if r.get("sleepSecs") else None
        quality = r.get("sleepQuality")  # 1-5 scale in Intervals

        if hours:
            sleep_data.append({
                "date": d,
                "hours": round(hours, 1),
                "quality": quality,
            })

        if r.get("hrv"):
            hrv_values.append((d, r["hrv"]))
        if r.get("restingHR"):
            rhr_values.append((d, r["restingHR"]))
        if r.get("steps"):
            steps_values.append((d, r["steps"]))
        if r.get("weight"):
            weight_values.append((d, r["weight"]))

    hrv_trend = _trend_label(hrv_values) if len(hrv_values) >= 3 else None
    rhr_trend = _trend_label(rhr_values, invert=True) if len(rhr_values) >= 3 else None

    return {
        "sleep": sleep_data,
        "hrv_trend": hrv_trend,
        "hrv_values": hrv_values,
        "rhr_trend": rhr_trend,
        "steps": steps_values,
        "weight": weight_values,
    }


def _trend_label(values: list, invert: bool = False) -> str:
    """
    Simple 3-point trend label: 'rising', 'falling', 'stable'.
    invert=True means rising is bad (e.g. resting HR).
    """
    if len(values) < 2:
        return "stable"
    nums = [v[1] for v in values]
    first_half = sum(nums[:len(nums)//2]) / max(len(nums)//2, 1)
    second_half = sum(nums[len(nums)//2:]) / max(len(nums) - len(nums)//2, 1)
    diff = second_half - first_half
    if abs(diff) < 0.02 * first_half:
        return "stable"
    rising = diff > 0
    if invert:
        return "rising (⚠️ fatigue signal)" if rising else "falling (good)"
    return "rising ✅" if rising else "falling (⚠️ check recovery)"
