"""save_output node — writes extraction results to JSON files."""
from __future__ import annotations
import json
from pathlib import Path
from langchain_core.runnables import RunnableConfig
from simagents.graph.state import ExtractionState


def save_output(state: ExtractionState, config: RunnableConfig) -> dict:
    output_dir = Path(config.get("configurable", {}).get("output_dir", "./output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    paper_path = state.get("paper_path")
    paper_name = Path(paper_path).stem if paper_path else "extraction"
    formatted = state.get("formatted_parameters", {})
    comment = formatted.get("comment", "")
    sources = formatted.get("sources", [])

    profile = config.get("configurable", {}).get("profile")
    sections = formatted.get("sections", {})

    if profile and profile.output_sections:
        # Write one file per output section using profile's filename template
        for section in profile.output_sections:
            filename = section.filename_template.format(paper=paper_name)
            section_data = {
                "source": paper_path or "user_input",
                "parameters": sections.get(section.name, {}),
                "comment": comment,
                "sources": sources,
            }
            (output_dir / filename).write_text(json.dumps(section_data, indent=2))
    else:
        # Fallback: write each section key as a separate file
        for section_name, params in sections.items():
            filename = f"{paper_name}_{section_name}.json"
            section_data = {
                "source": paper_path or "user_input",
                "parameters": params if isinstance(params, dict) else {},
                "comment": comment,
                "sources": sources,
            }
            (output_dir / filename).write_text(json.dumps(section_data, indent=2))

    return {"status": state.get("status", "incomplete")}
