# Resource Estimator — Design Spec

## Overview

Add a resource estimator to SimAgents that automatically estimates compute requirements (memory, CPU-hours, wall-clock time, storage, recommended nodes) after parameter extraction completes. Uses three signals: heuristic scaling formulas, a curated resource database of published simulation costs, and LLM reasoning to synthesize a grounded estimate.

**Branch:** `feature/multi-software` (extends current work)

---

## 1. Resource Database

### File: `data/resource_database.md`

A curated markdown file containing historical compute costs mined from published simulation papers. Covers multiple simulation software, scales from small (256³) to flagship (10000³+).

### Structure

Each entry contains:
- Simulation name and paper citation
- Software used
- Box size, particle count, physics modules
- CPU-hours or node-hours
- Number of nodes/cores
- Memory per node
- Storage requirements
- Wall-clock time

### Coverage targets

**By software:** MP-Gadget (BlueTides, ASTRID, DMO runs), Arepo (IllustrisTNG series), SWIFT (FLAMINGO series), GIZMO (FIRE-2 zoom-ins, SIMBA), Gadget-2/3 (Millennium, EAGLE, Magneticum)

**By scale:**
- Small: 50-100 Mpc/h, 256³-512³ particles (hours on workstation)
- Medium: 100-300 Mpc/h, 1024³-2048³ particles (days on small cluster)
- Large: 300 Mpc/h, 2500³-5040³ particles (weeks-months on HPC)
- Flagship: 1000+ Mpc/h, 10000³+ particles (months on top-tier HPC)

### Scaling formulas (included in the database)

```
Memory:
- DM only: ~80 bytes/particle → memory_GB ≈ N_particles × 80 / 1e9
- Hydro (DM + gas): ~200 bytes/particle → memory_GB ≈ N_particles × 200 / 1e9
- Per-node: total_memory / N_nodes (must fit in node RAM, typically 128-256 GB)

Compute:
- N-body: O(N × log(N) × N_timesteps)
- N_timesteps ≈ (z_start + 1) × 50 for typical cosmological runs
- Hydro overhead: ~3-5x over DM-only
- MHD: ~1.5x over hydro
- Star formation/AGN: ~1.2-2x depending on resolution

Storage:
- DM only: ~24 bytes/particle/snapshot
- Hydro: ~100 bytes/particle/snapshot
- Total: N_snapshots × per_snapshot_size
```

### How the database is built

1. Mine compute costs from papers already downloaded (`example/` directory) and golden standard paper references
2. Web search for additional published costs of major simulations
3. Store in structured markdown — small enough to fit directly in LLM context (~2-3K tokens)

### Usage

Loaded directly into the estimator prompt (not RAG). The LLM reads the full database and finds the nearest reference simulation to the user's extracted parameters.

---

## 2. Estimator Node

### New file: `simagents/nodes/estimator.py`

A LangGraph node that runs after `save_output` when extraction status is "complete".

### Behavior

```python
def estimator(state: ExtractionState, config: RunnableConfig) -> dict:
    # 1. Extract simulation parameters from state
    params = state.get("formatted_parameters", {})
    sections = params.get("sections", {})

    # 2. Compute heuristic estimates (pure Python, no LLM)
    heuristic = compute_heuristic(sections, state.get("target_software"))

    # 3. Load resource_database.md
    db_content = load_resource_database()

    # 4. Load and render estimator prompt with: parameters + heuristic + database
    # 5. Call LLM to synthesize final estimate with reasoning

    # 6. Return structured estimates
    return {
        "resource_estimates": {
            "memory_per_node_gb": <float>,
            "total_cpu_hours": <int>,
            "wall_clock": <str>,        # human-readable, e.g., "~3 days on 256 cores"
            "storage_tb": <float>,
            "recommended_nodes": <int>,
            "confidence": <str>,         # "high" | "medium" | "low"
            "reference_simulation": <str>,  # name of nearest match
            "reasoning": <str>,          # LLM explanation (posted as chat message)
        }
    }
```

### `compute_heuristic()` — pure Python, no LLM

Extracts from the parameter sections:
- `N_particles`: from Ngrid/GridSize (cubed, doubled if hydro)
- `box_size`: from BoxSize (converted to consistent units)
- `is_hydro`: from presence of gas/baryon parameters
- `z_start`: from starting redshift
- `n_snapshots`: from output list length or estimate

Applies scaling formulas from the database to produce initial estimates.

### Estimator prompt: `simagents/prompts/estimator.md`

Template variables: `{parameters}`, `{heuristic_estimates}`, `{resource_database}`, `{target_software}`

```
You are an expert in HPC resource estimation for cosmological simulations.

## Simulation Parameters
{parameters}

## Target Software: {target_software}

## Heuristic Estimates (starting point)
{heuristic_estimates}

## Resource Database (historical data from published simulations)
{resource_database}

## Your Task
1. Find the closest reference simulation(s) in the database to the user's parameters
2. Explain how the user's simulation differs (particle count, box size, physics)
3. Scale the reference's reported resources to estimate the user's requirements
4. Combine with the heuristic estimates to produce a final estimate
5. Rate your confidence (high: very close match, medium: reasonable extrapolation, low: large extrapolation)

## Output Format
Respond with ONLY this JSON:
{
    "memory_per_node_gb": <number>,
    "total_cpu_hours": <number>,
    "wall_clock": "<human-readable string>",
    "storage_tb": <number>,
    "recommended_nodes": <number>,
    "confidence": "high|medium|low",
    "reference_simulation": "<name of nearest match>",
    "reasoning": "<2-3 paragraph explanation of how you arrived at the estimate>"
}
```

---

## 3. Graph Topology Change

### Current graph:
```
parse_input → physics_expert → formatter → check_done → save_output → END
                                              ↑
                                         loop/ask_user
```

### New graph:
```
parse_input → physics_expert → formatter → check_done → save_output → estimator → END
                                              ↑
                                         loop/ask_user
```

The conditional edge from `check_done` still routes to `save_output` when "done". After `save_output`, the graph proceeds to `estimator`, then END.

### Skip condition

The estimator should only run when extraction completed successfully. If `save_output` returns `status: "incomplete"`, the estimator should be skipped. This is implemented as a conditional edge after `save_output`:

```python
def should_estimate(state):
    if state.get("status") == "complete":
        return "estimate"
    return "end"

graph.add_conditional_edges("save_output", should_estimate, {"estimate": "estimator", "end": END})
```

---

## 4. State Changes

### `ExtractionState` — add field:
```python
resource_estimates: dict  # Populated by estimator node
```

### `ExtractionOutput` — add field:
```python
resource_estimates: dict  # memory, cpu_hours, wall_clock, storage, nodes, confidence, reasoning
```

---

## 5. SSE Streaming

### New event type:
```json
{"type": "resource_estimates", "data": {
    "memory_per_node_gb": 128,
    "total_cpu_hours": 500000,
    "wall_clock": "~3 days on 256 cores",
    "storage_tb": 2.5,
    "recommended_nodes": 64,
    "confidence": "medium",
    "reference_simulation": "TNG300-1",
    "reasoning": "Your simulation is similar to..."
}}
```

### Chat message:
The estimator's `reasoning` field is also posted as an `agent_message` with `role: "estimator"` so it appears in the chat conversation.

---

## 6. GUI Changes

### Estimates tab in ParameterPanel

Added as the last tab (after software-specific sections and Sources). Shows:
- **Memory:** value + context bar (typical node sizes: 128/256/512 GB)
- **CPU-hours:** value + context ("small: 100K, medium: 1M, large: 10M")
- **Wall-clock:** human-readable estimate
- **Storage:** total snapshot storage
- **Recommended nodes:** node count × cores
- **Confidence:** colored badge (green=high, orange=medium, red=low)
- **Reference:** "Based on TNG300-1 (Pillepich+2018)"

When extraction is incomplete or estimator hasn't run: "Complete the extraction to get resource estimates."

### Chat message

The estimator posts a message styled with a new role color (e.g., teal for estimator, distinct from green/purple for physics expert/formatter). Shows the reasoning text.

---

## 7. File Changes

| Action | File |
|--------|------|
| **New** | `data/resource_database.md` |
| **New** | `simagents/nodes/estimator.py` |
| **New** | `simagents/prompts/estimator.md` |
| **New** | `tests/test_nodes/test_estimator.py` |
| **Modify** | `simagents/graph/parameter_extraction.py` — add estimator node + conditional edge |
| **Modify** | `simagents/graph/state.py` — add resource_estimates field |
| **Modify** | `simagents/types.py` — add resource_estimates to ExtractionOutput |
| **Modify** | `simagents/nodes/__init__.py` — export estimator |
| **Modify** | `simagents/api/routes/extract.py` — stream estimator events |
| **Modify** | `frontend/src/lib/types.ts` — add ResourceEstimates interface |
| **Modify** | `frontend/src/components/ParameterPanel.tsx` — add Estimates tab |
| **Modify** | `frontend/src/app/page.tsx` — handle resource_estimates SSE event |
| **Modify** | `main.py` — print estimates after extraction |

### What does NOT change
- Profile system
- Physics expert / formatter / save_output nodes (only graph wiring changes)
- Settings / config
- Upload / settings / profiles API routes
