import asyncio
import time
from typing import Dict, Any, List

_sessions: Dict[str, Dict[str, Any]] = {}
_session_lock = asyncio.Lock()


def get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "memory": {},
            "history": [],
            "coords": None,
            "updated_at": time.time(),
        }
    return _sessions[session_id]


def get_session_history(session_id: str) -> List[Dict[str, str]]:
    return list(get_session(session_id).get("history", []))


def get_session_memory(session_id: str) -> Dict[str, Any]:
    return dict(get_session(session_id).get("memory", {}))


def append_history(session_id: str, user_message: str, assistant_reply: str) -> None:
    session = get_session(session_id)
    history = session.setdefault("history", [])
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": assistant_reply})
    if len(history) > 40:
        session["history"] = history[-40:]
    session["updated_at"] = time.time()


def update_memory(session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    session = get_session(session_id)
    memory = session.setdefault("memory", {})
    for key, value in payload.items():
        if value is not None:
            memory[key] = value
    session["updated_at"] = time.time()
    return memory
