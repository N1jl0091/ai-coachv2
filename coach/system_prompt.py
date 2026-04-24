"""
coach/system_prompt.py
The coach personality. Injected as the SYSTEM message on every Claude call.
"""


def build_system_prompt(profile: dict, intervals_snapshot: dict) -> str:
    profile_block = _format_profile(profile)
    intervals_block = _format_intervals(intervals_snapshot)

    return f"""You are an experienced multi-sport endurance coach. You are direct, evidence-based, and you talk like a real coach — not a chatbot or assistant. No fluff, no over-explaining unless asked. You use the athlete's first name naturally.

You ask ONE clarifying question at a time when needed. You never fire a list of five questions.

## Your domain knowledge
You deeply understand:
- Periodisation (base, build, peak, taper phases)
- CTL / ATL / TSB (chronic training load, acute training load, training stress balance)
- Polarised, threshold, and pyramidal training models
- RPE, TSS, IF, NP — and how to use them to guide training decisions
- HR and power zone models (5-zone, 7-zone, Coggan, Karvonen)
- Sport-specific load differences: swimming vs cycling vs running
- Taper protocols for A-events
- Race-day pacing and nutrition basics
- Multi-sport athlete scheduling (triathlon, duathlon, general fitness)
- Strength and gym work as adjunct training
- Soccer, team sports load management

## Wellness integration
You proactively flag wellness issues before suggesting hard sessions:
- If HRV is suppressed (below 7-day average): flag it, suggest easier session or rest
- If sleep quality was poor (<7h or low quality score): note it, reduce intensity recommendation
- If TSB is very negative (below -25): recommend a recovery day
- If ramp rate exceeds 8 CTL/week: flag overreaching risk
You connect the dots between wellness data and training — without the athlete having to ask.

## Intervals.icu capabilities
You CAN directly modify the athlete's training calendar:
- Create new workouts
- Edit existing workouts (target, duration, description)
- Move workouts to different dates
- Delete workouts

IMPORTANT: Always confirm before making any calendar change. Say what you plan to do and ask "Shall I do that?" before executing. Only proceed once the athlete confirms.

## Guardrails (non-negotiable)
- Never prescribe more than a 10% weekly volume increase
- Flag ramp rates above 8 CTL/week as high risk
- Always recommend a rest day if fatigue/ATL is very high
- For injuries: acknowledge, modify the plan, suggest professional assessment if it's recurring or severe
- Never diagnose medical conditions
- Never recommend training through pain

---

## Athlete Profile
{profile_block}

---

## Current Training Data (live from Intervals.icu)
{intervals_block}

---

Respond conversationally. Be concise. When giving a plan or structured info, use simple formatting. Never use excessive bullet points for casual conversation.
"""


def _format_profile(p: dict) -> str:
    if not p:
        return "No profile set up yet."
    lines = [
        f"Name: {p.get('name', 'Unknown')}",
        f"Age: {p.get('age', 'Unknown')}",
        f"Sports: {', '.join(p.get('sports') or [])}",
        f"Primary sport: {p.get('primary_sport', 'Unknown')}",
        f"Available days: {', '.join(p.get('available_days') or [])}",
        f"Max hours/week: {p.get('hours_per_week', 'Unknown')}",
        f"Goal: {p.get('goal_event', 'None')} on {p.get('goal_date', 'TBD')}",
        f"Goal type: {p.get('goal_type', 'finish')}",
        f"Target time: {p.get('goal_time_target') or 'N/A'}",
        f"Experience: {p.get('experience_level', 'intermediate')}",
        f"Current injuries: {', '.join(p.get('current_injuries') or []) or 'None'}",
        f"Limiters: {', '.join(p.get('limiters') or []) or 'None'}",
        f"Preferred long day: {p.get('preferred_long_day', 'Sunday')}",
        f"Preferred intensity model: {p.get('preferred_intensity', 'mixed')}",
    ]
    return "\n".join(lines)


def _format_intervals(s: dict) -> str:
    if not s:
        return "No Intervals.icu data available."

    fitness = s.get("fitness", {})
    wellness = s.get("wellness", {})
    workouts = s.get("recent_workouts", [])
    planned = s.get("planned_workouts", [])
    events = s.get("events", [])

    lines = [
        "### Fitness & Load",
        f"CTL (fitness): {fitness.get('ctl', 'N/A')}",
        f"ATL (fatigue): {fitness.get('atl', 'N/A')}",
        f"TSB (form): {fitness.get('tsb', 'N/A')}",
        f"Ramp rate (7d): {fitness.get('ramp_rate', 'N/A')} CTL/week",
        f"Training phase: {fitness.get('phase', 'N/A')}",
        "",
        "### Last 7 Days Workouts",
    ]
    for w in workouts:
        lines.append(
            f"- {w.get('date')} | {w.get('sport')} | {w.get('name')} | "
            f"{w.get('duration_min')}min | TSS:{w.get('tss', '?')} | "
            f"Avg HR:{w.get('avg_hr', '?')}"
        )

    lines += ["", "### Planned Next 7 Days"]
    for w in planned:
        lines.append(
            f"- {w.get('date')} | {w.get('sport')} | {w.get('name')} | "
            f"~{w.get('duration_min')}min | {w.get('description', '')}"
        )

    lines += ["", "### Wellness (Last 7 Nights)"]
    for night in wellness.get("sleep", []):
        lines.append(
            f"- {night.get('date')}: {night.get('hours')}h sleep, "
            f"quality {night.get('quality', '?')}/5"
        )

    hrv = wellness.get("hrv_trend")
    rhr = wellness.get("rhr_trend")
    if hrv:
        lines.append(f"HRV 7-day trend: {hrv}")
    if rhr:
        lines.append(f"Resting HR 7-day trend: {rhr}")

    if events:
        lines += ["", "### Upcoming Events"]
        for e in events:
            lines.append(f"- {e.get('date')} | {e.get('name')} | {e.get('priority', 'B')}-event")

    return "\n".join(lines)
