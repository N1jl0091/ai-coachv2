"""
coach/system_prompt.py
"""
from datetime import date


def build_system_prompt(profile: dict, intervals_snapshot: dict) -> str:
    profile_block = _format_profile(profile)
    intervals_block = _format_intervals(intervals_snapshot)
    today = date.today().isoformat()

    return f"""You are an experienced multi-sport endurance coach. Today is {today}.

You are direct, concise, and proactive. You talk like a real coach texting an athlete — short, clear, no waffle. Use the athlete's first name naturally.

## Communication rules
- Keep responses under 100 words unless asked for a detailed plan
- Never ask questions at the end
- Never ask for confirmation — act and then briefly confirm
- No bullet points for casual conversation
- Do not explain reasoning unless asked

## Tool usage (CRITICAL — follow exactly)

When you decide to act, you MUST call a tool using valid JSON arguments.

Rules:
- Only call a tool if you are confident in all required fields
- If unsure → respond normally instead (do NOT call a tool)
- NEVER invent or guess IDs
- NEVER output XML or text tool formats

### Field constraints
- sport MUST be exactly one of: "Run", "Ride", "Swim", "Other"
- date MUST be YYYY-MM-DD
- description_override MUST be a valid Intervals.icu workout

### Structured workouts (IMPORTANT)
Always use create_structured_workout for:
- intervals
- tempo
- fartlek
- workouts with structure

You MUST include description_override.

Format:
Warmup
- 10m Z1 Pace

Main set 6x
- 1m Z4 Pace
- 2m Z1 Pace

Cooldown
- 10m Z1 Pace

## Capabilities — act without asking permission
- Create, edit, move, delete workouts
- Update athlete profile when relevant

If asked to plan:
→ create workouts immediately via tools
→ then confirm briefly

## Wellness rules (apply automatically)
- HRV suppressed → easy or rest
- Sleep <7h → reduce intensity
- TSB < -25 → recovery
- Ramp > 8 → flag overreaching

## Guardrails
- Max 10% weekly volume increase
- Modify around injuries
- Never train through pain

---

## Athlete Profile
{profile_block}

---

## Live Training Data
{intervals_block}

---

Be decisive. Act cleanly. Only call tools when correct.
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
        f"Injuries: {', '.join(p.get('current_injuries') or []) or 'None'}",
        f"Limiters: {', '.join(p.get('limiters') or []) or 'None'}",
        f"Preferred long day: {p.get('preferred_long_day', 'Sunday')}",
        f"Intensity model: {p.get('preferred_intensity', 'mixed')}",
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
        f"CTL: {fitness.get('ctl', 'N/A')} | ATL: {fitness.get('atl', 'N/A')} | TSB: {fitness.get('tsb', 'N/A')} | Ramp: {fitness.get('ramp_rate', 'N/A')}/week",
        f"Phase: {fitness.get('phase', 'N/A')}",
        "",
        "### Last 7 Days",
    ]
    if workouts:
        for w in workouts:
            lines.append(
                f"- {w.get('date')} {w.get('sport')} {w.get('name')} "
                f"{w.get('duration_min')}min TSS:{w.get('tss', '?')} HR:{w.get('avg_hr', '?')}"
            )
    else:
        lines.append("- No recent workouts")

    lines += ["", "### Planned"]
    if planned:
        for w in planned:
            lines.append(f"- {w.get('date')} {w.get('sport')} {w.get('name')} ~{w.get('duration_min')}min")
    else:
        lines.append("- Nothing planned")

    lines += ["", "### Wellness"]
    for night in wellness.get("sleep", [])[-3:]:
        lines.append(f"- {night.get('date')}: {night.get('hours')}h sleep quality {night.get('quality', '?')}/5")

    hrv = wellness.get("hrv_trend")
    rhr = wellness.get("rhr_trend")
    if hrv:
        lines.append(f"HRV trend: {hrv}")
    if rhr:
        lines.append(f"RHR trend: {rhr}")

    if events:
        lines += ["", "### Events"]
        for e in events:
            lines.append(f"- {e.get('date')} {e.get('name')}")

    detailed = s.get("detailed_activities", [])
    if detailed:
        lines += ["", "### Detailed Activity Breakdown"]
        for a in detailed:
            lines.append(f"**{a.get('date')} {a.get('name')}**")
            lines.append(f"  Notes: {a.get('notes') or 'None'} | RPE: {a.get('perceived_exertion') or '?'} | Feel: {a.get('feel') or '?'}")
            for lap in (a.get("laps") or [])[:10]:
                lines.append(
                    f"  Lap {lap.get('lap_index', '?')}: "
                    f"{round((lap.get('elapsed_time', 0))/60, 1)}min "
                    f"HR:{lap.get('average_heartrate', '?')} "
                    f"Pace:{lap.get('average_speed', '?')}"
                )

    return "\n".join(lines)