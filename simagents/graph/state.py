"""LangGraph state definition for the parameter extraction graph."""
from __future__ import annotations
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ExtractionState(TypedDict):
    """Internal state for the extraction graph.
    Note: Retrievers are NOT stored in state (not serializable).
    They are passed via LangGraph's configurable dict.
    All fields must be provided in the initial invoke() call.
    """
    input_mode: str
    paper_path: str | None
    user_parameters: dict | None
    target_software: str
    custom_prompt: str | None
    raw_parameters: str
    formatted_parameters: dict
    status: str
    missing_parameters: list[str]
    user_questions: list[str]
    user_answers: list[dict]
    iteration: int
    max_iterations: int
    messages: Annotated[list[BaseMessage], add_messages]
