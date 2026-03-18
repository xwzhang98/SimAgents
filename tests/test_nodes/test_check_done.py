"""Tests for check_done routing node."""
from simagents.nodes.check_done import check_done

def test_check_done_complete():
    assert check_done({"status": "complete", "iteration": 1, "max_iterations": 2}) == "done"

def test_check_done_max_iterations_reached():
    assert check_done({"status": "incomplete", "iteration": 2, "max_iterations": 2}) == "done"

def test_check_done_needs_user_input():
    assert check_done({"status": "needs_user_input", "iteration": 0, "max_iterations": 2}) == "needs_user_input"

def test_check_done_loop():
    assert check_done({"status": "incomplete", "iteration": 0, "max_iterations": 2}) == "loop"
