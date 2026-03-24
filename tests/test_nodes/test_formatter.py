"""Tests for formatter node."""
import json
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from simagents.nodes.formatter import formatter


def test_formatter_complete():
    json_output = json.dumps({
        "sections": {"genic": {"BoxSize": 100000, "Ngrid": 64}, "gadget": {"Omega0": 0.3, "TimeMax": 1.0}},
        "comment": "All params found",
        "sources": [{"param": "BoxSize", "value": 100000, "location": "Table 1", "page": 3}],
        "status": "complete",
        "missing_parameters": [],
        "user_questions": [],
    })
    state = {"raw_parameters": "- BoxSize: 100 Mpc/h\n- Omega0: 0.3", "target_software": "mp-gadget"}
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = [MagicMock(page_content="BoxSize: kpc/h. Required.")]
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content=json_output)
    config = {"configurable": {"docs_retriever": mock_retriever, "llm": mock_llm}}
    result = formatter(state, config)
    assert result["status"] == "complete"
    assert result["formatted_parameters"]["sections"]["genic"]["BoxSize"] == 100000


def test_formatter_incomplete():
    json_output = json.dumps({
        "sections": {"genic": {"BoxSize": 100000}, "gadget": {}},
        "comment": "Missing required params",
        "sources": [],
        "status": "incomplete",
        "missing_parameters": ["Omega0", "HubbleParam"],
        "user_questions": [],
    })
    state = {"raw_parameters": "- BoxSize: 100 Mpc/h", "target_software": "mp-gadget"}
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = []
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content=json_output)
    config = {"configurable": {"docs_retriever": mock_retriever, "llm": mock_llm}}
    result = formatter(state, config)
    assert result["status"] == "incomplete"
    assert "Omega0" in result["missing_parameters"]


def test_formatter_with_profile():
    """Formatter uses profile to build prompt and compute IC notes."""
    from simagents.profiles.loader import SoftwareProfile, OutputSection
    from pathlib import Path
    profile = SoftwareProfile(
        slug="test-sw",
        name="TestSoftware",
        description="A test simulation code.",
        family="gadget",
        output_format="key-value",
        output_sections=[
            OutputSection(name="params", description="Main params"),
        ],
        units={"length": "kpc/h"},
        ic_generator="external",
        ic_note="Use N-GenIC for ICs.",
        parameter_names={"box_size": "BoxSize"},
        docs_dir=Path("/tmp/fake_docs"),
        templates_dir=Path("/tmp/fake_templates"),
        profile_dir=Path("/tmp/fake_profile"),
    )
    json_output = json.dumps({
        "sections": {"params": {"BoxSize": 100000, "Sigma8": 0.8, "Seed": 42}},
        "comment": "Test",
        "sources": [],
        "status": "complete",
        "missing_parameters": [],
        "user_questions": [],
    })
    state = {"raw_parameters": "- BoxSize: 100 Mpc/h", "target_software": "test-sw"}
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = []
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content=json_output)
    config = {"configurable": {"docs_retriever": mock_retriever, "llm": mock_llm, "profile": profile}}
    result = formatter(state, config)
    assert result["status"] == "complete"
    assert result["formatted_parameters"]["sections"]["params"]["BoxSize"] == 100000
    # IC notes should be computed for external IC generator
    ic_notes = result["formatted_parameters"].get("ic_notes", [])
    assert len(ic_notes) >= 1
    assert "external" in ic_notes[0].lower() or "External" in ic_notes[0]
