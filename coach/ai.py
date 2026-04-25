"""
coach/ai.py
"""
import os
import json
from openai import AsyncOpenAI
from typing import List
from coach.context_builder import build_context
from coach.system_prompt import build_system_prompt
from db.profile import get_profile, patch_profile
from intervals.workouts import (
    create_workout,
    create_structured_workout,
    update_workout,
    move_workout,
    delete_workout,
)

_client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ["GROQ_API_KEY"],
)
MODEL = "llama-3.3-70b-versatile"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_workout",
            "description": "Create a simple unstructured workout on the athlete's Intervals.icu calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                    "sport": {"type": "string", "description": "e.g. Run, Ride, Swim"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "duration_seconds": {"type": "integer"},
                    "target_tss": {"type": "number"},
                },
                "required": ["date", "sport", "name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_structured_workout",
            "description": (
                "Create a structured workout with steps on the Intervals.icu calendar. "
                "Use this for any interval, fartlek, tempo, or structured session. "
                "Always use description_override with full Intervals.icu plain text format. "
                "Format rules: steps start with '-', duration e.g. 10m/30s/1m30, "
                "power e.g. 80% or Z2 or 100w or Ramp 60-80%, "
                "HR e.g. Z2 HR or 75% HR, pace e.g. Z2 Pace or 4:30/km, "
                "cadence e.g. 90rpm, repeats e.g. '6x' on line before steps, "
                "text before duration becomes step label. "
                "Example: 'Warmup\\n- 10m Z1 Pace\\n\\nMain set 6x\\n- 1m Z4 Pace\\n- 2m Z1 Pace\\n\\nCooldown\\n- 10m Z1 Pace'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                    "sport": {"type": "string", "description": "e.g. Run, Ride, Swim"},
                    "name": {"type": "string"},
                    "warmup_mins": {"type": "integer", "description": "Warmup minutes if not using description_override"},
                    "main_set": {"type": "string", "description": "Main set in Intervals plain text format"},
                    "cooldown_mins": {"type": "integer", "description": "Cooldown minutes if not using description_override"},
                    "description_override": {"type": "string", "description": "Full workout in Intervals.icu plain text format — use this for full control"},
                },
                "required": ["date", "sport", "name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_workout",
            "description": "Edit an existing workout on the Intervals.icu calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workout_id": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "duration_seconds": {"type": "integer"},
                    "target_tss": {"type": "number"},
                },
                "required": ["workout_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_workout",
            "description": "Move an existing workout to a different date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workout_id": {"type": "string"},
                    "new_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                },
                "required": ["workout_id", "new_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_workout",
            "description": "Delete a workout from the Intervals.icu calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workout_id": {"type": "string"},
                },
                "required": ["workout_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_athlete_profile",
            "description": "Update one or more fields in the athlete's stored profile.",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_injuries": {"type": "array", "items": {"type": "string"}},
                    "limiters": {"type": "array", "items": {"type": "string"}},
                    "available_days": {"type": "array", "items": {"type": "string"}},
                    "hours_per_week": {"type": "number"},
                },
            },
        },
    },
]


async def get_coach_reply(
    telegram_id: str,
    user_message: str,
    session_history: List[dict],
) -> tuple[str, List[dict]]:
    deep_keywords = ["analyse", "analyze", "analysis", "in depth", "detail", "breakdown", "splits", "laps", "review"]
    needs_deep = any(word in user_message.lower() for word in deep_keywords)

    if needs_deep:
        from coach.context_builder import build_deep_activity_context
        profile_dict, intervals_snapshot = await build_deep_activity_context(telegram_id)
    else:
        reply = _extract_text(response)
        if not reply:
            reply = "Something went wrong — try again."
        messages.append({"role": "assistant", "content": reply})

    system = build_system_prompt(profile_dict, intervals_snapshot)
    messages = list(session_history) + [{"role": "user", "content": user_message}]

    action_keywords = [
        "add", "create", "move", "delete", "cancel", "schedule", "plan", "remove",
        "interval", "fartlek", "tempo", "structured", "workout", "session", "training"
    ]
    use_tools = any(word in user_message.lower() for word in action_keywords)

    try:
        response = await _client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system}, *messages],
            tools=TOOLS if use_tools else None,
        )
    except Exception as e:
        return f"API error: {str(e)}", messages

    if response.choices[0].finish_reason == "tool_calls":
        reply, messages = await _handle_tool_use(
            telegram_id, response, messages, system
        )
    else:
        reply = _extract_text(response)
        if not reply:
            reply = "Something went wrong — try again."
        messages.append({"role": "assistant", "content": reply})

    return reply, messages

async def _handle_tool_use(
    telegram_id: str,
    response,
    messages: List[dict],
    system: str,
) -> tuple[str, List[dict]]:
    tool_results = []

    for choice in response.choices:
        if choice.message.tool_calls:
            for tool_call in choice.message.tool_calls:
                tool_name = tool_call.function.name
                tool_input = json.loads(tool_call.function.arguments)
                result = await _dispatch_tool(telegram_id, tool_name, tool_input)
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

    messages.append({
        "role": "assistant",
        "content": response.choices[0].message.content,
        "tool_calls": response.choices[0].message.tool_calls,
    })
    messages.extend(tool_results)

    follow_up = await _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, *messages],
        tools=TOOLS,
    )
    reply = _extract_text(follow_up)
    if not reply:
        # Model returned empty — summarise what was done from tool results
        done = [json.loads(r["content"]) for r in tool_results]
        names = [d.get("name", "") for d in done if d.get("success")]
        reply = f"Done — added {', '.join(names)} to your calendar." if names else "Done."
    messages.append({"role": "assistant", "content": reply})
    return reply, messages


async def _dispatch_tool(telegram_id: str, tool_name: str, tool_input: dict) -> dict:
    try:
        if tool_name == "create_workout":
            result = await create_workout(**tool_input)
        elif tool_name == "create_structured_workout":
            result = await create_structured_workout(**tool_input)
        elif tool_name == "update_workout":
            result = await update_workout(**tool_input)
        elif tool_name == "move_workout":
            result = await move_workout(**tool_input)
        elif tool_name == "delete_workout":
            result = await delete_workout(**tool_input)
        elif tool_name == "update_athlete_profile":
            patch_profile(telegram_id, tool_input)
            result = {"success": True, "updated": list(tool_input.keys())}
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        result = {"error": str(e)}

    return result


def _extract_text(response) -> str:
    try:
        content = response.choices[0].message.content
        if content and content.strip():
            return content.strip()
    except (IndexError, AttributeError):
        pass
    return None

async def analyse_activity(
    activity: dict,
    profile_dict: dict,
    intervals_snapshot: dict,
) -> str:
    system = (
        "You are an experienced endurance coach writing a concise post-activity analysis. "
        "Be specific, data-driven, and actionable. 200-300 words. Use the athlete's first name. "
        "Structure: what went well, pacing/power/HR review, recovery recommendation, "
        "how it fits the training plan. Plain text suitable for email."
    )

    prompt = f"""Athlete profile:
{json.dumps(profile_dict, indent=2)}

Current fitness snapshot:
{json.dumps(intervals_snapshot.get('fitness', {}), indent=2)}

Completed activity:
{json.dumps(activity, indent=2)}

Write the post-activity analysis."""

    response = await _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    )

    return _extract_text(response)