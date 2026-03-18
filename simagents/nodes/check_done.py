"""check_done routing node — pure logic, no LLM call."""
from __future__ import annotations
from simagents.graph.state import ExtractionState


def check_done(state: ExtractionState) -> str:
    status = state.get("status", "incomplete")
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 2)
    if status == "complete":
        return "done"
    if iteration >= max_iterations:
        return "done"
    if status == "needs_user_input":
        return "needs_user_input"
    return "loop"
