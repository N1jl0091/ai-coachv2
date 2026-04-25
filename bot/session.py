"""
bot/session.py
Per-conversation in-memory state. Resets when the process restarts or a new session starts.
Keeps last N messages for context continuity within a session.
"""
from typing import Dict, List
import time

_sessions: dict = {}
MAX_HISTORY = 20
SESSION_TIMEOUT = 7200  # 2 hours

def get_session(telegram_id: str) -> dict:
    session = _sessions.get(telegram_id)
    if not session:
        _sessions[telegram_id] = {"history": [], "last_active": time.time()}
        return _sessions[telegram_id]
    # Auto-reset if inactive for 2 hours
    if time.time() - session.get("last_active", 0) > SESSION_TIMEOUT:
        _sessions[telegram_id] = {"history": [], "last_active": time.time()}
    return _sessions[telegram_id]


def update_session(telegram_id: str, new_history: list):
    trimmed = new_history[-MAX_HISTORY:]
    _sessions[telegram_id] = {"history": trimmed, "last_active": time.time()}


def clear_session(telegram_id: str):
    _sessions.pop(telegram_id, None)
