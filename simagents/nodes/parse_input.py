"""Parse input node — detects paper/chat/hybrid mode."""
from __future__ import annotations
from simagents.graph.state import ExtractionState


def parse_input(state: ExtractionState) -> dict:
    has_paper = bool(state.get("paper_path"))
    has_params = bool(state.get("user_parameters"))
    if has_paper and has_params:
        mode = "hybrid"
    elif has_paper:
        mode = "paper"
    elif has_params:
        mode = "chat"
    else:
        raise ValueError("No input provided. Supply paper_path, user_parameters, or both.")
    return {"input_mode": mode, "iteration": 0}
