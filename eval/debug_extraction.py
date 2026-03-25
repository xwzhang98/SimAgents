"""Debug extraction — show raw physics_expert output before formatter."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

from simagents.config.settings import Settings
from simagents.tools.pdf_loader import build_paper_retriever
from simagents.nodes.physics_expert import physics_expert, _load_prompt, _build_input_context
from langchain.chat_models import init_chat_model


def debug_extract(paper_path: str, custom_prompt: str = None):
    settings = Settings.from_yaml(str(PROJECT_ROOT / "config.yaml"))
    llm_kwargs = {"temperature": settings.llm.temperature}
    if settings.openai_api_key:
        llm_kwargs["api_key"] = settings.openai_api_key
    llm = init_chat_model(model=settings.llm.model, model_provider=settings.llm.provider, **llm_kwargs)
    paper_retriever = build_paper_retriever(paper_path, settings.rag)

    state = {
        "input_mode": "paper",
        "target_software": "mp-gadget",
        "custom_prompt": custom_prompt,
        "iteration": 0,
        "missing_parameters": [],
        "user_answers": [],
    }

    config = {"configurable": {"llm": llm, "paper_retriever": paper_retriever}}

    # Show what RAG retrieves
    print("=== RAG Retrieved Chunks ===")
    queries = [
        "cosmological parameters Omega matter dark energy baryon Hubble",
        "sigma8 sigma_8 power spectrum normalization spectral index n_s",
        "simulation box size volume Mpc resolution particle number",
        "initial conditions starting redshift power spectrum transfer function seed",
        "simulation setup configuration parameters table summary",
        "output redshift snapshots scale factor",
        "cooling star formation black hole feedback wind neutrino",
    ]
    for q in queries:
        docs = paper_retriever.invoke(q)
        print(f"\nQuery: '{q}'")
        for i, doc in enumerate(docs[:2]):  # show top 2 per query
            print(f"  [{i}] {doc.page_content[:200]}...")

    # Run physics expert
    print("\n\n=== Physics Expert Raw Output ===")
    result = physics_expert(state, config)
    raw = result["raw_parameters"]
    print(raw[:3000])

    # Try to parse as JSON
    try:
        parsed = json.loads(raw)
        print("\n\n=== Parsed Parameters ===")
        for p in parsed.get("parameters", []):
            print(f"  {p['name']}: {p['value']} ({p.get('source', '?')}) [{p.get('confidence', '?')}]")
        print(f"\n  Not found: {parsed.get('not_found', [])}")
    except json.JSONDecodeError:
        print("\n(Could not parse as JSON)")


if __name__ == "__main__":
    paper = sys.argv[1] if len(sys.argv) > 1 else "golden_standard/papers/bluetides.pdf"
    prompt = sys.argv[2] if len(sys.argv) > 2 else None
    debug_extract(paper, prompt)
