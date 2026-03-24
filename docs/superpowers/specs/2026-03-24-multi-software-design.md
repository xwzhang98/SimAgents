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

`load_profile()` reads `profile.yaml`, validates it with Pydantic, and returns a `SoftwareProfile` object. `list_profiles()` scans all subdirectories for profiles.

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

`prompts/formatter.md` updated to use generic `sections` output:

```json
{
  "sections": {
    "<section_name>": {
      "<software_specific_param>": "value"
    }
  },
  "ic_notes": ["list of IC-relevant params when ic_generator is external"],
  "comment": "...",
  "sources": [...],
  "status": "complete|incomplete|needs_user_input",
  "missing_parameters": [],
  "user_questions": []
}
```

The profile's section names, parameter naming conventions, and unit conventions are injected into the prompt.

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

Replaces `genic_parameters` + `gadget_parameters`. The `ExtractionState` updates similarly — `formatted_parameters` becomes the sections-based structure.

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

Uses `jinja2` (already available as a transitive dependency).

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
- **`GET /api/parameters/{id}/export`** — ZIP now includes native param files when templates available
- **`POST /api/extract`** — passes loaded `SoftwareProfile` to the graph via `configurable` dict

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
