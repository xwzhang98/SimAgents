"""Evaluation harness: extract parameters from papers and compare to golden standard."""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load env
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

from simagents.config.settings import Settings
from simagents.graph.parameter_extraction import create_extraction_graph
from simagents.tools.pdf_loader import build_paper_retriever
from simagents.tools.docs_loader import build_docs_retriever
from simagents.profiles import load_profile
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver


GOLDEN_DIR = PROJECT_ROOT / "golden_standard"
PAPERS_DIR = GOLDEN_DIR / "papers"


def load_golden_standard(name: str) -> dict:
    """Load golden standard parameters for a simulation."""
    path = GOLDEN_DIR / f"{name}_parameters.json"
    if not path.exists():
        raise FileNotFoundError(f"No golden standard for {name}")
    with open(path) as f:
        return json.load(f)


def load_paper_mapping() -> list[dict]:
    """Load paper → simulation mapping."""
    path = PAPERS_DIR / "paper_mapping.json"
    with open(path) as f:
        return json.load(f)


def score_extraction(extracted: dict, golden: dict) -> dict:
    """Score extracted parameters against golden standard.

    Returns dict with: total, correct, wrong, missing, extra, accuracy, details
    """
    # Flatten golden standard — only check numeric/boolean parameters
    golden_flat = {}
    for section_name, section_params in golden.items():
        if section_name == "comment":
            continue
        if isinstance(section_params, dict):
            for k, v in section_params.items():
                # Skip path placeholders and user-configurable params
                if isinstance(v, str) and ("<" in v or "path" in v.lower() or "user must" in v.lower()):
                    continue
                # Skip TimeLimitCPU (user-configurable)
                if k in ("TimeLimitCPU", "OutputDir", "InitCondFile", "FileBase", "FileWithInputSpectrum", "FileWithTransferFunction"):
                    continue
                golden_flat[f"{section_name}.{k}"] = v

    # Flatten extracted
    extracted_flat = {}
    sections = extracted.get("sections", extracted)  # handle both formats
    for section_name, section_params in sections.items():
        if not isinstance(section_params, dict):
            continue
        for k, v in section_params.items():
            if isinstance(v, str) and ("<" in v or "path" in v.lower()):
                continue
            if k in ("TimeLimitCPU", "OutputDir", "InitCondFile", "FileBase", "FileWithInputSpectrum", "FileWithTransferFunction"):
                continue
            extracted_flat[f"{section_name}.{k}"] = v

    correct = 0
    wrong = 0
    missing = 0
    details = []

    for key, golden_val in golden_flat.items():
        if key in extracted_flat:
            ext_val = extracted_flat[key]
            # Compare values with tolerance for floats
            if _values_match(ext_val, golden_val):
                correct += 1
                details.append({"param": key, "status": "correct", "extracted": ext_val, "golden": golden_val})
            else:
                wrong += 1
                details.append({"param": key, "status": "wrong", "extracted": ext_val, "golden": golden_val})
        else:
            missing += 1
            details.append({"param": key, "status": "missing", "golden": golden_val})

    # Extra parameters (in extracted but not in golden)
    extra = 0
    for key in extracted_flat:
        if key not in golden_flat:
            extra += 1

    total = len(golden_flat)
    accuracy = correct / total if total > 0 else 0.0

    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "missing": missing,
        "extra": extra,
        "accuracy": round(accuracy, 4),
        "details": details,
    }


def _values_match(extracted, golden, tolerance=0.01) -> bool:
    """Compare two values with tolerance for floats."""
    # Convert strings to numbers if possible
    try:
        e = float(str(extracted))
        g = float(str(golden))
        if g == 0:
            return abs(e - g) < tolerance
        return abs(e - g) / abs(g) < tolerance
    except (ValueError, TypeError):
        pass

    # String comparison (case-insensitive, strip whitespace)
    return str(extracted).strip().lower() == str(golden).strip().lower()


def run_single_extraction(
    paper_path: str,
    target_software: str = "mp-gadget",
    custom_prompt: str | None = None,
    model: str = "gpt-5.4-mini",
) -> dict:
    """Run a single extraction and return the formatted parameters."""
    settings = Settings.from_yaml(str(PROJECT_ROOT / "config.yaml"))
    settings.llm.model = model

    # Build LLM
    llm_kwargs = {"temperature": settings.llm.temperature}
    if settings.openai_api_key:
        llm_kwargs["api_key"] = settings.openai_api_key
    llm = init_chat_model(model=settings.llm.model, model_provider=settings.llm.provider, **llm_kwargs)

    # Build retrievers
    paper_retriever = build_paper_retriever(paper_path, settings.rag)
    profile = load_profile(target_software, str(PROJECT_ROOT / "data" / "software_profiles"))
    docs_retriever = build_docs_retriever(str(profile.docs_dir), settings.rag)

    # Build graph
    graph = create_extraction_graph(settings, checkpointer=MemorySaver())

    config = {
        "configurable": {
            "llm": llm,
            "paper_retriever": paper_retriever,
            "docs_retriever": docs_retriever,
            "profile": profile,
            "output_dir": str(PROJECT_ROOT / "eval" / "output"),
            "thread_id": "eval",
        }
    }

    initial_state = {
        "paper_path": paper_path,
        "user_parameters": None,
        "target_software": target_software,
        "custom_prompt": custom_prompt,
        "max_iterations": 2,
        "input_mode": "",
        "raw_parameters": "",
        "formatted_parameters": {},
        "status": "",
        "missing_parameters": [],
        "user_questions": [],
        "user_answers": [],
        "iteration": 0,
        "messages": [],
        "resource_estimates": {},
    }

    result = graph.invoke(initial_state, config=config)
    return result


def evaluate_paper(
    paper_path: str,
    simulation_name: str,
    custom_prompt: str | None = None,
    model: str = "gpt-5.4-mini",
) -> dict:
    """Extract parameters from a paper and score against golden standard."""
    golden = load_golden_standard(simulation_name)

    print(f"\n{'='*60}")
    print(f"Evaluating: {simulation_name}")
    print(f"Paper: {Path(paper_path).name}")
    print(f"Model: {model}")
    if custom_prompt:
        print(f"Instruction: {custom_prompt}")
    print(f"{'='*60}")

    start = time.time()
    result = run_single_extraction(paper_path, "mp-gadget", custom_prompt, model)
    elapsed = time.time() - start

    formatted = result.get("formatted_parameters", {})
    score = score_extraction(formatted, golden)

    print(f"\nResults ({elapsed:.1f}s):")
    print(f"  Accuracy: {score['accuracy']*100:.1f}%")
    print(f"  Correct: {score['correct']}/{score['total']}")
    print(f"  Wrong: {score['wrong']}")
    print(f"  Missing: {score['missing']}")
    print(f"  Extra: {score['extra']}")

    # Show wrong/missing details
    for d in score["details"]:
        if d["status"] == "wrong":
            print(f"  WRONG: {d['param']} = {d['extracted']} (expected {d['golden']})")
        elif d["status"] == "missing":
            print(f"  MISSING: {d['param']} (expected {d['golden']})")

    return {
        "simulation": simulation_name,
        "paper": str(paper_path),
        "model": model,
        "elapsed_seconds": round(elapsed, 1),
        "score": score,
        "status": result.get("status", "unknown"),
    }


def run_evaluation_suite(
    paper_path: str,
    simulations: list[dict],
    model: str = "gpt-5.4-mini",
) -> list[dict]:
    """Run evaluation for multiple simulations from the same paper."""
    results = []
    for sim in simulations:
        try:
            r = evaluate_paper(
                paper_path,
                sim["simulation_name"],
                sim.get("instruction"),
                model,
            )
            results.append(r)
        except Exception as e:
            print(f"ERROR evaluating {sim['simulation_name']}: {e}")
            results.append({"simulation": sim["simulation_name"], "error": str(e)})

    # Summary
    total_correct = sum(r.get("score", {}).get("correct", 0) for r in results if "score" in r)
    total_params = sum(r.get("score", {}).get("total", 0) for r in results if "score" in r)
    overall_accuracy = total_correct / total_params if total_params > 0 else 0

    print(f"\n{'='*60}")
    print(f"OVERALL: {overall_accuracy*100:.1f}% ({total_correct}/{total_params})")
    print(f"{'='*60}")

    return results


if __name__ == "__main__":
    # Quick test with the example paper
    paper = str(PROJECT_ROOT / "example" / "2105.01016v2.pdf")

    # Check which golden standards match this paper
    mapping = load_paper_mapping()

    # For a quick test, just evaluate one simulation
    if len(sys.argv) > 1:
        sim_name = sys.argv[1]
        paper_file = sys.argv[2] if len(sys.argv) > 2 else paper
        instruction = sys.argv[3] if len(sys.argv) > 3 else None
        evaluate_paper(paper_file, sim_name, instruction)
    else:
        # Default: evaluate the example paper against dmo-100MPC-64
        print("Usage: python eval/evaluate.py <simulation_name> [paper_path] [instruction]")
        print("\nRunning default evaluation: dmo-100MPC-64")
        evaluate_paper(paper, "dmo-100MPC-64", "Extract parameters for the low-resolution 100 Mpc/h dark matter only simulation with 64^3 particles")
