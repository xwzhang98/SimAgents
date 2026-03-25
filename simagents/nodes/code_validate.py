"""code_validate — profile-driven validation of extracted parameters.

No LLM calls. Uses profile validation rules to check parameters.
Returns routing decision: "done", "retry", or "needs_user_input".
"""
from __future__ import annotations

from simagents.graph.state import ExtractionState
from simagents.profiles.validator import validate_and_correct, _safe_float


def code_validate(state: ExtractionState, profile=None) -> str:
    """Validate extracted parameters and route accordingly.

    Returns:
        "done" — validation passed or max iterations reached
        "retry" — validation failed, should retry extraction
        "needs_user_input" — user input required
    """
    status = state.get("status", "incomplete")
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 2)

    if status == "needs_user_input":
        return "needs_user_input"

    if iteration >= max_iterations:
        return "done"

    formatted = state.get("formatted_parameters", {})
    sections = formatted.get("sections", {})

    if not sections or not any(bool(v) for v in sections.values()):
        return "retry" if iteration < max_iterations else "done"

    # Use profile-driven validation if available
    if profile:
        _, issues = validate_and_correct(dict(sections), profile)
        if issues and iteration < max_iterations:
            return "retry"
        return "done"

    # Fallback: minimal check without profile
    all_params = {}
    for sec_params in sections.values():
        if isinstance(sec_params, dict):
            all_params.update(sec_params)

    if any(v is None for v in all_params.values()):
        return "retry" if iteration < max_iterations else "done"

    return "done"


def validate_and_get_issues(state: ExtractionState, profile=None) -> list[str]:
    """Get a list of validation issues (for feedback to retry)."""
    formatted = state.get("formatted_parameters", {})
    sections = formatted.get("sections", {})

    if profile:
        _, issues = validate_and_correct(dict(sections), profile)
        return [f"VALIDATION ERROR: {issue}" for issue in issues]

    # Fallback without profile
    all_params = {}
    for sec_params in sections.values():
        if isinstance(sec_params, dict):
            all_params.update(sec_params)

    issues = []
    for k, v in all_params.items():
        if v is None:
            issues.append(f"VALIDATION ERROR: {k} is None — remove it or provide a value")
    return issues
