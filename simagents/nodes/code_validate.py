"""code_validate — pure Python validation of extracted parameters.

No LLM calls. Checks types, ranges, consistency, and required params.
Returns routing decision: "done", "retry", or "needs_user_input".
"""
from __future__ import annotations

from simagents.graph.state import ExtractionState


def code_validate(state: ExtractionState) -> str:
    """Validate extracted parameters and route accordingly.

    Returns:
        "done" — validation passed or max iterations reached
        "retry" — validation failed, should retry extraction
        "needs_user_input" — user input required
    """
    status = state.get("status", "incomplete")
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 2)

    # If user input needed, route to ask_user
    if status == "needs_user_input":
        return "needs_user_input"

    # If max iterations reached, stop regardless
    if iteration >= max_iterations:
        return "done"

    # If status is complete, validate the values
    formatted = state.get("formatted_parameters", {})
    sections = formatted.get("sections", {})

    if not sections or not any(bool(v) for v in sections.values()):
        # No parameters at all — retry if we can
        return "retry" if iteration < max_iterations else "done"

    # Collect all params across sections
    all_params = {}
    for sec_params in sections.values():
        if isinstance(sec_params, dict):
            all_params.update(sec_params)

    issues = []

    # Check Omega swap
    omega0 = _get_float(all_params, ["Omega0", "Omega_cdm", "Omega_m"])
    omega_lambda = _get_float(all_params, ["OmegaLambda", "Omega_lambda", "Omega_Lambda"])

    if omega0 is not None and omega0 > 0.5:
        issues.append(f"Omega0={omega0} > 0.5 — likely swapped with OmegaLambda")
    if omega_lambda is not None and omega_lambda < 0.5:
        issues.append(f"OmegaLambda={omega_lambda} < 0.5 — likely swapped with Omega0")

    # Check h range
    h = _get_float(all_params, ["HubbleParam", "h", "Hubble"])
    if h is not None and (h < 0.5 or h > 1.0):
        issues.append(f"HubbleParam={h} outside expected range [0.5, 1.0]")

    # Check for None values
    for k, v in all_params.items():
        if v is None:
            issues.append(f"{k} is None — should be omitted or have a value")

    # Check Ngrid reasonability
    ngrid = _get_float(all_params, ["Ngrid", "GridSize", "Nmesh"])
    if ngrid is not None and ngrid > 50000:
        issues.append(f"Ngrid={ngrid} seems too large — may be N³ instead of N")

    # If there are validation issues and we have retries left, retry
    if issues and iteration < max_iterations:
        # Store issues as feedback for the next extraction
        current_missing = state.get("missing_parameters", [])
        return "retry"

    return "done"


def validate_and_get_issues(state: ExtractionState) -> list[str]:
    """Get a list of validation issues (for feedback to retry)."""
    formatted = state.get("formatted_parameters", {})
    sections = formatted.get("sections", {})
    all_params = {}
    for sec_params in sections.values():
        if isinstance(sec_params, dict):
            all_params.update(sec_params)

    issues = []

    omega0 = _get_float(all_params, ["Omega0", "Omega_cdm", "Omega_m"])
    omega_lambda = _get_float(all_params, ["OmegaLambda", "Omega_lambda", "Omega_Lambda"])
    if omega0 is not None and omega0 > 0.5:
        issues.append(f"VALIDATION ERROR: Omega0={omega0} > 0.5 — matter density should be ~0.3, dark energy ~0.7. You likely swapped them.")
    if omega_lambda is not None and omega_lambda < 0.5:
        issues.append(f"VALIDATION ERROR: OmegaLambda={omega_lambda} < 0.5 — dark energy should be ~0.7, matter ~0.3. You likely swapped them.")

    h = _get_float(all_params, ["HubbleParam", "h", "Hubble"])
    if h is not None and (h < 0.5 or h > 1.0):
        issues.append(f"VALIDATION ERROR: HubbleParam={h} outside [0.5, 1.0]")

    for k, v in all_params.items():
        if v is None:
            issues.append(f"VALIDATION ERROR: {k} is None — remove it or provide a value")

    ngrid = _get_float(all_params, ["Ngrid", "GridSize", "Nmesh"])
    if ngrid is not None and ngrid > 50000:
        issues.append(f"VALIDATION ERROR: Ngrid={ngrid} too large — if the paper says N³, use N not N³")

    return issues


def _get_float(params: dict, keys: list[str]) -> float | None:
    """Try to get a float value from params using multiple possible key names."""
    for k in keys:
        if k in params:
            try:
                return float(params[k])
            except (ValueError, TypeError):
                pass
    return None
