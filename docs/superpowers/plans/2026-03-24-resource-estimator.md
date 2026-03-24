# Resource Estimator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a resource estimator node to the LangGraph pipeline that estimates memory, CPU-hours, wall-clock time, storage, and recommended nodes after parameter extraction completes.

**Architecture:** New `estimator` node runs after `save_output` using three signals: pure-Python heuristic scaling, a curated resource database (`data/resource_database.md`), and LLM synthesis. Results shown in a new "Estimates" tab in the GUI and as a chat message.

**Tech Stack:** Existing LangGraph pipeline + resource_database.md (already created) + new estimator node + frontend Estimates tab

**Spec:** `docs/superpowers/specs/2026-03-24-resource-estimator-design.md`

---

## File Structure

### New files
```
simagents/nodes/estimator.py         # Estimator node: heuristic + LLM synthesis
simagents/prompts/estimator.md       # Prompt template for LLM synthesis
tests/test_nodes/test_estimator.py   # Tests for heuristic + node
```

### Modified files
```
simagents/graph/state.py             # Add resource_estimates field
simagents/graph/parameter_extraction.py  # Add estimator node + conditional edge
simagents/nodes/__init__.py          # Export estimator
simagents/config/settings.py         # Add run_estimator toggle
simagents/types.py                   # Add ResourceEstimates type
simagents/api/routes/extract.py      # Stream estimator events, fix complete ordering
frontend/src/lib/types.ts            # Add ResourceEstimates interface
frontend/src/components/ParameterPanel.tsx  # Add Estimates tab
frontend/src/app/page.tsx            # Handle resource_estimates SSE event
main.py                              # Print estimates
```

---

## Task 0: Types, State, Config Updates

**Files:**
- Modify: `simagents/types.py`
- Modify: `simagents/graph/state.py`
- Modify: `simagents/config/settings.py`
- Modify: `config.example.yaml`

- [ ] **Step 1: Add ResourceEstimates type to types.py**

Add to `simagents/types.py`:

```python
class ResourceEstimates(TypedDict):
    """Compute resource estimates for a simulation."""
    memory_per_node_gb: float
    total_cpu_hours: int
    wall_clock: str
    storage_tb: float
    recommended_nodes: int
    confidence: str  # "high" | "medium" | "low"
    reference_simulation: str
    reasoning: str
```

Add `resource_estimates: dict` to `ExtractionOutput`.

- [ ] **Step 2: Add resource_estimates to ExtractionState**

Add to `simagents/graph/state.py`:

```python
resource_estimates: dict  # Populated by estimator node
```

- [ ] **Step 3: Add run_estimator toggle to config**

Add to `ExtractionSettings` in `simagents/config/settings.py`:

```python
run_estimator: bool = True
```

Add to `config.example.yaml` under `extraction:`:

```yaml
run_estimator: true           # Set false to skip resource estimation
```

- [ ] **Step 4: Update tests**

Update `tests/test_types.py` to include `resource_estimates` and `ic_notes` in test dicts.

- [ ] **Step 5: Run tests, commit**

```bash
conda run -n langgraph pytest tests/test_types.py tests/test_config.py -v
git add simagents/types.py simagents/graph/state.py simagents/config/settings.py config.example.yaml tests/
git commit -m "feat: add ResourceEstimates type, state field, run_estimator config toggle"
```

---

## Task 1: Estimator Node (Heuristic + LLM)

**Files:**
- Create: `simagents/nodes/estimator.py`
- Create: `simagents/prompts/estimator.md`
- Create: `tests/test_nodes/test_estimator.py`
- Modify: `simagents/nodes/__init__.py`

- [ ] **Step 1: Write tests**

Create: `tests/test_nodes/test_estimator.py`

```python
"""Tests for the resource estimator node."""
import json
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from simagents.nodes.estimator import estimator, compute_heuristic


def test_compute_heuristic_dm_only():
    """Heuristic estimates for a DM-only simulation."""
    sections = {"params": {"Ngrid": 512, "BoxSize": 100000, "Redshift": 99, "TimeMax": 1.0}}
    result = compute_heuristic(sections, "mp-gadget")
    assert result["memory_gb"] > 0
    assert result["cpu_hours"] > 0
    assert result["storage_gb"] > 0
    assert result["n_particles"] == 512**3


def test_compute_heuristic_hydro():
    """Hydro simulations should have higher resource estimates."""
    dm_sections = {"params": {"Ngrid": 512, "BoxSize": 100000, "Redshift": 99}}
    hydro_sections = {"params": {"Ngrid": 512, "BoxSize": 100000, "Redshift": 99, "OmegaBaryon": 0.049}}
    dm = compute_heuristic(dm_sections, "mp-gadget")
    hydro = compute_heuristic(hydro_sections, "mp-gadget")
    assert hydro["memory_gb"] > dm["memory_gb"]
    assert hydro["cpu_hours"] > dm["cpu_hours"]


def test_compute_heuristic_missing_params():
    """Heuristic handles missing parameters gracefully."""
    sections = {"params": {"BoxSize": 100000}}  # No Ngrid
    result = compute_heuristic(sections, "mp-gadget")
    assert result["n_particles"] == 0 or result["memory_gb"] == 0


def test_estimator_node():
    """Estimator node returns structured resource_estimates."""
    state = {
        "formatted_parameters": {
            "sections": {"params": {"Omega0": 0.3, "BoxSize": 100000, "Ngrid": 512, "Redshift": 99}},
            "comment": "test",
        },
        "target_software": "mp-gadget",
        "status": "complete",
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content=json.dumps({
        "memory_per_node_gb": 64,
        "total_cpu_hours": 50000,
        "wall_clock": "~12 hours on 128 cores",
        "storage_tb": 0.5,
        "recommended_nodes": 4,
        "confidence": "medium",
        "reference_simulation": "DMO Medium (1024^3)",
        "reasoning": "Your simulation has 512^3 DM particles..."
    }))
    config = {"configurable": {"llm": mock_llm}}
    result = estimator(state, config)
    assert "resource_estimates" in result
    assert result["resource_estimates"]["total_cpu_hours"] == 50000
    assert result["resource_estimates"]["confidence"] == "medium"
```

- [ ] **Step 2: Write estimator prompt**

Create: `simagents/prompts/estimator.md`

```
You are an expert in HPC resource estimation for cosmological simulations.

## Simulation Parameters
{parameters}

## Target Software: {target_software}

## Heuristic Estimates (starting point — may be rough)
{heuristic_estimates}

## Resource Database (historical data from published simulations)
{resource_database}

## Your Task
1. Find the closest reference simulation(s) in the database to the user's parameters
2. Explain how the user's simulation differs (particle count, box size, physics modules)
3. Scale the reference's reported resources to estimate the user's requirements
4. Combine with the heuristic estimates to produce a final estimate
5. Rate your confidence: high (very close match), medium (reasonable extrapolation), low (large extrapolation)

## Output Format
Respond with ONLY this JSON (no additional text):

{{{{
    "memory_per_node_gb": <number>,
    "total_cpu_hours": <number>,
    "wall_clock": "<human-readable, e.g. ~3 days on 256 cores>",
    "storage_tb": <number>,
    "recommended_nodes": <number>,
    "confidence": "high|medium|low",
    "reference_simulation": "<name of nearest match from database>",
    "reasoning": "<2-3 paragraph explanation>"
}}}}
```

Note: quadruple braces `{{{{` because the formatter node renders with `.format()` first (escaping to `{{`), then the estimator node renders again (escaping to `{`).

Actually, the estimator node will render this prompt directly (not via the formatter). So use double braces `{{` for the JSON output example:

```
{{
    "memory_per_node_gb": <number>,
    ...
}}
```

- [ ] **Step 3: Write estimator.py**

Create: `simagents/nodes/estimator.py`

```python
"""estimator node — estimates compute resources for the extracted simulation."""
from __future__ import annotations
import json
import math
from pathlib import Path
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from simagents.graph.state import ExtractionState
from simagents.nodes.formatter import _extract_json

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "estimator.md"
_DB_PATH = Path(__file__).parent.parent.parent / "data" / "resource_database.md"


def compute_heuristic(sections: dict, target_software: str) -> dict:
    """Pure-Python heuristic resource estimates from scaling laws."""
    # Find particle-related parameters across all sections
    all_params = {}
    for sec_params in sections.values():
        if isinstance(sec_params, dict):
            all_params.update(sec_params)

    # Extract key values
    ngrid = all_params.get("Ngrid") or all_params.get("GridSize") or all_params.get("Nmesh") or 0
    if isinstance(ngrid, str):
        try:
            ngrid = int(ngrid)
        except ValueError:
            ngrid = 0

    is_hydro = bool(all_params.get("OmegaBaryon") or all_params.get("Omega_b") or all_params.get("ProduceGas"))
    n_particles = int(ngrid) ** 3
    if is_hydro:
        n_particles *= 2  # DM + gas

    z_start = float(all_params.get("Redshift") or all_params.get("a_begin") or 99)
    if z_start < 1:  # a_begin is scale factor, convert
        z_start = (1.0 / z_start) - 1 if z_start > 0 else 99

    n_timesteps = int((z_start + 1) * 50)
    n_snapshots = 20  # default estimate

    # Memory: bytes per particle
    bytes_per_particle = 500 if is_hydro else 150
    memory_gb = n_particles * bytes_per_particle / 1e9

    # Compute: N log N * timesteps * physics overhead
    if n_particles > 0:
        base_flops = n_particles * math.log2(max(n_particles, 1)) * n_timesteps
        physics_multiplier = 4.0 if is_hydro else 1.0
        # Rough calibration: TNG100 (2*1820^3, hydro) ~ 5.5M CPU-hours
        # That's ~1.2e10 particles, ~5000 timesteps, multiplier 4 → base ~2e14
        # 5.5e6 / 2e14 → ~2.75e-8 CPU-hours per base_flop
        cpu_hours = base_flops * 2.75e-8 * physics_multiplier
    else:
        cpu_hours = 0

    # Storage: bytes per particle per snapshot
    snapshot_bytes = (200 if is_hydro else 40) * n_particles
    storage_gb = snapshot_bytes * n_snapshots / 1e9

    return {
        "n_particles": n_particles,
        "is_hydro": is_hydro,
        "memory_gb": round(memory_gb, 1),
        "cpu_hours": round(cpu_hours),
        "storage_gb": round(storage_gb, 1),
        "n_timesteps": n_timesteps,
    }


def _load_prompt(parameters: str, target_software: str, heuristic: str, database: str) -> str:
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    return template.format(
        parameters=parameters,
        target_software=target_software,
        heuristic_estimates=heuristic,
        resource_database=database,
    )


def estimator(state: ExtractionState, config: RunnableConfig) -> dict:
    """Estimate compute resources using heuristic + LLM synthesis."""
    configurable = config.get("configurable", {})
    llm = configurable["llm"]

    formatted = state.get("formatted_parameters", {})
    sections = formatted.get("sections", {})
    target_software = state.get("target_software", "mp-gadget")

    # 1. Heuristic estimates
    heuristic = compute_heuristic(sections, target_software)

    # 2. Load resource database
    db_content = ""
    if _DB_PATH.exists():
        db_content = _DB_PATH.read_text(encoding="utf-8")

    # 3. Build prompt
    params_str = json.dumps(sections, indent=2)
    heuristic_str = json.dumps(heuristic, indent=2)
    system_prompt = _load_prompt(params_str, target_software, heuristic_str, db_content)

    # 4. LLM synthesis
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Please estimate the compute resources for this simulation."),
    ]

    try:
        response = llm.invoke(messages)
        estimates = _extract_json(response.content)
    except Exception:
        # Non-fatal: return heuristic-only estimates
        estimates = {
            "memory_per_node_gb": round(heuristic["memory_gb"] / 64, 1) if heuristic["memory_gb"] > 0 else 0,
            "total_cpu_hours": heuristic["cpu_hours"],
            "wall_clock": "unknown (LLM estimation failed)",
            "storage_tb": round(heuristic["storage_gb"] / 1000, 2),
            "recommended_nodes": max(1, round(heuristic["memory_gb"] / 128)),
            "confidence": "low",
            "reference_simulation": "none (heuristic only)",
            "reasoning": f"LLM estimation failed. Heuristic estimates: {heuristic['n_particles']} particles, {heuristic['memory_gb']} GB memory, {heuristic['cpu_hours']} CPU-hours.",
        }

    return {"resource_estimates": estimates}
```

- [ ] **Step 4: Update nodes/__init__.py**

Add: `from .estimator import estimator` and add to `__all__`.

- [ ] **Step 5: Run tests, commit**

```bash
conda run -n langgraph pytest tests/test_nodes/test_estimator.py -v
git add simagents/nodes/estimator.py simagents/prompts/estimator.md simagents/nodes/__init__.py tests/test_nodes/test_estimator.py
git commit -m "feat: add estimator node with heuristic scaling and LLM synthesis"
```

---

## Task 2: Wire Estimator into Graph

**Files:**
- Modify: `simagents/graph/parameter_extraction.py`
- Modify: `tests/test_graph/test_parameter_extraction.py`

- [ ] **Step 1: Update graph construction**

Modify `simagents/graph/parameter_extraction.py`:

```python
from simagents.nodes import parse_input, physics_expert, formatter, check_done, ask_user, save_output, estimator

def create_extraction_graph(settings: Settings, checkpointer: BaseCheckpointSaver | None = None):
    graph = StateGraph(ExtractionState)
    graph.add_node("parse_input", parse_input)
    graph.add_node("physics_expert", physics_expert)
    graph.add_node("formatter", formatter)
    graph.add_node("ask_user", ask_user)
    graph.add_node("save_output", save_output)
    graph.add_node("estimator", estimator)
    graph.set_entry_point("parse_input")
    graph.add_edge("parse_input", "physics_expert")
    graph.add_edge("physics_expert", "formatter")
    graph.add_conditional_edges("formatter", check_done, {"done": "save_output", "loop": "physics_expert", "needs_user_input": "ask_user"})
    graph.add_edge("ask_user", "physics_expert")

    # After save_output: estimate if params exist and estimator is enabled
    def should_estimate(state):
        sections = state.get("formatted_parameters", {}).get("sections", {})
        has_params = any(bool(v) for v in sections.values())
        if has_params:
            return "estimate"
        return "end"

    graph.add_conditional_edges("save_output", should_estimate, {"estimate": "estimator", "end": END})
    graph.add_edge("estimator", END)
    return graph.compile(checkpointer=checkpointer)
```

- [ ] **Step 2: Update graph integration test**

Update mock LLM to return a third response (for estimator) and add `resource_estimates: {}` to initial state. Verify `resource_estimates` is populated in result.

- [ ] **Step 3: Run tests, commit**

```bash
conda run -n langgraph pytest tests/ -v
git add simagents/graph/ tests/test_graph/
git commit -m "feat: wire estimator node into extraction graph with conditional edge"
```

---

## Task 3: Update SSE Streaming

**Files:**
- Modify: `simagents/api/routes/extract.py`

- [ ] **Step 1: Update _stream_events**

In `_stream_events()`:

1. Remove the `{"type": "complete"}` emission from the `save_output` handler
2. Add handler for `estimator` node:
```python
elif "estimator" in event:
    data = event["estimator"]
    estimates = data.get("resource_estimates", {})
    session.resource_estimates = estimates
    # Emit resource_estimates event
    yield {"event": "message", "data": json.dumps({"type": "resource_estimates", "data": estimates})}
    # Emit agent message with reasoning
    reasoning = estimates.get("reasoning", "")
    if reasoning:
        msg = {"type": "agent_message", "role": "estimator", "content": reasoning}
        session.messages.append(msg)
        yield {"event": "message", "data": json.dumps(msg)}
```
3. After the `async for` loop ends, emit `{"type": "complete"}`:
```python
# After the loop
session.status = "complete"
yield {"event": "message", "data": json.dumps({"type": "complete", "status": "complete"})}
```

- [ ] **Step 2: Update initial state**

Add `"resource_estimates": {}` to `session._initial_state` in `_build_graph_and_config`.

- [ ] **Step 3: Commit**

```bash
git add simagents/api/routes/extract.py
git commit -m "feat: stream estimator events via SSE, fix complete event ordering"
```

---

## Task 4: Frontend — Estimates Tab

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/components/ParameterPanel.tsx`
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Update types.ts**

Add:

```typescript
export interface ResourceEstimates {
  memory_per_node_gb: number;
  total_cpu_hours: number;
  wall_clock: string;
  storage_tb: number;
  recommended_nodes: number;
  confidence: string;
  reference_simulation: string;
  reasoning: string;
}
```

- [ ] **Step 2: Update page.tsx**

Add `resourceEstimates` state. Handle `resource_estimates` SSE event type:

```typescript
case "resource_estimates":
  if (event.data) {
    setResourceEstimates(event.data as ResourceEstimates);
  }
  break;
```

Pass `resourceEstimates` to `ParameterPanel`.

- [ ] **Step 3: Update ParameterPanel.tsx**

Add "Estimates" tab (rendered last, after dynamic sections + Sources). Content:

- Memory: value with context
- CPU-hours: value with scale context
- Wall-clock: human-readable
- Storage: TB
- Recommended nodes: count
- Confidence: colored badge (green/orange/red)
- Reference: simulation name

Style the estimator chat message with a teal color (distinct from physics expert green and formatter purple).

When no estimates: "Complete the extraction to get resource estimates."

- [ ] **Step 4: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add Estimates tab to parameter panel with resource visualization"
```

---

## Task 5: CLI & Final Cleanup

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update main.py**

After extraction completes, print resource estimates:

```python
estimates = result.get("resource_estimates", {})
if estimates:
    print("\n--- Resource Estimates ---")
    print(f"Memory: {estimates.get('memory_per_node_gb', '?')} GB/node")
    print(f"CPU-hours: {estimates.get('total_cpu_hours', '?')}")
    print(f"Wall-clock: {estimates.get('wall_clock', '?')}")
    print(f"Storage: {estimates.get('storage_tb', '?')} TB")
    print(f"Nodes: {estimates.get('recommended_nodes', '?')}")
    print(f"Confidence: {estimates.get('confidence', '?')}")
    print(f"Based on: {estimates.get('reference_simulation', '?')}")
```

Also add `"resource_estimates": {}` to the initial state dict in the invoke call.

- [ ] **Step 2: Run full test suite**

```bash
conda run -n langgraph pytest tests/ -v
cd frontend && npm run build
```

- [ ] **Step 3: Commit and push**

```bash
git add main.py
git commit -m "feat: print resource estimates in CLI output"
git push
```
