"""Parameter extraction StateGraph construction."""
from __future__ import annotations
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from simagents.config.settings import Settings
from simagents.graph.state import ExtractionState
from simagents.nodes import parse_input, ask_user, save_output, estimator
from simagents.nodes.structured_extract import structured_extract
from simagents.nodes.code_validate import code_validate


def create_extraction_graph(settings: Settings, checkpointer: BaseCheckpointSaver | None = None):
    """Build the extraction graph.

    New architecture (single-pass structured extraction):
        parse_input → structured_extract → [code_validate] → save_output → [should_estimate] → estimator → END
                            ↑                    |
                            ├── retry ──────────┘
                            └── ask_user ←──────┘
    """
    graph = StateGraph(ExtractionState)

    # Nodes
    graph.add_node("parse_input", parse_input)
    graph.add_node("structured_extract", structured_extract)
    graph.add_node("ask_user", ask_user)
    graph.add_node("save_output", save_output)
    graph.add_node("estimator", estimator)

    # Entry
    graph.set_entry_point("parse_input")

    # Edges
    graph.add_edge("parse_input", "structured_extract")

    # After extraction: code_validate routes to done/retry/needs_user_input
    graph.add_conditional_edges(
        "structured_extract",
        code_validate,
        {
            "done": "save_output",
            "retry": "structured_extract",
            "needs_user_input": "ask_user",
        },
    )

    # After user answers, go back to extraction
    graph.add_edge("ask_user", "structured_extract")

    # After save: optionally run estimator
    def should_estimate(state):
        sections = state.get("formatted_parameters", {}).get("sections", {})
        has_params = any(bool(v) for v in sections.values())
        if has_params:
            return "estimate"
        return "end"

    graph.add_conditional_edges("save_output", should_estimate, {"estimate": "estimator", "end": END})
    graph.add_edge("estimator", END)

    return graph.compile(checkpointer=checkpointer)
