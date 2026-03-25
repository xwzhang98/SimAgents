"""formatter node — validates and formats parameters against software docs via RAG."""
from __future__ import annotations
import json
import re
from pathlib import Path
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from simagents.graph.state import ExtractionState

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "formatter.md"

# Canonical IC-relevant parameter names
_IC_PARAMS = {"sigma8", "Sigma8", "spectral_index", "PrimordialIndex", "ns",
              "starting_redshift", "Redshift", "seed", "Seed", "RandomSeed"}


def _build_template_vars(profile, raw_parameters: str) -> dict:
    """Build all template variables from a SoftwareProfile."""
    # sections_spec
    section_names = [s.name for s in profile.output_sections]
    sections_spec = "\n".join(f"- **{s.name}**: {s.description}" for s in profile.output_sections)

    # parameter_names_table
    if profile.parameter_names:
        rows = [f"| {canon} | {sw_name} |" for canon, sw_name in profile.parameter_names.items()]
        parameter_names_table = "| Canonical | {name} |\n|---|---|\n".format(name=profile.name) + "\n".join(rows)
    else:
        parameter_names_table = "(No parameter name mappings defined — discover from documentation.)"

    # units_info
    if profile.units:
        units_info = "\n".join(f"- {dim}: {unit}" for dim, unit in profile.units.items())
    else:
        units_info = "See documentation for unit conventions."

    # ic_info
    if profile.ic_generator == "builtin":
        ic_info = f"This software has a BUILT-IN IC generator. {profile.ic_note}"
    elif profile.ic_generator == "external":
        ic_info = f"This software requires EXTERNAL IC generation. {profile.ic_note}"
    else:
        ic_info = "No specific IC generator information."

    # output_example
    example_sections = {s.name: {"example_param": "value"} for s in profile.output_sections}
    example = {
        "sections": example_sections,
        "comment": "...",
        "sources": [{"param": "name", "value": "val", "location": "Table X", "page": 1}],
        "status": "complete|incomplete|needs_user_input",
        "missing_parameters": [],
        "user_questions": [],
    }
    output_example = json.dumps(example, indent=2)

    return {
        "software_name": profile.name,
        "software_description": profile.description,
        "sections_spec": sections_spec,
        "parameter_names_table": parameter_names_table,
        "units_info": units_info,
        "ic_info": ic_info,
        "raw_parameters": raw_parameters,
        "output_example": output_example,
    }


def _load_prompt_with_profile(profile, raw_parameters: str) -> str:
    """Render formatter prompt from profile."""
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    tvars = _build_template_vars(profile, raw_parameters)
    return template.format(**tvars)


def _load_prompt(target_software: str, raw_parameters: str) -> str:
    """Fallback prompt rendering without profile."""
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    return template.format(
        software_name=target_software,
        software_description=f"{target_software} simulation software",
        sections_spec="- **params**: simulation parameters",
        parameter_names_table="(see documentation)",
        units_info="See documentation for unit conventions.",
        ic_info="See documentation for IC generation.",
        raw_parameters=raw_parameters,
        output_example='{\n  "sections": {"params": {"param": "value"}},\n  "comment": "...",\n  "sources": [],\n  "status": "complete|incomplete|needs_user_input",\n  "missing_parameters": [],\n  "user_questions": []\n}',
    )


def _compute_ic_notes(profile, sections: dict) -> list[str]:
    """Deterministically compute IC notes when profile uses external IC generator."""
    if not profile or profile.ic_generator != "external":
        return []
    notes = []
    # Scan all sections for IC-relevant parameters
    found_ic_params = {}
    for section_name, params in sections.items():
        if not isinstance(params, dict):
            continue
        for key, value in params.items():
            if key in _IC_PARAMS or key.lower() in {"sigma8", "ns", "spectral_index",
                                                       "starting_redshift", "seed",
                                                       "redshift", "randomseed"}:
                found_ic_params[key] = value
    if found_ic_params:
        param_list = ", ".join(f"{k}={v}" for k, v in found_ic_params.items())
        notes.append(f"External IC generation required. Relevant IC parameters found: {param_list}")
    else:
        notes.append("External IC generation required. No IC-relevant parameters found in output — ensure ICs are generated separately.")
    if profile.ic_note:
        notes.append(profile.ic_note)
    return notes


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    code_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_match:
        try:
            return json.loads(code_match.group(1))
        except json.JSONDecodeError:
            pass
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not extract JSON from response: {text[:200]}...")


def formatter(state: ExtractionState, config: RunnableConfig) -> dict:
    configurable = config.get("configurable", {})
    llm = configurable["llm"]
    docs_retriever = configurable["docs_retriever"]
    target_software = state.get("target_software", "mp-gadget")
    raw_parameters = state.get("raw_parameters", "")
    profile = configurable.get("profile")

    # Build prompt from profile or fallback
    if profile:
        system_prompt = _load_prompt_with_profile(profile, raw_parameters)
    else:
        system_prompt = _load_prompt(target_software, raw_parameters)

    search_queries = [f"{target_software} required parameters", f"{target_software} parameter format units", "cosmological parameters configuration"]
    retrieved_docs = []
    for query in search_queries:
        docs = docs_retriever.invoke(query)
        for doc in docs:
            retrieved_docs.append(doc.page_content)
    doc_context = "\n---\n".join(retrieved_docs) if retrieved_docs else "No documentation found."
    user_msg = f"## Documentation Reference\n{doc_context}\n\n## Extracted Parameters\n{raw_parameters}\n\nPlease validate and format these parameters according to {target_software} documentation."
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_msg)]
    response = llm.invoke(messages)
    try:
        parsed = _extract_json(response.content)
    except ValueError:
        retry_msg = HumanMessage(content="Your response was not valid JSON. Please respond with ONLY the JSON object, no other text.")
        response = llm.invoke(messages + [response, retry_msg])
        try:
            parsed = _extract_json(response.content)
        except ValueError:
            return {
                "formatted_parameters": {"sections": {}, "comment": response.content, "sources": [], "ic_notes": []},
                "status": "incomplete",
                "missing_parameters": ["JSON_PARSE_FAILED"],
                "messages": [response],
            }

    # Post-processing: code-based validation and auto-correction
    sections = parsed.get("sections", {})
    sections = _auto_correct(sections)
    parsed["sections"] = sections

    # Compute IC notes deterministically
    ic_notes = _compute_ic_notes(profile, sections)
    if ic_notes:
        parsed["ic_notes"] = ic_notes

    return {
        "formatted_parameters": parsed,
        "status": parsed.get("status", "incomplete"),
        "missing_parameters": parsed.get("missing_parameters", []),
        "user_questions": parsed.get("user_questions", []),
        "messages": [response],
    }


def _auto_correct(sections: dict) -> dict:
    """Code-based auto-correction of common LLM errors. No LLM calls."""
    all_params = {}
    for sec_params in sections.values():
        if isinstance(sec_params, dict):
            all_params.update(sec_params)

    # Fix Omega swap: if Omega0 > 0.5 and OmegaLambda < 0.5, swap them
    omega0_keys = ["Omega0", "Omega_cdm"]
    omega_l_keys = ["OmegaLambda", "Omega_lambda"]

    for sec_name, sec_params in sections.items():
        if not isinstance(sec_params, dict):
            continue

        o0_key = next((k for k in omega0_keys if k in sec_params), None)
        ol_key = next((k for k in omega_l_keys if k in sec_params), None)

        if o0_key and ol_key:
            o0 = _safe_float(sec_params[o0_key])
            ol = _safe_float(sec_params[ol_key])
            if o0 is not None and ol is not None and o0 > 0.5 and ol < 0.5:
                # Swap them
                sec_params[o0_key], sec_params[ol_key] = sec_params[ol_key], sec_params[o0_key]

    # Fix Ngrid: if > 50000, likely N³ instead of N — try cube root
    for sec_name, sec_params in sections.items():
        if not isinstance(sec_params, dict):
            continue
        for key in ["Ngrid", "GridSize", "Nmesh"]:
            if key in sec_params:
                val = _safe_float(sec_params[key])
                if val is not None and val > 50000:
                    import math
                    cube_root = round(val ** (1/3))
                    if abs(cube_root ** 3 - val) < val * 0.01:
                        sec_params[key] = cube_root

    # Remove None values
    for sec_name, sec_params in sections.items():
        if isinstance(sec_params, dict):
            sections[sec_name] = {k: v for k, v in sec_params.items() if v is not None}

    return sections


def _safe_float(val) -> float | None:
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
