"""Batch evaluation against golden standard papers."""
from __future__ import annotations
import json
import sys
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from eval.evaluate import evaluate_paper, load_paper_mapping

PAPERS_DIR = PROJECT_ROOT / "golden_standard" / "papers"
EXAMPLE_DIR = PROJECT_ROOT / "example"

# Select one representative simulation per paper (avoid duplicates)
TEST_CASES = [
    # Paper, simulation, instruction, paper_location
    ("2105.01016v2.pdf", "dmo-100MPC-64", "Extract parameters for the low-resolution 100 Mpc/h dark matter only simulation with 64 particles per side", PAPERS_DIR),
    ("2105.01016v2.pdf", "dmo-100MPC-512", "Extract parameters for the high-resolution 100 Mpc/h dark matter only simulation with 512 particles per side", PAPERS_DIR),
    ("illustrisTNG.pdf", "TNG100-1", "Extract parameters for the TNG100-1 simulation run (75 Mpc/h box, highest resolution)", PAPERS_DIR),
    ("illustrisTNG.pdf", "TNG300-1", "Extract parameters for the TNG300-1 simulation run (205 Mpc/h box, highest resolution)", PAPERS_DIR),
    ("2111.01160v2.pdf", "astrid", "Extract parameters for the ASTRID simulation", PAPERS_DIR),
    ("bluetides.pdf", "BlueTides", "Extract parameters for the BlueTides simulation", PAPERS_DIR),
    ("eagle.pdf", "L100N1504", "Extract parameters for the L100N1504 EAGLE simulation (100 Mpc box, 1504^3 particles)", PAPERS_DIR),
    ("simba.pdf", "m100n1024", "Extract parameters for the m100n1024 SIMBA simulation (100 Mpc/h box, 1024^3 particles)", PAPERS_DIR),
]


def run_batch(model: str = "gpt-5.4-mini", max_tests: int = None):
    results = []
    cases = TEST_CASES[:max_tests] if max_tests else TEST_CASES

    for paper_file, sim_name, instruction, paper_dir in cases:
        paper_path = str(paper_dir / paper_file)
        if not Path(paper_path).exists():
            print(f"SKIP: {paper_file} not found")
            continue

        try:
            r = evaluate_paper(paper_path, sim_name, instruction, model)
            results.append(r)
        except Exception as e:
            print(f"ERROR: {sim_name}: {e}")
            results.append({"simulation": sim_name, "error": str(e)})

    # Summary
    print(f"\n{'='*70}")
    print(f"BATCH SUMMARY ({model})")
    print(f"{'='*70}")
    total_correct = 0
    total_params = 0
    for r in results:
        if "score" in r:
            s = r["score"]
            total_correct += s["correct"]
            total_params += s["total"]
            print(f"  {r['simulation']:25s} {s['accuracy']*100:5.1f}%  ({s['correct']}/{s['total']})  wrong={s['wrong']} missing={s['missing']}")
        elif "error" in r:
            print(f"  {r['simulation']:25s} ERROR: {r['error'][:60]}")

    if total_params > 0:
        overall = total_correct / total_params * 100
        print(f"\n  OVERALL: {overall:.1f}% ({total_correct}/{total_params})")

    # Save results
    out_path = PROJECT_ROOT / "eval" / f"results_{model.replace('.', '_')}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "gpt-5.4-mini"
    max_tests = int(sys.argv[2]) if len(sys.argv) > 2 else None
    run_batch(model, max_tests)
