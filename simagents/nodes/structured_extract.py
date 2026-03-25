"""structured_extract node — single-pass extraction with structured output.

Replaces the physics_expert + formatter two-agent pipeline with a single
LLM call using with_structured_output() for guaranteed valid JSON.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from simagents.graph.state import ExtractionState


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "structured_extract.md"


class ParameterSource(BaseModel):
    """A source citation for an extracted parameter."""
    param: str = Field(description="Parameter name")
    value: Any = Field(description="Extracted value")
    location: str = Field(description="Where in the paper (Table 1, Section 2.1, etc.)")
    page: int = Field(default=0, description="Page number if known")


class ExtractionResult(BaseModel):
    """Structured output from the extraction agent."""
    sections: dict[str, dict[str, Any]] = Field(
        description="Parameter sections. Keys are section names (e.g., 'genic', 'gadget', 'params'). Values are dicts of parameter_name: value."
    )
    comment: str = Field(
        default="",
        description="Brief explanation of extracted parameters, unit conversions, and assumptions"
    )
    sources: list[ParameterSource] = Field(
        default_factory=list,
        description="Source citations for key parameters"
    )
    status: str = Field(
        description="'complete' if all core params found, 'incomplete' if missing, 'needs_user_input' if user must provide values"
    )
    missing_parameters: list[str] = Field(
        default_factory=list,
        description="Parameters that could not be found in the paper"
    )
    user_questions: list[str] = Field(
        default_factory=list,
        description="Questions to ask the user for missing values"
    )


def _build_prompt(state: ExtractionState, config: RunnableConfig) -> str:
    """Build the extraction prompt from template + profile data."""
    template = _PROMPT_PATH.read_text(encoding="utf-8")

    configurable = config.get("configurable", {})
    profile = configurable.get("profile")

    # Build profile context
    software_name = "the target simulation software"
    sections_spec = "Use a single 'params' section."
    parameter_names_table = "Use standard parameter names from the documentation."
    units_info = "Check documentation for unit conventions."
    ic_info = ""
    family_hint = ""

    if profile:
        software_name = profile.name
        sections_spec = "\n".join(
            f"- '{s.name}': {s.description}" for s in profile.output_sections
        )
        if profile.parameter_names:
            rows = [f"  {canonical} → {software}" for canonical, software in profile.parameter_names.items()]
            parameter_names_table = "\n".join(rows)
        if profile.units:
            units_info = "\n".join(f"  {k}: {v}" for k, v in profile.units.items())
        if profile.ic_generator == "external":
            ic_info = f"IC generator: external. {profile.ic_note}"
        elif profile.ic_generator == "builtin":
            ic_info = f"IC generator: built-in. {profile.ic_note}"
        family_hint = f"Software family: {profile.family}"

    # Build input context
    input_parts = []
    mode = state.get("input_mode", "paper")
    if mode in ("paper", "hybrid"):
        input_parts.append("Source: scientific paper (relevant sections provided below)")
    if mode in ("chat", "hybrid"):
        user_params = state.get("user_parameters", {})
        input_parts.append(f"User-provided parameters: {json.dumps(user_params)}")
        if mode == "hybrid":
            input_parts.append("User values take precedence over paper values.")

    # Feedback from previous iteration
    missing = state.get("missing_parameters", [])
    if missing:
        input_parts.append(f"\nPREVIOUS ITERATION: these parameters were flagged as wrong or missing: {', '.join(missing)}")
        input_parts.append("Please search more carefully for these specific parameters.")

    user_answers = state.get("user_answers", [])
    if user_answers:
        input_parts.append(f"\nUser provided these answers: {json.dumps(user_answers)}")

    custom_prompt = state.get("custom_prompt", "")

    return template.format(
        software_name=software_name,
        sections_spec=sections_spec,
        parameter_names_table=parameter_names_table,
        units_info=units_info,
        ic_info=ic_info,
        family_hint=family_hint,
        input_context="\n".join(input_parts),
        custom_prompt=custom_prompt or "",
    )


def _retrieve_context(state: ExtractionState, config: RunnableConfig) -> str:
    """Retrieve relevant chunks from both paper and docs."""
    configurable = config.get("configurable", {})
    paper_retriever = configurable.get("paper_retriever")
    docs_retriever = configurable.get("docs_retriever")

    chunks = []
    seen = set()

    # Paper RAG
    if paper_retriever and state.get("input_mode") in ("paper", "hybrid"):
        queries = [
            "cosmological parameters Omega matter dark energy baryon Hubble sigma8",
            "simulation box size volume Mpc resolution particle number grid",
            "initial conditions starting redshift power spectrum transfer function seed",
            "output redshift snapshots scale factor time",
            "simulation setup configuration parameters table summary",
            "cooling star formation black hole feedback wind neutrino physics",
            "softening length mass resolution time step",
        ]
        # Add targeted queries for missing params
        missing = state.get("missing_parameters", [])
        if missing:
            queries.append(" ".join(missing))

        for q in queries:
            docs = paper_retriever.invoke(q)
            for doc in docs:
                if doc.page_content not in seen:
                    seen.add(doc.page_content)
                    chunks.append(f"[PAPER] {doc.page_content}")

    # Docs RAG
    if docs_retriever:
        doc_queries = [
            "required parameters configuration",
            "parameter format units conventions",
            "cosmological parameters simulation setup",
        ]
        for q in doc_queries:
            docs = docs_retriever.invoke(q)
            for doc in docs:
                if doc.page_content not in seen:
                    seen.add(doc.page_content)
                    chunks.append(f"[DOCS] {doc.page_content}")

    return "\n\n---\n\n".join(chunks) if chunks else "No context available."


def structured_extract(state: ExtractionState, config: RunnableConfig) -> dict:
    """Single-pass structured extraction combining physics + formatting."""
    configurable = config.get("configurable", {})
    llm = configurable["llm"]

    # Build prompt and retrieve context
    system_prompt = _build_prompt(state, config)
    context = _retrieve_context(state, config)

    user_msg = f"## Source Material\n\n{context}\n\nExtract all simulation parameters from the source material above and format them for the target software."

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_msg),
    ]

    # Use regular invoke + JSON parse (more reliable across models than structured_output
    # which struggles with deeply nested dict[str, dict[str, Any]] schemas)
    from simagents.nodes.formatter import _extract_json

    response = llm.invoke(messages)

    try:
        parsed = _extract_json(response.content)
        result = ExtractionResult(**parsed)
    except Exception as e:
        # Retry once with explicit JSON instruction
        retry_msg = HumanMessage(content="Your response was not valid JSON. Please respond with ONLY the JSON object matching the schema: {sections: {section_name: {param: value}}, comment: str, sources: [...], status: str, missing_parameters: [...], user_questions: [...]}")
        response = llm.invoke(messages + [response, retry_msg])
        try:
            parsed = _extract_json(response.content)
            result = ExtractionResult(**parsed)
        except Exception as e2:
            return {
                "formatted_parameters": {
                    "sections": {},
                    "comment": f"JSON parse failed: {e2}. Raw: {response.content[:500]}",
                    "sources": [],
                    "ic_notes": [],
                },
                "status": "incomplete",
                "missing_parameters": ["JSON_PARSE_FAILED"],
                "iteration": state.get("iteration", 0) + 1,
                "messages": [messages[1], response],
            }

    # Convert Pydantic model to dict for state
    sections = result.sections
    sources = [s.model_dump() for s in result.sources]

    # Compute IC notes deterministically
    ic_notes = []
    profile = configurable.get("profile")
    if profile and profile.ic_generator == "external":
        ic_relevant = ["sigma8", "Sigma8", "Seed", "seed", "Redshift", "starting_redshift", "n_s", "PrimordialIndex", "spectral_index"]
        for sec_params in sections.values():
            if isinstance(sec_params, dict):
                for k, v in sec_params.items():
                    if any(ir in k for ir in ic_relevant) and v is not None:
                        ic_notes.append(f"{k}={v} (needed for IC generation)")
        if ic_notes:
            ic_notes.append(profile.ic_note)

    formatted = {
        "sections": sections,
        "comment": result.comment,
        "sources": sources,
        "ic_notes": ic_notes,
    }

    return {
        "formatted_parameters": formatted,
        "status": result.status,
        "missing_parameters": result.missing_parameters,
        "user_questions": result.user_questions,
        "iteration": state.get("iteration", 0) + 1,
        "messages": [messages[1]],
    }
