# Multi-Software Support — Design Spec

## Overview

Extend SimAgents to support multiple cosmological simulation software packages beyond MP-Gadget. Uses a **software profile system** where each supported code gets a profile folder containing metadata, parameter naming maps, reference docs (for RAG), and native param file templates.

**Supported software (Tier 1 + SWIFT):**
- MP-Gadget (existing, migrated to profile system)
- Gadget-4
- Arepo
- GIZMO
- SWIFT

**Branch:** `feature/multi-software` from `feature/langgraph-rewrite`

---

## 1. Software Profile System

### Directory structure

```
data/software_profiles/
  mp-gadget/
    profile.yaml
    templates/
      genic_params.txt.j2
      gadget_params.txt.j2
    docs/
      paramfile_reference.md
      genic_reference.md
  gadget-4/
    profile.yaml
    templates/
      params.txt.j2
    docs/
      paramfile_reference.md
  arepo/
    profile.yaml
    templates/
      params.txt.j2
    docs/
      paramfile_reference.md
  gizmo/
    profile.yaml
    templates/
      params.txt.j2
    docs/
      paramfile_reference.md
  swift/
    profile.yaml
    templates/
      swift_params.yml.j2
    docs/
      parameter_reference.md
```

### `profile.yaml` schema

```yaml
name: "Software Name"
description: "One-line description"
family: "gadget"                     # gadget | swift | enzo — helps physics_expert tailor search

output:
  format: "key-value"               # key-value | yaml | ini
  sections:
    - name: "section_name"
      description: "What this section configures"
      filename_template: "{paper}_section.json"
      native_template: "section.txt.j2"   # Jinja2 template for native format (optional)
  comment_prefix: "%"               # For native format comments

units:
  length: "kpc"                     # kpc | kpc/h | Mpc | Mpc/h
  mass: "1e10_Msun"
  velocity: "km/s"
  box_size_unit: "kpc"              # Unit for BoxSize parameter

ic_generator: "builtin"             # builtin | external | none
ic_note: "How to generate ICs for this software"

parameter_names:
  # Canonical name → software-specific name
  # Cosmology
  matter_density: "Omega0"
  dark_energy_density: "OmegaLambda"
  baryon_density: "OmegaBaryon"
  hubble_parameter: "HubbleParam"
  sigma8: "Sigma8"
  spectral_index: "PrimordialIndex"
  cmb_temperature: "CMBTemperature"
  # Box
  box_size: "BoxSize"
  # Resolution
  grid_size: "Ngrid"
  mesh_size: "Nmesh"
  # Time
  time_begin: "TimeBegin"
  time_end: "TimeMax"
  # I/O
  output_dir: "OutputDir"
  ic_file: "InitCondFile"
  output_list: "OutputList"
  # IC
  seed: "Seed"
  starting_redshift: "Redshift"
```

### Scope of `parameter_names`

The mapping covers **~15 core cosmological/simulation parameters** that appear in virtually every simulation paper and have different names across codes. It is NOT intended to be exhaustive. For parameters not in the mapping (e.g., Arepo's `CellShapingSpeed`, GIZMO's `ArtBulkViscConst`), the LLM discovers them via RAG search of the software's docs and uses the software-native name directly. The mapping is a translation aid for the most common parameters, not a complete registry.

### Software-specific profiles

**MP-Gadget** — 2 sections (genic + gadget), builtin IC generator, kpc/h units
**Gadget-4** — 1 section (params), builtin NGENIC (same file), kpc units
**Arepo** — 1 section (params), external IC generator, kpc units
**GIZMO** — 1 section (params), external IC generator, kpc units
**SWIFT** — 1 section (params), external IC generator, Mpc units, YAML format, different naming (`Omega_cdm`, `h`, `a_begin`/`a_end`)

---

## 2. Profile Loader

New module: `simagents/profiles/loader.py`

```python
class SoftwareProfile:
    name: str
    description: str
    family: str
    output: OutputConfig         # sections, format, comment_prefix
    units: UnitConfig
    ic_generator: str
    ic_note: str
    parameter_names: dict[str, str]   # canonical → software-specific
    docs_dir: Path               # Path to docs/ for RAG
    templates_dir: Path          # Path to templates/ for export

def load_profile(software_name: str, profiles_dir: str = "data/software_profiles") -> SoftwareProfile
def list_profiles(profiles_dir: str = "data/software_profiles") -> list[dict]
```

`load_profile()` reads `profile.yaml`, validates it with Pydantic, and returns a `SoftwareProfile` object. Validation is **eager** — if the YAML is malformed or required fields are missing, raises `ValueError` with a clear message. If `docs/` is empty, raises `FileNotFoundError`. This happens when the extract endpoint is called (before graph starts), so the user gets an immediate API error.

`list_profiles()` scans all subdirectories for profiles. Skips directories without `profile.yaml` (no error).

### The `family` field

The `family` field (`"gadget"` | `"swift"` | `"enzo"`) controls a single sentence injected into the physics_expert prompt:

- `family: "gadget"` → "This paper likely uses Gadget-family terminology (Omega0, HubbleParam, BoxSize in kpc/h)."
- `family: "swift"` → "This paper may use SWIFT terminology (Omega_cdm, h, box size in Mpc)."

This is a hint, not a constraint. The physics expert still extracts canonical physics values regardless. The family helps when the same concept has different names in different communities (e.g., papers by SWIFT groups say "Omega_cdm" while Gadget groups say "Omega0").

If `family` is unknown or omitted, no hint is injected.

### `ic_notes` generation

`ic_notes` is computed **deterministically** from the profile, not by the LLM. When `profile.ic_generator == "external"`, the formatter node's post-processing code scans the extracted parameters for IC-relevant ones (starting redshift, sigma8, spectral index, seed) and generates notes like "Sigma8=0.8159 needed for IC generator". This avoids LLM reliability issues.

---

## 3. Changes to Extraction Pipeline

### Physics Expert Node

- Search queries become **canonical** — not software-specific:
  - "matter density parameter Omega"
  - "Hubble constant parameter"
  - "simulation box size length"
  - "particle resolution grid"
  - "initial conditions starting redshift"
  - "power spectrum sigma8 spectral index"
  - "output redshifts scale factors"
- The profile's `family` field is injected into the prompt context so the LLM knows what terminology to expect
- Output format unchanged — structured list of physics values with citations

### Formatter Node

The biggest change. New behavior:

1. Loads `SoftwareProfile` from config (passed via `configurable` dict)
2. RAG searches the profile's `docs/` folder
3. Uses `profile.parameter_names` mapping to translate canonical → software-specific names
4. Uses `profile.output.sections` to structure the output
5. When `profile.ic_generator == "external"`, flags IC-relevant parameters in `ic_notes`

### Formatter prompt changes

`prompts/formatter.md` becomes a template that the formatter node renders with profile data before passing to the LLM. The profile injects: software name, section names, parameter naming reference, unit conventions, and IC generator info.

**Concrete example of the rendered formatter prompt (for Gadget-4):**

```
You are an expert in Gadget-4 simulation software configuration.
You have access to Gadget-4 documentation through search.

## Target Software: Gadget-4

## Output Sections
Your output MUST use these section names:
- "params": Runtime + IC parameter file

## Parameter Naming Reference
Use these exact parameter names for Gadget-4 (canonical → Gadget-4):
- Matter density → Omega0
- Dark energy density → OmegaLambda
- Baryon density → OmegaBaryon
- Hubble parameter → HubbleParam
- Box size → BoxSize (unit: kpc)
- Sigma8 → Sigma8
- ...

## Unit Conventions
- Length: kpc (NOTE: papers often quote Mpc/h — convert by multiplying by 1000/h)
- Mass: 10^10 M_sun
- Velocity: km/s

## IC Generator Info
Gadget-4 has built-in NGENIC. IC parameters go in the same "params" section.

## Output Format
Respond with ONLY this JSON:
{
  "sections": {
    "params": {
      "Omega0": 0.3089,
      "BoxSize": 75000,
      ...
    }
  },
  "ic_notes": [],
  "comment": "...",
  "sources": [...],
  "status": "complete|incomplete|needs_user_input",
  "missing_parameters": [],
  "user_questions": []
}
```

**For SWIFT, the rendered prompt would differ:**
- Section name: `"params"` but with SWIFT naming (`Omega_cdm`, `h`, `a_begin`)
- Unit note: "Length: Mpc" instead of "kpc"
- IC note: "SWIFT uses external IC generator (MUSIC/monofonIC). Flag IC-relevant params in ic_notes."
- Output example uses SWIFT parameter names

**How `parameter_names` is used:** The mapping dict is rendered as a reference table in the prompt (as shown above). The LLM uses it to translate the physics expert's canonical values into the correct software-specific names. This is prompt-injected, not post-processed — the LLM does the translation. For parameters NOT in the mapping, the LLM discovers them from the RAG docs and uses the software-native name directly. The mapping covers ~15 core cosmological parameters; software-specific parameters (e.g., Arepo mesh refinement) are discovered via RAG.

### Formatter fallback on JSON parse failure

When the LLM returns unparseable JSON, the fallback structure becomes:

```python
{
    "sections": {},
    "ic_notes": [],
    "comment": response.content,
    "sources": [],
    "status": "incomplete",
    "missing_parameters": ["JSON_PARSE_FAILED"],
    "user_questions": []
}
```

### Save Output Node

Iterates over `sections` from formatter output:

```python
for section in profile.output.sections:
    params = formatted["sections"].get(section.name, {})
    filename = section.filename_template.format(paper=paper_name)
    write_json({"source": paper_path, "parameters": params, ...}, output_dir / filename)
```

### Docs Loader

Changes from `data/software_docs/{software}/` to `data/software_profiles/{software}/docs/`. The `build_docs_retriever()` function path updates accordingly.

### Config changes

`PathSettings.software_docs_dir` renamed to `software_profiles_dir` with default `"./data/software_profiles"`.

---

## 4. Types — Generic Output

```python
class ExtractionOutput(TypedDict):
    sections: dict[str, dict]       # {"params": {...}} or {"genic": {...}, "gadget": {...}}
    ic_notes: list[str]             # IC-relevant params when ic_generator is external
    status: str                     # "complete" | "incomplete"
    missing: list[str]
    comment: str
    sources: list[dict]
```

Replaces `genic_parameters` + `gadget_parameters`.

### `ExtractionState.formatted_parameters` shape

The `formatted_parameters` field in `ExtractionState` (currently typed as `dict`) will hold the full formatter output:

```python
{
    "sections": {"params": {"Omega0": 0.3089, ...}},
    "ic_notes": [],
    "comment": "...",
    "sources": [...],
}
```

The `status`, `missing_parameters`, and `user_questions` remain as separate top-level state fields (not nested inside `formatted_parameters`), consistent with the current design.

### `SoftwareProfile` carries slug

The `SoftwareProfile` class includes both the slug (directory name, e.g., `"mp-gadget"`) and display name:

```python
class SoftwareProfile:
    slug: str               # Directory name, used for lookups and paths
    name: str               # Display name from profile.yaml
    ...
```

`load_profile("mp-gadget")` sets `slug="mp-gadget"` from the directory name.

---

## 5. Native Param File Export

### Template-based rendering

Each profile can include Jinja2 templates in `templates/`. The exporter renders them with the extracted parameters.

```python
# simagents/profiles/exporter.py
def export_native(profile: SoftwareProfile, sections: dict, paper_name: str) -> dict[str, str]:
    """Render native param files from Jinja2 templates.
    Returns: {filename: content} dict
    """
```

Uses `jinja2` — add as an explicit dependency in `pyproject.toml` and `requirements.txt` (currently available transitively via FastAPI/Starlette, but should be direct to avoid breakage).

### Export ZIP contents

When user exports, the ZIP contains:
- JSON files (one per section) — always included
- Native param file(s) — included if templates exist for the profile
- `ic_notes.txt` — included if `ic_generator == "external"` and there are IC notes

### Fallback

If no template exists for a profile, export produces JSON only. This allows adding new software with just a `profile.yaml` + `docs/` and no template initially.

---

## 6. API Changes

### New endpoints

- **`GET /api/profiles`** — returns list of available profiles: `[{name, description, family, ic_generator}]`
- **`GET /api/profiles/{software}`** — returns full profile metadata (sections, units, parameter_names, ic_note)

### Modified endpoints

- **`GET /api/parameters/{id}`** — response changes from `{genic, gadget, status, missing, sources}` to `{sections, ic_notes, status, missing, sources}`
- **`PUT /api/parameters/{id}`** — request changes from `{genic?, gadget?}` to `{sections: {section_name: {param: value}}}`. The route iterates over provided sections and merges into the session's parameters.
- **`GET /api/parameters/{id}/export`** — ZIP now includes native param files when templates available
- **`POST /api/extract`** — loads `SoftwareProfile` via `load_profile(target_software)` and passes it to the graph via `configurable` dict alongside llm, retrievers, etc.

### SSE `parameters_update` event migration

The SSE event in `extract.py` changes from:

```python
# Old (hardcoded genic/gadget)
params = {"genic": fmt.get("genic", {}), "gadget": fmt.get("gadget", {}), ...}
```

To:

```python
# New (generic sections)
params = {
    "sections": fmt.get("sections", {}),
    "ic_notes": fmt.get("ic_notes", []),
    "status": data.get("status", "incomplete"),
    "missing": data.get("missing_parameters", []),
    "sources": fmt.get("sources", []),
}
```

The frontend `ParametersData` type updates accordingly — `genic`/`gadget` replaced by `sections: Record<string, Record<string, unknown>>`.

### Unchanged endpoints

- `POST /api/upload` — no change
- `GET/PUT /api/settings` — no change (target_software field still works)
- `POST /api/respond/{id}` — no change
- `GET /api/stream/{id}` — SSE events carry `sections` instead of `genic`/`gadget` in `parameters_update`
- `GET /api/session/status` — no change

---

## 7. Frontend Changes

### ParameterPanel.tsx

- **Dynamic tabs** — instead of hardcoded GenIC/Gadget/Sources, render tabs from the profile's `output.sections` + a Sources tab
- Tab names come from `GET /api/profiles/{software}` response
- When `ic_generator == "external"`, show an info banner with IC notes

### SettingsView.tsx

- Target software dropdown populated from `GET /api/profiles` instead of hardcoded list
- Shows profile description as helper text under the dropdown

### Export

- "Export" button downloads ZIP with native param files when available
- Tooltip shows what's in the ZIP: "JSON + Gadget-4 param.txt"

---

## 8. Migration from Current Structure

- `data/software_docs/mp-gadget/` → `data/software_profiles/mp-gadget/docs/`
- New `profile.yaml` added for MP-Gadget with 2 sections (genic + gadget)
- `ExtractionOutput.genic_parameters` / `gadget_parameters` → `ExtractionOutput.sections`
- `PathSettings.software_docs_dir` → `PathSettings.software_profiles_dir`
- Golden standard files stay as-is (MP-Gadget format, benchmarking only)
- Breaking change to output format — acceptable on a new branch

---

## 9. What Does NOT Change

- LangGraph topology (same nodes, same edges, same graph structure)
- Checkpointer / interrupt / resume flow
- Physics expert prompt structure (still extracts canonical physics, just with better generic queries)
- CLI interface (`main.py` still takes `--software`)
- GUI layout (sidebar, chat, parameter panel structure)
- Golden standard database
- Test infrastructure

---

## 10. File Changes Summary

| Action | File |
|--------|------|
| **New** | `simagents/profiles/__init__.py` |
| **New** | `simagents/profiles/loader.py` — load & validate profile.yaml |
| **New** | `simagents/profiles/exporter.py` — Jinja2 native param file rendering |
| **New** | `simagents/api/routes/profiles.py` — GET /api/profiles endpoints |
| **New** | `data/software_profiles/mp-gadget/profile.yaml` |
| **New** | `data/software_profiles/mp-gadget/templates/*.j2` |
| **New** | `data/software_profiles/gadget-4/` (profile + docs + templates) |
| **New** | `data/software_profiles/arepo/` (profile + docs + templates) |
| **New** | `data/software_profiles/gizmo/` (profile + docs + templates) |
| **New** | `data/software_profiles/swift/` (profile + docs + templates) |
| **Move** | `data/software_docs/mp-gadget/` → `data/software_profiles/mp-gadget/docs/` |
| **Modify** | `simagents/types.py` — sections replaces genic/gadget |
| **Modify** | `simagents/graph/state.py` — update state for sections |
| **Modify** | `simagents/nodes/physics_expert.py` — generic queries, family context |
| **Modify** | `simagents/nodes/formatter.py` — profile-driven, sections output |
| **Modify** | `simagents/nodes/save_output.py` — iterate sections |
| **Modify** | `simagents/prompts/physics_expert.md` — generic terminology |
| **Modify** | `simagents/prompts/formatter.md` — sections-based output format |
| **Modify** | `simagents/tools/docs_loader.py` — load from profiles dir |
| **Modify** | `simagents/config/settings.py` — software_profiles_dir |
| **Modify** | `simagents/api/routes/extract.py` — load & pass profile |
| **Modify** | `simagents/api/routes/parameters.py` — sections format, native export |
| **Modify** | `simagents/api/server.py` — include profiles router |
| **Modify** | `frontend/src/components/ParameterPanel.tsx` — dynamic tabs |
| **Modify** | `frontend/src/components/SettingsView.tsx` — populate from API |
| **Modify** | `frontend/src/lib/types.ts` — update ParametersData |
| **Modify** | `frontend/src/lib/api.ts` — add profiles endpoints |
| **Modify** | `main.py` — update for sections output |
| **Modify** | Tests — update for new format |
