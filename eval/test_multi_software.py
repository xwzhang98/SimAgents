"""Test extraction with different target software (no golden standard — manual review)."""
from __future__ import annotations
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from eval.evaluate import run_single_extraction

TESTS = [
    {
        "name": "IllustrisTNG → Arepo",
        "paper": "example/IllustrisTNG_Pillepich2018.pdf",
        "software": "arepo",
        "prompt": "Extract parameters for the TNG100-1 simulation run",
    },
    {
        "name": "FLAMINGO → SWIFT",
        "paper": "example/FLAMINGO_Schaye2023.pdf",
        "software": "swift",
        "prompt": "Extract parameters for the L1000N1800 FLAMINGO simulation",
    },
    {
        "name": "FIRE-2 → GIZMO",
        "paper": "example/FIRE2_Hopkins2018.pdf",
        "software": "gizmo",
        "prompt": "Extract cosmological parameters for the FIRE-2 simulations",
    },
]


def run_test(test: dict):
    print(f"\n{'='*60}")
    print(f"Testing: {test['name']}")
    print(f"Software: {test['software']}")
    print(f"{'='*60}")

    paper_path = str(PROJECT_ROOT / test["paper"])
    if not Path(paper_path).exists():
        print(f"SKIP: {test['paper']} not found")
        return

    result = run_single_extraction(paper_path, test["software"], test["prompt"])
    formatted = result.get("formatted_parameters", {})

    print(f"\nStatus: {result.get('status', 'unknown')}")

    sections = formatted.get("sections", {})
    for sec_name, sec_params in sections.items():
        if isinstance(sec_params, dict) and sec_params:
            print(f"\n[{sec_name}]")
            for k, v in sec_params.items():
                print(f"  {k}: {v}")

    ic_notes = formatted.get("ic_notes", [])
    if ic_notes:
        print(f"\nIC Notes: {ic_notes}")

    missing = result.get("missing_parameters", [])
    if missing:
        print(f"\nMissing: {missing}")

    # Basic sanity checks
    all_params = {}
    for sec in sections.values():
        if isinstance(sec, dict):
            all_params.update(sec)

    checks_passed = 0
    checks_total = 0

    # Check cosmological params exist
    cosmo_keys = ["Omega0", "OmegaLambda", "HubbleParam", "Omega_cdm", "Omega_lambda", "h"]
    has_cosmo = any(k in all_params for k in cosmo_keys)
    checks_total += 1
    if has_cosmo:
        checks_passed += 1
        print("\n✓ Has cosmological parameters")
    else:
        print("\n✗ Missing cosmological parameters")

    # Check box size or resolution
    box_keys = ["BoxSize", "Ngrid", "GridSize"]
    has_box = any(k in all_params for k in box_keys)
    checks_total += 1
    if has_box:
        checks_passed += 1
        print("✓ Has box size or resolution")
    else:
        print("✗ Missing box size or resolution")

    # Check no None values
    none_count = sum(1 for v in all_params.values() if v is None)
    checks_total += 1
    if none_count == 0:
        checks_passed += 1
        print("✓ No None values")
    else:
        print(f"✗ {none_count} None values found")

    print(f"\nSanity: {checks_passed}/{checks_total} checks passed")
    return formatted


if __name__ == "__main__":
    for test in TESTS:
        try:
            run_test(test)
        except Exception as e:
            print(f"ERROR: {e}")
