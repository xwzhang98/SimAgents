"""Tests for the parameter extraction graph."""
import json
from pathlib import Path
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from simagents.graph.parameter_extraction import create_extraction_graph
from simagents.config.settings import Settings
from simagents.profiles.loader import SoftwareProfile, OutputSection


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
        "sections": {"genic": {"BoxSize": 100000, "Ngrid": 64}, "gadget": {"Omega0": 0.3, "TimeMax": 1.0}},
        "comment": "Extracted from paper",
        "sources": [{"param": "BoxSize", "value": 100000, "location": "Table 1", "page": 3}],
        "status": "complete",
        "missing_parameters": [],
        "user_questions": [],
    }))
    estimator_response = AIMessage(content=json.dumps({
        "memory_per_node_gb": 32.0,
        "total_cpu_hours": 1000,
        "wall_clock": "1 hour",
        "storage_tb": 0.1,
        "recommended_nodes": 4,
        "confidence": "low",
        "reference_simulation": "BlueTides",
        "reasoning": "Small test simulation; scaled from BlueTides reference.",
    }))
    mock_llm.invoke.side_effect = [extraction_response, formatter_response, estimator_response]
    mock_paper_retriever = MagicMock()
    mock_paper_retriever.invoke.return_value = [MagicMock(page_content="BoxSize = 100 Mpc/h")]
    mock_docs_retriever = MagicMock()
    mock_docs_retriever.invoke.return_value = [MagicMock(page_content="BoxSize: kpc/h. Required.")]

    profile = SoftwareProfile(
        slug="mp-gadget",
        name="MP-Gadget",
        description="Test profile",
        family="gadget",
        output_format="key-value",
        output_sections=[
            OutputSection(name="genic", description="GenIC params"),
            OutputSection(name="gadget", description="Gadget params"),
        ],
        units={"length": "kpc/h"},
        ic_generator="builtin",
        ic_note="Has built-in IC gen.",
        parameter_names={"box_size": "BoxSize"},
        docs_dir=Path("/tmp/fake_docs"),
        templates_dir=Path("/tmp/fake_templates"),
        profile_dir=Path("/tmp/fake_profile"),
    )

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
            "resource_estimates": {},
        },
        config={"configurable": {"llm": mock_llm, "paper_retriever": mock_paper_retriever, "docs_retriever": mock_docs_retriever, "profile": profile, "output_dir": "/tmp/simagents_test", "thread_id": "test-1"}},
    )
    assert result["status"] == "complete"
    assert result["formatted_parameters"]["sections"]["genic"]["BoxSize"] == 100000
    assert isinstance(result["resource_estimates"], dict)
    assert result["resource_estimates"].get("memory_per_node_gb") == 32.0
