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
    genic_file = output_dir / f"{paper_name}_genic.json"
    genic_data = {"source": paper_path or "user_input", "parameters": formatted.get("genic", {}), "comment": comment, "sources": sources}
    genic_file.write_text(json.dumps(genic_data, indent=2))
    gadget_file = output_dir / f"{paper_name}_gadget.json"
    gadget_data = {"source": paper_path or "user_input", "parameters": formatted.get("gadget", {}), "comment": comment, "sources": sources}
    gadget_file.write_text(json.dumps(gadget_data, indent=2))
    return {"status": state.get("status", "incomplete")}
