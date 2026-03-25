"""Profile-driven parameter validation and auto-correction.

All validation rules come from the SoftwareProfile — no hardcoded physics.
"""
from __future__ import annotations
import math
from simagents.profiles.loader import SoftwareProfile, ValidationConfig


def validate_and_correct(
    sections: dict, profile: SoftwareProfile
) -> tuple[dict, list[str]]:
    """Validate and auto-correct parameters using profile rules.

    Returns (corrected_sections, list_of_issues).
    """
    issues: list[str] = []
    vc = profile.validation

    # Swap detection
    for rule in vc.swap_detection:
        pair = rule["pair"]
        if len(pair) != 2:
            continue
        key_a, key_b = pair[0], pair[1]
        for sec_params in sections.values():
            if not isinstance(sec_params, dict):
                continue
            if key_a in sec_params and key_b in sec_params:
                val_a = _safe_float(sec_params[key_a])
                val_b = _safe_float(sec_params[key_b])
                if val_a is not None and val_b is not None and val_a > 0.5 and val_b < 0.5:
                    sec_params[key_a], sec_params[key_b] = sec_params[key_b], sec_params[key_a]
                    issues.append(
                        f"Swapped {key_a} and {key_b}: {rule.get('rule', 'values were reversed')}"
                    )

    # Large value corrections (e.g. Ngrid cube root)
    for rule in vc.large_value_corrections:
        params = rule.get("params", [])
        threshold = rule.get("threshold", 50000)
        action = rule.get("action", "")
        for sec_params in sections.values():
            if not isinstance(sec_params, dict):
                continue
            for key in params:
                if key not in sec_params:
                    continue
                val = _safe_float(sec_params[key])
                if val is None or val <= threshold:
                    continue
                if action == "cube_root":
                    cube_root = round(val ** (1 / 3))
                    if abs(cube_root**3 - val) < val * 0.01:
                        sec_params[key] = cube_root
                        issues.append(
                            f"Corrected {key}: {val} -> {cube_root} ({rule.get('reason', 'cube root')})"
                        )

    # Range validation (report only, auto-correct already handled swaps)
    for param_name, (lo, hi) in vc.parameter_ranges.items():
        for sec_params in sections.values():
            if not isinstance(sec_params, dict):
                continue
            if param_name not in sec_params:
                continue
            val = _safe_float(sec_params[param_name])
            if val is not None and (val < lo or val > hi):
                issues.append(
                    f"{param_name}={val} outside expected range [{lo}, {hi}]"
                )

    # Remove None values (universal)
    for sec_name, sec_params in sections.items():
        if isinstance(sec_params, dict):
            sections[sec_name] = {k: v for k, v in sec_params.items() if v is not None}

    return sections, issues


def generate_validation_rules_text(profile: SoftwareProfile) -> str:
    """Generate human-readable validation rules for prompt injection."""
    vc = profile.validation
    if not vc.parameter_ranges and not vc.swap_detection and not vc.large_value_corrections:
        return ""

    lines = ["## Validation Rules (from software profile)"]

    for param_name, (lo, hi) in vc.parameter_ranges.items():
        lines.append(f"- {param_name} must be in range [{lo}, {hi}].")

    for rule in vc.swap_detection:
        pair = rule["pair"]
        if len(pair) == 2:
            lines.append(
                f"- If {pair[0]} > 0.5 and {pair[1]} < 0.5, you likely swapped them. "
                f"{rule.get('rule', '')}"
            )

    for rule in vc.large_value_corrections:
        params = ", ".join(rule.get("params", []))
        threshold = rule.get("threshold", 50000)
        reason = rule.get("reason", "check the value")
        lines.append(f"- {params}: if > {threshold}, {reason}.")

    return "\n".join(lines)


def _safe_float(val) -> float | None:
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
