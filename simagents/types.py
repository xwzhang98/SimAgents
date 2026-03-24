"""Public input/output contracts for the SimAgents extraction graph."""
from __future__ import annotations

from typing import TypedDict


class ExtractionInput(TypedDict, total=False):
    """Input contract for the extraction graph.

    Provide paper_path, user_parameters, or both (hybrid mode).
    """
    paper_path: str | None
    user_parameters: dict | None
    target_software: str
    custom_prompt: str | None


class ResourceEstimates(TypedDict):
    """Resource estimates for a cosmological simulation."""
    memory_per_node_gb: float
    total_cpu_hours: int
    wall_clock: str
    storage_tb: float
    recommended_nodes: int
    confidence: str
    reference_simulation: str
    reasoning: str


class ExtractionOutput(TypedDict):
    """Output contract for the extraction graph."""
    sections: dict[str, dict]       # {"params": {...}} or {"genic": {...}, "gadget": {...}}
    ic_notes: list[str]             # IC-relevant params when ic_generator is external
    status: str                     # "complete" | "incomplete"
    missing: list[str]
    comment: str
    sources: list[dict]  # [{param, value, location, page}]
    resource_estimates: dict
