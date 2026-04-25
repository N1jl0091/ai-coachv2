"""
coach/ai.py
Claude API calls. Handles message routing, tool use (Intervals write ops), and profile updates.
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
    update_workout,
    move_workout,
    delete_workout,
)

_client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ["GROQ_API_KEY"],
)
MODEL = "deepseek-r1-distill-llama-70b"


# ── Tool definitions for Intervals.icu write operations ───────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_workout",
            "description": "Create a new workout on the athlete's Intervals.icu calendar.",
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
    """
    Main entry point for the chat loop.
    Returns (reply_text, updated_history).
    """
    profile_dict, intervals_snapshot = await build_context(telegram_id)
    system = build_system_prompt(profile_dict, intervals_snapshot)

    # Build message list
    messages = list(session_history) + [{"role": "user", "content": user_message}]
    
    response = await _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, *messages],
        tools=TOOLS,
    )

    # Handle tool use
    if response.choices[0].finish_reason == "tool_calls":
        reply, messages = await _handle_tool_use(
            telegram_id, response, messages, system
        )
    else:
        reply = _extract_text(response)
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

    # Append assistant message and tool results
    messages.append({"role": "assistant", "content": response.choices[0].message.content, "tool_calls": response.choices[0].message.tool_calls})
    messages.extend(tool_results)

    follow_up = await _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, *messages],
        tools=TOOLS,
    )
    reply = _extract_text(follow_up)
    messages.append({"role": "assistant", "content": reply})
    return reply, messages


async def _dispatch_tool(telegram_id: str, tool_name: str, tool_input: dict) -> dict:
    """Route tool calls to the appropriate function."""
    try:
        if tool_name == "create_workout":
            result = await create_workout(**tool_input)
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
    return response.choices[0].message.content or "Sorry, I couldn't generate a response."

# ── Activity analysis (used by Strava webhook) ────────────────────────────────

async def analyse_activity(
    activity: dict,
    profile_dict: dict,
    intervals_snapshot: dict,
) -> str:
    """
    Generate a 200-300 word post-activity analysis email body.
    """
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
