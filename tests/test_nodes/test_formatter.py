"""Tests for formatter node."""
import json
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from simagents.nodes.formatter import formatter

def test_formatter_complete():
    json_output = json.dumps({"genic": {"BoxSize": 100000, "Ngrid": 64}, "gadget": {"Omega0": 0.3, "TimeMax": 1.0}, "comment": "All params found", "sources": [{"param": "BoxSize", "value": 100000, "location": "Table 1", "page": 3}], "status": "complete", "missing_parameters": [], "user_questions": []})
    state = {"raw_parameters": "- BoxSize: 100 Mpc/h\n- Omega0: 0.3", "target_software": "mp-gadget"}
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = [MagicMock(page_content="BoxSize: kpc/h. Required.")]
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content=json_output)
    config = {"configurable": {"docs_retriever": mock_retriever, "llm": mock_llm}}
    result = formatter(state, config)
    assert result["status"] == "complete"
    assert result["formatted_parameters"]["genic"]["BoxSize"] == 100000

def test_formatter_incomplete():
    json_output = json.dumps({"genic": {"BoxSize": 100000}, "gadget": {}, "comment": "Missing required params", "sources": [], "status": "incomplete", "missing_parameters": ["Omega0", "HubbleParam"], "user_questions": []})
    state = {"raw_parameters": "- BoxSize: 100 Mpc/h", "target_software": "mp-gadget"}
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = []
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content=json_output)
    config = {"configurable": {"docs_retriever": mock_retriever, "llm": mock_llm}}
    result = formatter(state, config)
    assert result["status"] == "incomplete"
    assert "Omega0" in result["missing_parameters"]
