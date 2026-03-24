# Multi-Software Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend SimAgents to support Gadget-4, Arepo, GIZMO, and SWIFT via a software profile system, replacing the hardcoded MP-Gadget output format with profile-driven extraction and native param file export.

**Architecture:** Each software gets a profile folder (`profile.yaml` + `docs/` + `templates/`). The physics expert extracts canonical physics values, the formatter uses the profile to translate to software-specific naming and structure, and a Jinja2 exporter generates native param files.

**Tech Stack:** Existing LangGraph pipeline + Pydantic for profile validation + Jinja2 for native export

**Spec:** `docs/superpowers/specs/2026-03-24-multi-software-design.md`

---

## File Structure

### New files

```
simagents/profiles/
  __init__.py
  loader.py                          # SoftwareProfile dataclass, load_profile(), list_profiles()
  exporter.py                        # Jinja2 native param file rendering

simagents/api/routes/
  profiles.py                        # GET /api/profiles, GET /api/profiles/{software}

data/software_profiles/
  mp-gadget/
    profile.yaml
    templates/
      genic_params.txt.j2
      gadget_params.txt.j2
    docs/
      paramfile_reference.md         # moved from data/software_docs/mp-gadget/
      genic_reference.md             # moved from data/software_docs/mp-gadget/
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

tests/
  test_profiles/
    __init__.py
    test_loader.py
    test_exporter.py
```

### Modified files

```
simagents/types.py                   # sections replaces genic/gadget
simagents/graph/state.py             # same change
simagents/nodes/physics_expert.py    # generic queries, family hint
simagents/nodes/formatter.py         # profile-driven, sections output
simagents/nodes/save_output.py       # iterate sections from profile
simagents/prompts/physics_expert.md  # generic, family-aware
simagents/prompts/formatter.md       # profile-driven template
simagents/tools/docs_loader.py       # load from profiles dir
simagents/config/settings.py         # software_profiles_dir
simagents/api/routes/extract.py      # load & pass profile
simagents/api/routes/parameters.py   # sections format, native export
simagents/api/server.py              # include profiles router
frontend/src/lib/types.ts            # update ParametersData
frontend/src/lib/api.ts              # add profiles endpoints
frontend/src/components/ParameterPanel.tsx  # dynamic tabs
frontend/src/components/SettingsView.tsx    # populate from API
main.py                              # update for sections
pyproject.toml                       # add jinja2
tests/test_config.py                 # update defaults
tests/test_nodes/*                   # update for sections format
tests/test_graph/*                   # update for sections format
```

---

## Task 0: Branch & Dependencies

- [ ] **Step 1: Create branch**

```bash
git checkout -b feature/multi-software
```

- [ ] **Step 2: Add jinja2 to pyproject.toml**

Add `"jinja2>=3.1.0"` to the main `dependencies` list in `pyproject.toml`.

- [ ] **Step 3: Install**

```bash
conda run -n langgraph pip install -e ".[gui]"
```

- [ ] **Step 4: Commit**

```bash
git commit -am "chore: create multi-software branch, add jinja2 dependency"
```

---

## Task 1: Profile Loader

**Files:**
- Create: `simagents/profiles/__init__.py`
- Create: `simagents/profiles/loader.py`
- Create: `tests/test_profiles/__init__.py`
- Create: `tests/test_profiles/test_loader.py`

- [ ] **Step 1: Write tests**

Create: `tests/test_profiles/test_loader.py`

```python
"""Tests for software profile loader."""
import pytest
from pathlib import Path
from simagents.profiles.loader import SoftwareProfile, load_profile, list_profiles


PROFILES_DIR = str(Path(__file__).resolve().parents[2] / "data" / "software_profiles")


def test_load_profile_mp_gadget():
    profile = load_profile("mp-gadget", PROFILES_DIR)
    assert profile.slug == "mp-gadget"
    assert profile.name == "MP-Gadget"
    assert profile.family == "gadget"
    assert len(profile.output_sections) == 2  # genic + gadget
    assert profile.ic_generator == "builtin"
    assert "matter_density" in profile.parameter_names
    assert profile.parameter_names["matter_density"] == "Omega0"


def test_load_profile_swift():
    profile = load_profile("swift", PROFILES_DIR)
    assert profile.slug == "swift"
    assert profile.family == "swift"
    assert profile.units["length"] == "Mpc"
    assert profile.parameter_names["matter_density"] == "Omega_cdm"
    assert profile.ic_generator == "external"


def test_load_profile_not_found():
    with pytest.raises(FileNotFoundError):
        load_profile("nonexistent", PROFILES_DIR)


def test_list_profiles():
    profiles = list_profiles(PROFILES_DIR)
    assert len(profiles) >= 5
    slugs = [p["slug"] for p in profiles]
    assert "mp-gadget" in slugs
    assert "swift" in slugs
    assert "gadget-4" in slugs


def test_profile_has_docs_dir():
    profile = load_profile("mp-gadget", PROFILES_DIR)
    assert profile.docs_dir.exists()
    assert any(profile.docs_dir.glob("*.md"))
```

- [ ] **Step 2: Write loader.py**

Create: `simagents/profiles/loader.py`

```python
"""Software profile loader — reads profile.yaml and validates."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class OutputSection:
    name: str
    description: str
    filename_template: str
    native_template: str | None = None


@dataclass
class SoftwareProfile:
    slug: str
    name: str
    description: str
    family: str  # gadget | swift | enzo
    output_format: str  # key-value | yaml | ini
    output_sections: list[OutputSection]
    comment_prefix: str
    units: dict[str, str]
    ic_generator: str  # builtin | external | none
    ic_note: str
    parameter_names: dict[str, str]  # canonical → software-specific
    docs_dir: Path
    templates_dir: Path
    profile_dir: Path


def load_profile(software_name: str, profiles_dir: str = "data/software_profiles") -> SoftwareProfile:
    """Load and validate a software profile from its directory."""
    profile_path = Path(profiles_dir) / software_name
    yaml_path = profile_path / "profile.yaml"

    if not yaml_path.exists():
        raise FileNotFoundError(f"No profile found for '{software_name}' at {yaml_path}")

    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(f"Empty profile.yaml for '{software_name}'")

    docs_dir = profile_path / "docs"
    if not docs_dir.exists() or not any(docs_dir.glob("*.md")):
        raise FileNotFoundError(f"No docs found for '{software_name}' at {docs_dir}")

    output = data.get("output", {})
    sections = [
        OutputSection(
            name=s["name"],
            description=s.get("description", ""),
            filename_template=s.get("filename_template", f"{{paper}}_{s['name']}.json"),
            native_template=s.get("native_template"),
        )
        for s in output.get("sections", [])
    ]

    return SoftwareProfile(
        slug=software_name,
        name=data.get("name", software_name),
        description=data.get("description", ""),
        family=data.get("family", "unknown"),
        output_format=output.get("format", "key-value"),
        output_sections=sections,
        comment_prefix=output.get("comment_prefix", "#"),
        units=data.get("units", {}),
        ic_generator=data.get("ic_generator", "none"),
        ic_note=data.get("ic_note", ""),
        parameter_names=data.get("parameter_names", {}),
        docs_dir=docs_dir,
        templates_dir=profile_path / "templates",
        profile_dir=profile_path,
    )


def list_profiles(profiles_dir: str = "data/software_profiles") -> list[dict]:
    """List all available software profiles."""
    profiles = []
    base = Path(profiles_dir)
    if not base.exists():
        return profiles
    for d in sorted(base.iterdir()):
        if d.is_dir() and (d / "profile.yaml").exists():
            try:
                p = load_profile(d.name, profiles_dir)
                profiles.append({
                    "slug": p.slug,
                    "name": p.name,
                    "description": p.description,
                    "family": p.family,
                    "ic_generator": p.ic_generator,
                })
            except (FileNotFoundError, ValueError):
                pass
    return profiles
```

- [ ] **Step 3: Write __init__.py**

Create: `simagents/profiles/__init__.py`

```python
from .loader import SoftwareProfile, load_profile, list_profiles
__all__ = ["SoftwareProfile", "load_profile", "list_profiles"]
```

- [ ] **Step 4: Create all 5 profile.yaml files + docs + templates**

This is the big data step. Create the full `data/software_profiles/` tree with:
- `mp-gadget/profile.yaml` + move existing docs from `data/software_docs/mp-gadget/` + genic/gadget Jinja2 templates
- `gadget-4/profile.yaml` + docs + param template
- `arepo/profile.yaml` + docs + param template
- `gizmo/profile.yaml` + docs + param template
- `swift/profile.yaml` + docs + YAML template

Each `profile.yaml` follows the schema from the spec (Section 1). Reference docs should contain parameter names, descriptions, valid ranges, and unit conventions sourced from official documentation. Use the deep research results from the brainstorming session.

- [ ] **Step 5: Run tests, commit**

```bash
conda run -n langgraph pytest tests/test_profiles/ -v
git add simagents/profiles/ data/software_profiles/ tests/test_profiles/
git commit -m "feat: add software profile system with 5 profiles (mp-gadget, gadget-4, arepo, gizmo, swift)"
```

---

## Task 2: Profile Exporter (Jinja2)

**Files:**
- Create: `simagents/profiles/exporter.py`
- Create: `tests/test_profiles/test_exporter.py`

- [ ] **Step 1: Write tests**

Create: `tests/test_profiles/test_exporter.py`

```python
"""Tests for native param file exporter."""
from simagents.profiles.loader import load_profile
from simagents.profiles.exporter import export_native
from pathlib import Path

PROFILES_DIR = str(Path(__file__).resolve().parents[2] / "data" / "software_profiles")


def test_export_gadget4_native():
    profile = load_profile("gadget-4", PROFILES_DIR)
    sections = {"params": {"Omega0": 0.3089, "OmegaLambda": 0.6911, "HubbleParam": 0.6774, "BoxSize": 75000}}
    result = export_native(profile, sections, "test_paper")
    assert len(result) > 0
    # Should have at least one file
    filename, content = list(result.items())[0]
    assert "Omega0" in content
    assert "0.3089" in content


def test_export_swift_yaml():
    profile = load_profile("swift", PROFILES_DIR)
    sections = {"params": {"h": 0.6774, "Omega_cdm": 0.2589, "Omega_lambda": 0.6911, "Omega_b": 0.0486}}
    result = export_native(profile, sections, "test_paper")
    assert len(result) > 0
    filename, content = list(result.items())[0]
    assert "h:" in content or "Omega_cdm" in content


def test_export_no_template_returns_empty():
    """Profile with no templates dir returns empty dict."""
    profile = load_profile("mp-gadget", PROFILES_DIR)
    profile.templates_dir = Path("/nonexistent")
    result = export_native(profile, {"genic": {}}, "test")
    assert result == {}
```

- [ ] **Step 2: Write exporter.py**

Create: `simagents/profiles/exporter.py`

```python
"""Native param file export via Jinja2 templates."""
from __future__ import annotations
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from simagents.profiles.loader import SoftwareProfile


def export_native(profile: SoftwareProfile, sections: dict, paper_name: str) -> dict[str, str]:
    """Render native param files from Jinja2 templates.

    Returns: {filename: rendered_content} dict. Empty if no templates exist.
    """
    if not profile.templates_dir.exists():
        return {}

    env = Environment(
        loader=FileSystemLoader(str(profile.templates_dir)),
        keep_trailing_newline=True,
    )

    results = {}
    for section in profile.output_sections:
        if not section.native_template:
            continue
        template_path = profile.templates_dir / section.native_template
        if not template_path.exists():
            continue

        template = env.get_template(section.native_template)
        rendered = template.render(
            sections=sections,
            section=sections.get(section.name, {}),
            paper=paper_name,
            source=paper_name,
            profile=profile,
        )
        filename = section.filename_template.format(paper=paper_name)
        # Replace .json extension with native extension if template exists
        if filename.endswith(".json"):
            filename = filename[:-5] + (".yml" if profile.output_format == "yaml" else ".txt")
        results[filename] = rendered

    return results
```

- [ ] **Step 3: Update profiles/__init__.py**

Add: `from .exporter import export_native`

- [ ] **Step 4: Run tests, commit**

```bash
conda run -n langgraph pytest tests/test_profiles/ -v
git add simagents/profiles/ tests/test_profiles/
git commit -m "feat: add Jinja2 native param file exporter"
```

---

## Task 3: Update Types, State, and Config

**Files:**
- Modify: `simagents/types.py`
- Modify: `simagents/graph/state.py`
- Modify: `simagents/config/settings.py`

- [ ] **Step 1: Update types.py**

Replace `genic_parameters` + `gadget_parameters` with `sections`:

```python
class ExtractionOutput(TypedDict):
    """Output contract for the extraction graph."""
    sections: dict[str, dict]       # {"params": {...}} or {"genic": {...}, "gadget": {...}}
    ic_notes: list[str]             # IC-relevant params when ic_generator is external
    status: str                     # "complete" | "incomplete"
    missing: list[str]
    comment: str
    sources: list[dict]
```

- [ ] **Step 2: Update settings.py**

Change `PathSettings.software_docs_dir` to `software_profiles_dir`:

```python
class PathSettings(BaseModel):
    output_dir: str = "./output"
    software_profiles_dir: str = "./data/software_profiles"
```

- [ ] **Step 3: Update tests**

Update `tests/test_types.py` — change `genic_parameters`/`gadget_parameters` to `sections`/`ic_notes`. Update `tests/test_config.py` if it references `software_docs_dir`.

- [ ] **Step 4: Run tests, commit**

```bash
conda run -n langgraph pytest tests/test_types.py tests/test_config.py -v
git add simagents/types.py simagents/graph/state.py simagents/config/settings.py tests/
git commit -m "feat: update types and config for generic sections output"
```

---

## Task 4: Update Prompts

**Files:**
- Modify: `simagents/prompts/physics_expert.md`
- Modify: `simagents/prompts/formatter.md`

- [ ] **Step 1: Update physics_expert.md**

Make it truly generic — replace MP-Gadget specific references with canonical physics terminology. Add `{family_hint}` template variable.

- [ ] **Step 2: Rewrite formatter.md as a profile-driven template**

The formatter prompt becomes a template rendered by the formatter node with profile data. It should include:
- Software name and description from profile
- Output section names from profile
- Parameter naming reference table from `profile.parameter_names`
- Unit conventions from `profile.units`
- IC generator info from `profile.ic_generator` and `profile.ic_note`
- Generic sections-based JSON output format (not hardcoded genic/gadget)

Use the concrete example from the spec (Section 3, "Formatter prompt changes").

- [ ] **Step 3: Commit**

```bash
git add simagents/prompts/
git commit -m "feat: make prompts generic and profile-driven"
```

---

## Task 5: Update Nodes (Physics Expert, Formatter, Save Output)

**Files:**
- Modify: `simagents/nodes/physics_expert.py`
- Modify: `simagents/nodes/formatter.py`
- Modify: `simagents/nodes/save_output.py`
- Modify: `simagents/tools/docs_loader.py`
- Update: `tests/test_nodes/test_physics_expert.py`
- Update: `tests/test_nodes/test_formatter.py`
- Update: `tests/test_nodes/test_save_output.py`

- [ ] **Step 1: Update docs_loader.py**

Change `build_docs_retriever()` to accept `docs_dir` (Path from profile) instead of constructing the path from `software_docs_dir + target_software`:

```python
def build_docs_retriever(docs_dir: str | Path, rag_settings: RAGSettings):
    docs_path = Path(docs_dir)
    if not docs_path.exists() or not any(docs_path.glob("*.md")):
        raise FileNotFoundError(f"No docs found at {docs_path}")
    # ... rest stays the same
```

- [ ] **Step 2: Update physics_expert.py**

- Load `family` from profile in configurable
- Inject family hint into prompt context
- Keep search queries generic (already mostly generic from previous fix)

- [ ] **Step 3: Update formatter.py**

This is the biggest change:
- Load `SoftwareProfile` from `configurable["profile"]`
- Render the formatter prompt using profile data (section names, parameter_names, units, ic_generator info)
- Compute `ic_notes` deterministically when `profile.ic_generator == "external"`
- Update fallback JSON to use `sections` instead of `genic`/`gadget`

- [ ] **Step 4: Update save_output.py**

- Load profile from configurable
- Iterate over `profile.output_sections` instead of hardcoded genic/gadget
- Use `section.filename_template.format(paper=paper_name)` for filenames

- [ ] **Step 5: Update all node tests**

Update mocked LLM responses and assertions to use `sections` format instead of `genic`/`gadget`.

- [ ] **Step 6: Run tests, commit**

```bash
conda run -n langgraph pytest tests/test_nodes/ tests/test_tools/ -v
git add simagents/nodes/ simagents/tools/ tests/
git commit -m "feat: make nodes profile-driven with generic sections output"
```

---

## Task 6: Update Graph & Extract Route

**Files:**
- Modify: `simagents/api/routes/extract.py`
- Modify: `simagents/graph/parameter_extraction.py` (if needed)
- Update: `tests/test_graph/test_parameter_extraction.py`

- [ ] **Step 1: Update extract.py**

- Import and call `load_profile(target_software, settings.paths.software_profiles_dir)`
- Pass `profile` to the `configurable` dict alongside llm, retrievers, etc.
- Use `profile.docs_dir` to build docs retriever: `build_docs_retriever(profile.docs_dir, settings.rag)`
- Update `_stream_events` to read `sections` from formatter output instead of `genic`/`gadget`

- [ ] **Step 2: Update graph integration test**

Update `test_graph_paper_mode_complete` mock LLM response to return `sections` format.

- [ ] **Step 3: Run tests, commit**

```bash
conda run -n langgraph pytest tests/ -v
git add simagents/api/routes/extract.py tests/test_graph/
git commit -m "feat: pass software profile through extraction pipeline"
```

---

## Task 7: API — Profiles Endpoint & Parameters Migration

**Files:**
- Create: `simagents/api/routes/profiles.py`
- Modify: `simagents/api/routes/parameters.py`
- Modify: `simagents/api/server.py`

- [ ] **Step 1: Create profiles route**

Create: `simagents/api/routes/profiles.py`

```python
"""Profiles routes — list and get software profiles."""
from __future__ import annotations
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from simagents.profiles.loader import load_profile, list_profiles

router = APIRouter()
PROFILES_DIR = os.environ.get("SIMAGENTS_PROFILES", str(Path(__file__).resolve().parents[3] / "data" / "software_profiles"))


@router.get("/api/profiles")
async def get_profiles():
    return list_profiles(PROFILES_DIR)


@router.get("/api/profiles/{software}")
async def get_profile(software: str):
    try:
        p = load_profile(software, PROFILES_DIR)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "slug": p.slug,
        "name": p.name,
        "description": p.description,
        "family": p.family,
        "output_format": p.output_format,
        "sections": [{"name": s.name, "description": s.description} for s in p.output_sections],
        "units": p.units,
        "ic_generator": p.ic_generator,
        "ic_note": p.ic_note,
        "parameter_names": p.parameter_names,
    }
```

- [ ] **Step 2: Update parameters.py**

Change `genic`/`gadget` to `sections` in GET/PUT/export endpoints. Add native param files to the export ZIP.

- [ ] **Step 3: Update server.py**

Add: `from simagents.api.routes import profiles` and `app.include_router(profiles.router)`

- [ ] **Step 4: Run tests, commit**

```bash
conda run -n langgraph pytest tests/ -v
git add simagents/api/ tests/
git commit -m "feat: add profiles API, update parameters for sections format"
```

---

## Task 8: Update Frontend

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/components/ParameterPanel.tsx`
- Modify: `frontend/src/components/SettingsView.tsx`
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Update types.ts**

```typescript
// Replace genic/gadget with sections
export interface ParametersData {
  sections: Record<string, Record<string, unknown>>;
  ic_notes: string[];
  status: string;
  missing: string[];
  sources: Array<{ param: string; value: unknown; location: string; page: number }>;
}

// Add profile types
export interface ProfileInfo {
  slug: string;
  name: string;
  description: string;
  family: string;
  ic_generator: string;
}

export interface ProfileDetail extends ProfileInfo {
  output_format: string;
  sections: Array<{ name: string; description: string }>;
  units: Record<string, string>;
  ic_note: string;
  parameter_names: Record<string, string>;
}
```

- [ ] **Step 2: Update api.ts**

Add `getProfiles()` and `getProfile(software)` functions.

- [ ] **Step 3: Update ParameterPanel.tsx**

- Fetch profile detail on mount (or receive as prop)
- Render tabs dynamically from `profile.sections` + "Sources" tab
- Show IC notes banner when `ic_generator === "external"` and `ic_notes.length > 0`
- Update parameter display to read from `parameters.sections[currentTab]`

- [ ] **Step 4: Update SettingsView.tsx**

- Fetch profiles list from `GET /api/profiles`
- Populate target software dropdown from profiles list instead of hardcoded options
- Show profile description as helper text

- [ ] **Step 5: Update page.tsx**

- Update SSE `parameters_update` handler to read `sections` from event data
- Pass profile info to ParameterPanel

- [ ] **Step 6: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: dynamic profile-driven parameter tabs, populate software dropdown from API"
```

---

## Task 9: Update CLI & Cleanup

**Files:**
- Modify: `main.py`
- Remove: `data/software_docs/` (replaced by `data/software_profiles/`)
- Update: `.gitignore` if needed

- [ ] **Step 1: Update main.py**

- Import and use `load_profile()`
- Pass profile to configurable
- Use `profile.docs_dir` for docs retriever
- Update output display for sections format

- [ ] **Step 2: Remove old software_docs**

```bash
rm -rf data/software_docs/
```

- [ ] **Step 3: Run full test suite**

```bash
conda run -n langgraph pytest tests/ -v
cd frontend && npm run build
```

- [ ] **Step 4: Commit and push**

```bash
git add -A
git commit -m "feat: update CLI for multi-software, remove old software_docs"
git push -u origin feature/multi-software
```
