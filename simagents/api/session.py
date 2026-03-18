"""Extraction session management for the API."""
from __future__ import annotations
import os
import uuid
from dataclasses import dataclass, field


@dataclass
class ExtractionSession:
    session_id: str
    graph: object
    config: dict
    file_path: str | None = None
    parameters: dict = field(default_factory=lambda: {"genic": {}, "gadget": {}})
    messages: list[dict] = field(default_factory=list)
    status: str = "idle"
    _initial_state: dict | None = field(default=None, repr=False)
    _resume_value: dict | None = field(default=None, repr=False)


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, ExtractionSession] = {}
        self._current_id: str | None = None

    def create_session(self, graph, config: dict, file_path: str | None = None) -> str:
        if self._current_id and self._current_id in self._sessions:
            del self._sessions[self._current_id]
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = ExtractionSession(
            session_id=session_id, graph=graph, config=config, file_path=file_path,
        )
        self._current_id = session_id
        return session_id

    def get_session(self, session_id: str) -> ExtractionSession | None:
        return self._sessions.get(session_id)

    def get_current(self) -> ExtractionSession | None:
        if self._current_id:
            return self._sessions.get(self._current_id)
        return None

    def cleanup(self):
        for session in self._sessions.values():
            if session.file_path and os.path.exists(session.file_path):
                try:
                    os.unlink(session.file_path)
                except OSError:
                    pass
        self._sessions.clear()
        self._current_id = None


# Module-level singleton
session_manager = SessionManager()
