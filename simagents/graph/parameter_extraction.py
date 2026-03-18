"""Parameter extraction StateGraph construction."""
from __future__ import annotations
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from simagents.config.settings import Settings
from simagents.graph.state import ExtractionState
from simagents.nodes import parse_input, physics_expert, formatter, check_done, ask_user, save_output


def create_extraction_graph(settings: Settings, checkpointer: BaseCheckpointSaver | None = None):
    graph = StateGraph(ExtractionState)
    graph.add_node("parse_input", parse_input)
    graph.add_node("physics_expert", physics_expert)
    graph.add_node("formatter", formatter)
    graph.add_node("ask_user", ask_user)
    graph.add_node("save_output", save_output)
    graph.set_entry_point("parse_input")
    graph.add_edge("parse_input", "physics_expert")
    graph.add_edge("physics_expert", "formatter")
    graph.add_conditional_edges("formatter", check_done, {"done": "save_output", "loop": "physics_expert", "needs_user_input": "ask_user"})
    graph.add_edge("ask_user", "physics_expert")
    graph.add_edge("save_output", END)
    return graph.compile(checkpointer=checkpointer)
