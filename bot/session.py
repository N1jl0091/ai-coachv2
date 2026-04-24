"""
bot/session.py
Per-conversation in-memory state. Resets when the process restarts or a new session starts.
Keeps last N messages for context continuity within a session.
"""
from typing import Dict, List

_sessions: Dict[str, dict] = {}
MAX_HISTORY = 20  # messages (user+assistant pairs counted individually)


def get_session(telegram_id: str) -> dict:
    if telegram_id not in _sessions:
        _sessions[telegram_id] = {"history": []}
    return _sessions[telegram_id]


def update_session(telegram_id: str, new_history: List[dict]):
    """Replace the history for this user, trimming to MAX_HISTORY."""
    trimmed = new_history[-MAX_HISTORY:]
    _sessions[telegram_id] = {"history": trimmed}


def clear_session(telegram_id: str):
    _sessions.pop(telegram_id, None)
