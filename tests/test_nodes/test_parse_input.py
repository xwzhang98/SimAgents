"""Tests for parse_input node."""
import pytest
from simagents.nodes.parse_input import parse_input

def test_parse_input_paper_mode():
    state = {"paper_path": "/path/paper.pdf", "user_parameters": None}
    result = parse_input(state)
    assert result["input_mode"] == "paper"

def test_parse_input_chat_mode():
    state = {"paper_path": None, "user_parameters": {"BoxSize": 100000}}
    result = parse_input(state)
    assert result["input_mode"] == "chat"

def test_parse_input_hybrid_mode():
    state = {"paper_path": "/path/paper.pdf", "user_parameters": {"BoxSize": 100000}}
    result = parse_input(state)
    assert result["input_mode"] == "hybrid"

def test_parse_input_no_input_raises():
    state = {"paper_path": None, "user_parameters": None}
    with pytest.raises(ValueError, match="No input provided"):
        parse_input(state)
