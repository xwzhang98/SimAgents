"""estimator node — estimates compute resources required for a simulation."""
from __future__ import annotations
import json
import math
from pathlib import Path
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from simagents.graph.state import ExtractionState
from simagents.nodes.formatter import _extract_json

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "estimator.md"
_RESOURCE_DB_PATH = Path(__file__).parent.parent.parent / "data" / "resource_database.md"


def compute_heuristic(sections: dict, target_software: str) -> dict:
    """Pure Python heuristic estimates — no LLM required.

    Extracts Ngrid/GridSize from parameters, computes particle counts, and
    estimates memory, CPU-hours, and storage requirements.
    """
    # Flatten all section params into one dict for easier lookup
    all_params: dict = {}
    for section_params in sections.values():
        if isinstance(section_params, dict):
            all_params.update(section_params)

    # Detect grid size
    ngrid = None
    for key in ("Ngrid", "NgridForces", "GridSize", "pmgrid", "PMGRID"):
        val = all_params.get(key)
        if val is not None:
            try:
                ngrid = int(float(str(val)))
                break
            except (ValueError, TypeError):
                pass

    # Detect if hydrodynamic from baryon/gas parameters
    is_hydro = False
    for key in ("OmegaBaryon", "Omega_b", "ProduceGas", "SphType", "Baryon"):
        val = all_params.get(key)
        if val is not None:
            if str(val).lower() not in ("0", "false", "none", ""):
                is_hydro = True
                break

    # Number of particles
    n_particles = 0
    if ngrid is not None and ngrid > 0:
        n_particles = ngrid ** 3
        if is_hydro:
            n_particles *= 2  # DM + gas particles

    # Bytes per particle
    bytes_per_particle = 500 if is_hydro else 150

    # Memory estimate in GB
    memory_bytes = n_particles * bytes_per_particle
    memory_gb = memory_bytes / (1024 ** 3)

    # Timesteps estimate
    timesteps = all_params.get("MaxSizeTimestep", None)
    try:
        timesteps = int(float(str(timesteps))) if timesteps else 10000
    except (ValueError, TypeError):
        timesteps = 10000

    # Physics multiplier
    physics_multiplier = 3.0 if is_hydro else 1.0

    # CPU-hours estimate: N * log2(N) * timesteps * multiplier * constant
    cpu_hours = 0
    if n_particles > 0:
        cpu_hours = int(n_particles * math.log2(n_particles) * timesteps * physics_multiplier * 2.75e-8)

    # Storage estimate
    # Snapshot size in bytes (roughly 80 bytes per particle per snapshot)
    n_snapshots_val = all_params.get("NumWrittenSnapshots", all_params.get("OutputListLength", 100))
    try:
        n_snapshots = int(float(str(n_snapshots_val)))
    except (ValueError, TypeError):
        n_snapshots = 100

    snapshot_bytes = n_particles * 80
    storage_bytes = snapshot_bytes * n_snapshots
    storage_gb = storage_bytes / (1024 ** 3)

    return {
        "n_particles": n_particles,
        "is_hydro": is_hydro,
        "memory_gb": round(memory_gb, 2),
        "cpu_hours": cpu_hours,
        "storage_gb": round(storage_gb, 2),
        "ngrid": ngrid,
    }


def estimator(state: ExtractionState, config: RunnableConfig) -> dict:
    """Estimate compute resources for the simulation described in state."""
    configurable = config.get("configurable", {})
    llm = configurable.get("llm")
    target_software = state.get("target_software", "mp-gadget")
    sections = state.get("formatted_parameters", {}).get("sections", {})

    # Compute heuristic estimates
    heuristic = compute_heuristic(sections, target_software)

    # Load resource database
    resource_db = ""
    if _RESOURCE_DB_PATH.exists():
        resource_db = _RESOURCE_DB_PATH.read_text(encoding="utf-8")
    else:
        resource_db = "No reference database available."

    # If LLM not available or no particles found, return heuristic-only
    if llm is None or heuristic["n_particles"] == 0:
        return {
            "resource_estimates": {
                "memory_per_node_gb": heuristic["memory_gb"],
                "total_cpu_hours": heuristic["cpu_hours"],
                "wall_clock": "unknown",
                "storage_tb": round(heuristic["storage_gb"] / 1024, 4),
                "recommended_nodes": 1,
                "confidence": "low",
                "reference_simulation": "none",
                "reasoning": "Heuristic-only estimate. Insufficient parameters for LLM synthesis.",
            }
        }

    # Render prompt
    prompt_template = _PROMPT_PATH.read_text(encoding="utf-8")
    prompt = prompt_template.format(
        parameters=json.dumps(sections, indent=2),
        target_software=target_software,
        heuristic_estimates=json.dumps(heuristic, indent=2),
        resource_database=resource_db,
    )

    messages = [SystemMessage(content=prompt), HumanMessage(content="Please provide the resource estimates for this simulation.")]

    try:
        response = llm.invoke(messages)
        estimates = _extract_json(response.content)
    except Exception:
        # Fall back to heuristic-only estimates
        estimates = {
            "memory_per_node_gb": heuristic["memory_gb"],
            "total_cpu_hours": heuristic["cpu_hours"],
            "wall_clock": "unknown",
            "storage_tb": round(heuristic["storage_gb"] / 1024, 4),
            "recommended_nodes": max(1, heuristic["cpu_hours"] // 10000) if heuristic["cpu_hours"] else 1,
            "confidence": "low",
            "reference_simulation": "none",
            "reasoning": "LLM synthesis failed. Using heuristic estimates only.",
        }

    return {"resource_estimates": estimates}
