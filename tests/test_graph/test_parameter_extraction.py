"""Tests for the parameter extraction graph."""
import json
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from simagents.graph.parameter_extraction import create_extraction_graph
from simagents.config.settings import Settings


def test_create_extraction_graph_returns_compiled_graph():
    settings = Settings()
    graph = create_extraction_graph(settings, checkpointer=MemorySaver())
    assert graph is not None
    assert hasattr(graph, "invoke")


def test_graph_paper_mode_complete():
    settings = Settings()
    graph = create_extraction_graph(settings, checkpointer=MemorySaver())
    mock_llm = MagicMock()
    extraction_response = AIMessage(content="- BoxSize: 100 Mpc/h (Table 1)\n- Omega0: 0.3 (Section 2)")
    formatter_response = AIMessage(content=json.dumps({
        "genic": {"BoxSize": 100000, "Ngrid": 64},
        "gadget": {"Omega0": 0.3, "TimeMax": 1.0},
        "comment": "Extracted from paper",
        "sources": [{"param": "BoxSize", "value": 100000, "location": "Table 1", "page": 3}],
        "status": "complete",
        "missing_parameters": [],
        "user_questions": [],
    }))
    mock_llm.invoke.side_effect = [extraction_response, formatter_response]
    mock_paper_retriever = MagicMock()
    mock_paper_retriever.invoke.return_value = [MagicMock(page_content="BoxSize = 100 Mpc/h")]
    mock_docs_retriever = MagicMock()
    mock_docs_retriever.invoke.return_value = [MagicMock(page_content="BoxSize: kpc/h. Required.")]
    result = graph.invoke(
        {
            "paper_path": "/fake/paper.pdf",
            "user_parameters": None,
            "target_software": "mp-gadget",
            "custom_prompt": None,
            "max_iterations": 2,
            "input_mode": "",
            "raw_parameters": "",
            "formatted_parameters": {},
            "status": "",
            "missing_parameters": [],
            "user_questions": [],
            "user_answers": [],
            "iteration": 0,
            "messages": [],
        },
        config={"configurable": {"llm": mock_llm, "paper_retriever": mock_paper_retriever, "docs_retriever": mock_docs_retriever, "output_dir": "/tmp/simagents_test", "thread_id": "test-1"}},
    )
    assert result["status"] == "complete"
    assert result["formatted_parameters"]["genic"]["BoxSize"] == 100000
