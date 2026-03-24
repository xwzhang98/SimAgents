"""Tests for physics_expert node."""
from pathlib import Path
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from simagents.nodes.physics_expert import physics_expert
from simagents.profiles.loader import SoftwareProfile, OutputSection


def test_physics_expert_paper_mode():
    state = {"input_mode": "paper", "target_software": "mp-gadget", "custom_prompt": None, "iteration": 0, "missing_parameters": [], "user_answers": []}
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = [MagicMock(page_content="BoxSize = 100 Mpc/h (Table 1)")]
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="- BoxSize: 100 Mpc/h (Table 1, page 5)\n- Omega0: 0.3 (Section 2)")
    config = {"configurable": {"paper_retriever": mock_retriever, "llm": mock_llm}}
    result = physics_expert(state, config)
    assert "raw_parameters" in result
    assert len(result["raw_parameters"]) > 0
    assert result["iteration"] == 1


def test_physics_expert_chat_mode():
    state = {"input_mode": "chat", "target_software": "mp-gadget", "custom_prompt": None, "user_parameters": {"BoxSize": 100000, "Omega0": 0.3}, "iteration": 0, "missing_parameters": [], "user_answers": []}
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="- BoxSize: 100000 kpc/h (user provided)\n- Omega0: 0.3 (user provided)")
    config = {"configurable": {"paper_retriever": None, "llm": mock_llm}}
    result = physics_expert(state, config)
    assert "raw_parameters" in result


def test_physics_expert_with_profile():
    """Physics expert uses profile family hint."""
    profile = SoftwareProfile(
        slug="test-sw",
        name="TestSoftware",
        description="A test simulation code.",
        family="gadget",
        output_format="key-value",
        output_sections=[OutputSection(name="params", description="Main params")],
        units={"length": "kpc/h"},
        ic_generator="builtin",
        ic_note="Has built-in IC gen.",
        parameter_names={},
        docs_dir=Path("/tmp/fake_docs"),
        templates_dir=Path("/tmp/fake_templates"),
        profile_dir=Path("/tmp/fake_profile"),
    )
    state = {"input_mode": "paper", "target_software": "test-sw", "custom_prompt": None, "iteration": 0, "missing_parameters": [], "user_answers": []}
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = [MagicMock(page_content="BoxSize = 100")]
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="- BoxSize: 100 Mpc/h")
    config = {"configurable": {"paper_retriever": mock_retriever, "llm": mock_llm, "profile": profile}}
    result = physics_expert(state, config)
    assert "raw_parameters" in result
    # Verify the system prompt included family hint by checking what was passed to the LLM
    call_args = mock_llm.invoke.call_args[0][0]
    system_msg = call_args[0].content
    assert "gadget" in system_msg.lower()
