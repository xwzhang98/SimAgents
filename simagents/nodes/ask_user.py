"""ask_user node — human-in-the-loop interrupt for missing parameters."""
from __future__ import annotations
from langgraph.types import interrupt
from simagents.graph.state import ExtractionState


def ask_user(state: ExtractionState) -> dict:
    questions = state.get("user_questions", [])
    missing = state.get("missing_parameters", [])
    prompt_parts = []
    if questions:
        prompt_parts.append("The following questions need your input:")
        for q in questions:
            prompt_parts.append(f"  - {q}")
    if missing:
        prompt_parts.append(f"\nMissing required parameters: {', '.join(missing)}")
        prompt_parts.append("Please provide values for these parameters.")
    prompt = "\n".join(prompt_parts)
    user_response = interrupt(prompt)
    answers = state.get("user_answers", [])
    if isinstance(user_response, dict):
        answers = answers + [user_response]
    else:
        answers = answers + [{"raw_response": user_response}]
    return {"user_answers": answers}
