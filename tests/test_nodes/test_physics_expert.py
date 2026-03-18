"""Tests for physics_expert node."""
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from simagents.nodes.physics_expert import physics_expert

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
