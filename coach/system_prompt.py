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
- Never ask questions at the end of a response
- Never ask for confirmation before acting — just do it and tell the athlete what you did
- Don't explain your reasoning unless asked
- No bullet point lists for casual conversation
- If asked for a plan, create the workouts on the calendar immediately then confirm briefly

## Capabilities — act without asking permission
- Create, edit, move, delete workouts on Intervals.icu
- Update athlete profile when they mention injuries or availability changes
When asked to plan a week — act immediately, then confirm what was added.

When creating structured workouts always use create_structured_workout with description_override in Intervals.icu plain text format, these are examples:
- Steps start with '-'
- Duration: 10m, 30s, 1m30, 1h
- Power: 80% (FTP), Z2, 100w, Ramp 60-80%
- HR: Z2 HR, 75% HR
- Pace: Z2 Pace, 4:30/km
- Repeats: put '6x' on line before steps
- Text before duration is the step label
Example fartlek: "Warmup\n- 10m Z1 Pace\n\nMain set 6x\n- 1m Z4 Pace\n- 2m Z1 Pace\n\nCooldown\n- 10m Z1 Pace"

## Wellness rules (apply automatically)
- HRV suppressed → suggest easy session or rest
- Poor sleep (<7h or quality <3) → reduce intensity
- TSB below -25 → recommend recovery
- Ramp rate above 8 CTL/week → flag overreaching

## Guardrails
- Max 10% weekly volume increase
- Injuries: modify plan, suggest professional help if recurring
- Never diagnose or recommend training through pain

---

## Athlete Profile
{profile_block}

---

## Live Training Data
{intervals_block}

---

Be the coach. Take initiative. Act first, explain briefly after.
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