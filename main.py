"""CLI entry point for SimAgents parameter extraction."""
from __future__ import annotations
import argparse
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from simagents.config.settings import Settings
from simagents.graph.parameter_extraction import create_extraction_graph
from simagents.tools.pdf_loader import build_paper_retriever
from simagents.tools.docs_loader import build_docs_retriever
from simagents.profiles import load_profile


def _get_llm(settings: Settings):
    from langchain.chat_models import init_chat_model
    kwargs = {"temperature": settings.llm.temperature}
    if settings.llm.provider == "openai" and settings.openai_api_key:
        kwargs["api_key"] = settings.openai_api_key
    elif settings.llm.provider == "anthropic" and settings.anthropic_api_key:
        kwargs["api_key"] = settings.anthropic_api_key
    elif settings.llm.provider == "google" and settings.google_api_key:
        kwargs["api_key"] = settings.google_api_key
    return init_chat_model(model=settings.llm.model, model_provider=settings.llm.provider, **kwargs)


def main():
    parser = argparse.ArgumentParser(description="SimAgents: Extract simulation parameters from papers")
    parser.add_argument("--paper", type=str, help="Path to the PDF paper")
    parser.add_argument("--software", type=str, default=None, help="Target simulation software")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config YAML")
    parser.add_argument("--output", type=str, default=None, help="Output directory")
    parser.add_argument("--prompt", type=str, default=None, help="Custom extraction instructions")
    args = parser.parse_args()
    load_dotenv()
    settings = Settings.from_yaml(args.config)
    if args.software:
        settings.extraction.target_software = args.software
    if args.output:
        settings.paths.output_dir = args.output

    target = settings.extraction.target_software
    print(f"Using LLM: {settings.llm.provider}/{settings.llm.model}")

    # Load software profile
    profile = load_profile(target, settings.paths.software_profiles_dir)
    print(f"Loaded profile: {profile.name} ({profile.family} family)")

    llm = _get_llm(settings)
    paper_retriever = None
    if args.paper:
        print(f"Loading paper: {args.paper}")
        paper_retriever = build_paper_retriever(args.paper, settings.rag)

    print(f"Loading {profile.name} docs...")
    docs_retriever = build_docs_retriever(profile.docs_dir, settings.rag)

    graph = create_extraction_graph(settings, checkpointer=MemorySaver())
    print("Starting parameter extraction...")
    result = graph.invoke(
        {
            "paper_path": args.paper,
            "user_parameters": None,
            "target_software": target,
            "custom_prompt": args.prompt,
            "max_iterations": settings.extraction.max_iterations,
            "input_mode": "",
            "raw_parameters": "",
            "formatted_parameters": {},
            "status": "",
            "missing_parameters": [],
            "user_questions": [],
            "user_answers": [],
            "iteration": 0,
            "messages": [],
        },
        config={
            "configurable": {
                "llm": llm,
                "paper_retriever": paper_retriever,
                "docs_retriever": docs_retriever,
                "profile": profile,
                "output_dir": settings.paths.output_dir,
                "thread_id": "cli-main",
            }
        },
    )

    print(f"\nExtraction status: {result.get('status', 'unknown')}")
    if result.get("missing_parameters"):
        print(f"Missing parameters: {', '.join(result['missing_parameters'])}")

    # Display sections
    formatted = result.get("formatted_parameters", {})
    sections = formatted.get("sections", {})
    for section_name, params in sections.items():
        print(f"\n--- {section_name} ---")
        if isinstance(params, dict):
            for k, v in params.items():
                print(f"  {k}: {v}")

    ic_notes = formatted.get("ic_notes", [])
    if ic_notes:
        print("\n--- IC Notes ---")
        for note in ic_notes:
            print(f"  {note}")

    print(f"\nOutput saved to: {settings.paths.output_dir}/")


if __name__ == "__main__":
    main()
