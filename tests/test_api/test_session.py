"""Tests for the API session manager."""
from unittest.mock import MagicMock
from simagents.api.session import ExtractionSession, SessionManager, session_manager

def test_session_manager_create_session():
    mgr = SessionManager()
    sid = mgr.create_session(graph=MagicMock(), config={"configurable": {}}, file_path="/fake/paper.pdf")
    assert sid is not None
    session = mgr.get_session(sid)
    assert session.file_path == "/fake/paper.pdf"
    assert session.status == "idle"

def test_session_manager_one_active_session():
    mgr = SessionManager()
    sid1 = mgr.create_session(graph=MagicMock(), config={}, file_path=None)
    sid2 = mgr.create_session(graph=MagicMock(), config={}, file_path=None)
    assert mgr.get_session(sid1) is None
    assert mgr.get_session(sid2) is not None

def test_session_manager_get_current():
    mgr = SessionManager()
    assert mgr.get_current() is None
    sid = mgr.create_session(graph=MagicMock(), config={}, file_path=None)
    assert mgr.get_current().session_id == sid

def test_module_level_singleton():
    assert session_manager is not None
    assert isinstance(session_manager, SessionManager)
