"""
coach/ai.py
"""

import os
import json
from typing import List, Tuple

from openai import AsyncOpenAI

from coach.context_builder import build_context
from coach.system_prompt import build_system_prompt
from db.profile import patch_profile
from intervals.workouts import (
    create_workout,
    create_structured_workout,
    update_workout,
    move_workout,
    delete_workout,
)

# ------------------------
# CONFIG
# ------------------------

_client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ["GROQ_API_KEY"],
)

MODEL = "llama-3.3-70b-versatile"

# ------------------------
# TOOL DEFINITIONS
# ------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_workout",
            "description": "Create a simple unstructured workout.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "sport": {"type": "string"},
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
            "description": "Create a structured workout (intervals, tempo, etc). Always prefer description_override.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "sport": {"type": "string"},
                    "name": {"type": "string"},
                    "description_override": {"type": "string"},
                },
                "required": ["date", "sport", "name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_workout",
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
            "parameters": {
                "type": "object",
                "properties": {
                    "workout_id": {"type": "string"},
                    "new_date": {"type": "string"},
                },
                "required": ["workout_id", "new_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_workout",
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

# ------------------------
# MAIN ENTRY
# ------------------------

async def get_coach_reply(
    telegram_id: str,
    user_message: str,
    session_history: List[dict],
) -> Tuple[str, List[dict]]:

    # 1. Build context (ALWAYS first)
    profile_dict, intervals_snapshot = await build_context(telegram_id)
    system = build_system_prompt(profile_dict, intervals_snapshot)

    # 2. Build message stack
    messages = list(session_history) + [
        {"role": "user", "content": user_message}
    ]

    # 3. Decide tool usage
    use_tools = _should_use_tools(user_message)

    # 4. First model call
    try:
        response = await _client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system}, *messages],
            tools=TOOLS if use_tools else None,
        )
    except Exception as e:
        return f"API error: {str(e)}", messages

    # 5. Tool handling or normal reply
    if _has_tool_calls(response):
        return await _handle_tool_flow(
            telegram_id, response, messages, system
        )

    reply = _extract_text(response) or "Something went wrong — try again."
    messages.append({"role": "assistant", "content": reply})

    return reply, messages


# ------------------------
# TOOL FLOW
# ------------------------

async def _handle_tool_flow(
    telegram_id: str,
    response,
    messages: List[dict],
    system: str,
) -> Tuple[str, List[dict]]:

    tool_messages = []

    for tool_call in response.choices[0].message.tool_calls:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)

        result = await _dispatch_tool(telegram_id, name, args)

        tool_messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result),
        })

    # Append assistant tool request
    messages.append({
        "role": "assistant",
        "content": response.choices[0].message.content,
        "tool_calls": response.choices[0].message.tool_calls,
    })

    messages.extend(tool_messages)

    # Follow-up call
    try:
        follow_up = await _client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system}, *messages],
            tools=TOOLS,
        )
    except Exception as e:
        reply = f"Tool executed but follow-up failed: {str(e)}"
        messages.append({"role": "assistant", "content": reply})
        return reply, messages

    reply = _extract_text(follow_up) or "Done."
    messages.append({"role": "assistant", "content": reply})

    return reply, messages


# ------------------------
# TOOL DISPATCH
# ------------------------

async def _dispatch_tool(
    telegram_id: str,
    tool_name: str,
    tool_input: dict
) -> dict:

    try:
        if tool_name == "create_workout":
            return await create_workout(**tool_input)

        if tool_name == "create_structured_workout":
            return await create_structured_workout(**tool_input)

        if tool_name == "update_workout":
            return await update_workout(**tool_input)

        if tool_name == "move_workout":
            return await move_workout(**tool_input)

        if tool_name == "delete_workout":
            return await delete_workout(**tool_input)

        if tool_name == "update_athlete_profile":
            patch_profile(telegram_id, tool_input)
            return {"success": True}

        return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        return {"error": str(e)}


# ------------------------
# HELPERS
# ------------------------

def _extract_text(response) -> str | None:
    try:
        content = response.choices[0].message.content
        return content.strip() if content else None
    except Exception:
        return None


def _has_tool_calls(response) -> bool:
    try:
        return bool(response.choices[0].message.tool_calls)
    except Exception:
        return False


def _should_use_tools(message: str) -> bool:
    keywords = [
        "add", "create", "move", "delete",
        "schedule", "plan", "remove",
        "interval", "tempo", "workout"
    ]
    return any(k in message.lower() for k in keywords)


# ------------------------
# ACTIVITY ANALYSIS
# ------------------------

async def analyse_activity(
    activity: dict,
    profile_dict: dict,
    intervals_snapshot: dict,
) -> str:

    system = (
        "You are an endurance coach. Write a concise, data-driven analysis "
        "(200–300 words). Include: performance, pacing, recovery, next steps."
    )

    prompt = f"""
Profile:
{json.dumps(profile_dict, indent=2)}

Fitness:
{json.dumps(intervals_snapshot.get('fitness', {}), indent=2)}

Activity:
{json.dumps(activity, indent=2)}
"""

    response = await _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )

    return _extract_text(response) or "Analysis unavailable."