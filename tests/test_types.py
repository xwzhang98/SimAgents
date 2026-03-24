"""Tests for ExtractionInput and ExtractionOutput type contracts."""
from simagents.types import ExtractionInput, ExtractionOutput


def test_extraction_input_paper_mode():
    inp: ExtractionInput = {
        "paper_path": "/path/to/paper.pdf",
        "user_parameters": None,
        "target_software": "mp-gadget",
        "custom_prompt": None,
    }
    assert inp["paper_path"] == "/path/to/paper.pdf"
    assert inp["target_software"] == "mp-gadget"


def test_extraction_input_chat_mode():
    inp: ExtractionInput = {
        "paper_path": None,
        "user_parameters": {"BoxSize": 100000, "Omega0": 0.3},
        "target_software": "mp-gadget",
        "custom_prompt": "Use these exact values",
    }
    assert inp["user_parameters"]["BoxSize"] == 100000


def test_extraction_output_complete():
    out: ExtractionOutput = {
        "sections": {"genic": {"BoxSize": 100000}, "gadget": {"Omega0": 0.3}},
        "ic_notes": [],
        "status": "complete",
        "missing": [],
        "comment": "All parameters found.",
        "sources": [{"param": "BoxSize", "value": 100000, "location": "Section 3", "page": 5}],
        "resource_estimates": {},
    }
    assert out["status"] == "complete"
    assert len(out["missing"]) == 0
    assert "genic" in out["sections"]


def test_extraction_output_incomplete():
    out: ExtractionOutput = {
        "sections": {"params": {"BoxSize": 100000}},
        "ic_notes": ["Use MUSIC to generate ICs"],
        "status": "incomplete",
        "missing": ["Omega0", "HubbleParam"],
        "comment": "Could not find all parameters.",
        "sources": [],
        "resource_estimates": {},
    }
    assert out["status"] == "incomplete"
    assert "Omega0" in out["missing"]
    assert len(out["ic_notes"]) == 1
