"""Tests for ask_user node."""
from unittest.mock import patch
from simagents.nodes.ask_user import ask_user

def test_ask_user_builds_prompt_and_returns_answers():
    state = {"user_questions": ["What BoxSize do you want?"], "missing_parameters": ["BoxSize", "Omega0"], "user_answers": []}
    with patch("simagents.nodes.ask_user.interrupt", return_value={"BoxSize": 100000, "Omega0": 0.3}):
        result = ask_user(state)
    assert len(result["user_answers"]) == 1
    assert result["user_answers"][0]["BoxSize"] == 100000

def test_ask_user_handles_string_response():
    state = {"user_questions": [], "missing_parameters": ["BoxSize"], "user_answers": []}
    with patch("simagents.nodes.ask_user.interrupt", return_value="BoxSize should be 100000"):
        result = ask_user(state)
    assert result["user_answers"][0]["raw_response"] == "BoxSize should be 100000"
