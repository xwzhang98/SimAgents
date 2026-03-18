# SimAgents LangGraph Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite SimAgents from ag2/AutoGen + OpenAI Assistants to LangGraph + LangChain with model-agnostic design, on a new `feature/langgraph-rewrite` branch.

**Architecture:** LangGraph StateGraph with two-node extraction loop (physics_expert → formatter → check_done), local Chroma RAG replacing OpenAI Assistants, configurable LLM via `init_chat_model()`, externalized markdown prompts, and Pydantic config merging YAML + env vars.

**Tech Stack:** LangGraph, LangChain, Chroma, Pydantic, Python 3.11+

**Spec:** `docs/superpowers/specs/2026-03-18-langgraph-rewrite-design.md`

---

## File Structure

```
simagents/
├── __init__.py                      # Package exports: create_extraction_graph, types
├── types.py                         # ExtractionInput, ExtractionOutput TypedDicts
├── config/
│   ├── __init__.py                  # Re-exports Settings
│   └── settings.py                  # Pydantic BaseSettings (LLM, RAG, extraction, paths, SLURM)
├── tools/
│   ├── __init__.py                  # Re-exports loader functions
│   ├── pdf_loader.py                # get_pdf_loader() factory, build_paper_retriever()
│   └── docs_loader.py               # build_docs_retriever() for software docs
├── prompts/
│   ├── physics_expert.md            # Template with {target_software}, {input_context}, {custom_prompt}
│   └── formatter.md                 # Template with {target_software}, {raw_parameters}
├── nodes/
│   ├── __init__.py                  # Re-exports all node functions
│   ├── parse_input.py               # parse_input() — detect paper/chat/hybrid mode
│   ├── physics_expert.py            # physics_expert() — RAG extract params from paper
│   ├── formatter.py                 # formatter() — RAG validate against software docs
│   ├── check_done.py                # check_done() — routing: done/loop/needs_user_input
│   ├── ask_user.py                  # ask_user() — LangGraph interrupt() for human-in-the-loop
│   └── save_output.py               # save_output() — write JSON config files
├── graph/
│   ├── __init__.py                  # Re-exports create_extraction_graph
│   ├── state.py                     # ExtractionState TypedDict
│   └── parameter_extraction.py      # StateGraph construction, create_extraction_graph()
├── visualization/
│   ├── __init__.py
│   ├── power_spectrum.py            # PowerSpectrumPlotter (standalone, model-agnostic)
│   └── density_field.py             # DensityFieldPlotter (standalone, model-agnostic)
└── utils/
    ├── __init__.py
    ├── file_utils.py                # Port from existing, remove hardcoded paths
    └── slurm_utils.py               # Port from existing, use config instead of hardcoded defaults

tests/
├── __init__.py
├── test_config.py                   # Config loading, validation, defaults
├── test_types.py                    # Type contracts
├── test_tools/
│   ├── __init__.py
│   ├── test_pdf_loader.py           # PDF loader factory, chunking
│   └── test_docs_loader.py          # Docs loader, retriever creation
├── test_nodes/
│   ├── __init__.py
│   ├── test_parse_input.py          # Input mode detection
│   ├── test_physics_expert.py       # Physics expert with mocked LLM
│   ├── test_formatter.py            # Formatter with mocked LLM
│   ├── test_check_done.py           # Routing logic
│   ├── test_save_output.py          # File writing
│   ├── test_ask_user.py             # Human-in-the-loop interrupt
│   └── test_extract_json.py         # JSON extraction helper
└── test_graph/
    ├── __init__.py
    └── test_parameter_extraction.py  # Full graph with mocked LLM

data/
├── software_docs/
│   └── mp-gadget/
│       ├── paramfile_reference.md   # MP-Gadget parameter file reference
│       └── genic_reference.md       # MP-Gadget GenIC reference
└── gaepsi2_demo.py                  # Carried over from main branch

pyproject.toml                       # Package definition
config.example.yaml                  # Template config
.env.example                         # API key template
main.py                              # CLI entry point
```

---

## Task 0: Environment & Branch Setup

**Files:**
- Create: conda environment `langgraph`
- Create: git branch `feature/langgraph-rewrite`

- [ ] **Step 1: Create conda environment**

```bash
conda create -n langgraph python=3.11 -y
conda activate langgraph
```

- [ ] **Step 2: Create and switch to new branch**

```bash
git checkout -b feature/langgraph-rewrite
```

- [ ] **Step 3: Delete old code on the new branch**

Remove the ag2-specific code and baselines:

```bash
rm -rf baseline/
rm -rf agents/
rm -rf workflows/
rm -rf configs/
```

- [ ] **Step 4: Create new directory structure**

```bash
mkdir -p simagents/{config,tools,prompts,nodes,graph,visualization,utils}
mkdir -p tests/{test_tools,test_nodes,test_graph}
mkdir -p data/software_docs/mp-gadget
```

- [ ] **Step 5: Create all `__init__.py` files**

```bash
touch simagents/__init__.py
touch simagents/{config,tools,prompts,nodes,graph,visualization,utils}/__init__.py
touch tests/__init__.py
touch tests/{test_tools,test_nodes,test_graph}/__init__.py
```

- [ ] **Step 6: Create pyproject.toml so `simagents` is importable**

Create: `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[project]
name = "simagents"
version = "0.1.0"
description = "Multi-agent parameter extraction for cosmological simulations"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.3.0",
    "langchain>=0.3.0",
    "langchain-core>=0.3.0",
    "langchain-community>=0.3.0",
    "langchain-chroma>=0.2.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0",
    "numpy>=1.21.0",
    "matplotlib>=3.5.0",
    "scipy>=1.9.0",
]

[project.optional-dependencies]
unstructured = ["unstructured>=0.10.0"]
openai = ["langchain-openai>=0.2.0"]
anthropic = ["langchain-anthropic>=0.2.0"]
google = ["langchain-google-genai>=2.0.0"]
ollama = ["langchain-ollama>=0.2.0"]
dev = ["pytest>=7.0.0", "pytest-cov>=4.0.0", "ruff>=0.1.0", "mypy>=1.0.0"]

[tool.setuptools.packages.find]
include = ["simagents*"]
```

- [ ] **Step 7: Install the package in dev mode**

```bash
pip install -e ".[dev,openai,unstructured]"
```

Note: `unstructured` is a heavy dependency (requires system packages like poppler/tesseract on some platforms). If installation fails, install without it and use `pypdf` as the PDF loader instead:

```bash
pip install -e ".[dev,openai]"
pip install pypdf
# Then set rag.pdf_loader: "pypdf" in config.yaml
```

- [ ] **Step 7: Write requirements.txt**

Create: `requirements.txt`

```
# Core
langgraph>=0.3.0
langchain>=0.3.0
langchain-core>=0.3.0
langchain-community>=0.3.0

# RAG
chromadb>=0.4.0
unstructured>=0.10.0

# Config
pydantic>=2.0.0
pydantic-settings>=2.0.0
pyyaml>=6.0
python-dotenv>=1.0.0

# Scientific
numpy>=1.21.0
matplotlib>=3.5.0
scipy>=1.9.0

# LLM providers (install the one you need)
# langchain-openai>=0.2.0
# langchain-anthropic>=0.2.0
# langchain-google-genai>=2.0.0
# langchain-ollama>=0.2.0

# Optional PDF loaders
# pymupdf>=1.24.0
# docling>=2.0.0

# Optional vector stores
# faiss-cpu>=1.7.0

# Optional visualization
# langchain-experimental>=0.3.0
# gaepsi2
# bigfile

# Dev
pytest>=7.0.0
pytest-cov>=4.0.0
ruff>=0.1.0
mypy>=1.0.0
```

- [ ] **Step 8: Create .env.example**

Create: `.env.example`

```
# SimAgents API Keys
# Copy this to .env and fill in your keys.
# Only the provider you use needs a key.

OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
```

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "chore: scaffold langgraph rewrite — clean branch, new directory structure"
```

Note: `data/gaepsi2_demo.py` is carried over from main branch unchanged (it's in `data/` which was not deleted). Other software doc directories (`arepo/`, `gadget-4/`, `enzo/`) are deferred — adding new software support is done by adding a docs folder to `data/software_docs/`.

---

## Task 1: Types & Config System

**Files:**
- Create: `simagents/types.py`
- Create: `simagents/config/settings.py`
- Create: `simagents/config/__init__.py`
- Create: `config.example.yaml`
- Create: `tests/test_types.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests for types**

Create: `tests/test_types.py`

```python
"""Tests for ExtractionInput and ExtractionOutput type contracts."""
from simagents.types import ExtractionInput, ExtractionOutput


def test_extraction_input_paper_mode():
    """ExtractionInput accepts paper_path with no user_parameters."""
    inp: ExtractionInput = {
        "paper_path": "/path/to/paper.pdf",
        "user_parameters": None,
        "target_software": "mp-gadget",
        "custom_prompt": None,
    }
    assert inp["paper_path"] == "/path/to/paper.pdf"
    assert inp["target_software"] == "mp-gadget"


def test_extraction_input_chat_mode():
    """ExtractionInput accepts user_parameters with no paper_path."""
    inp: ExtractionInput = {
        "paper_path": None,
        "user_parameters": {"BoxSize": 100000, "Omega0": 0.3},
        "target_software": "mp-gadget",
        "custom_prompt": "Use these exact values",
    }
    assert inp["user_parameters"]["BoxSize"] == 100000


def test_extraction_output_complete():
    """ExtractionOutput with complete status."""
    out: ExtractionOutput = {
        "genic_parameters": {"BoxSize": 100000},
        "gadget_parameters": {"Omega0": 0.3},
        "status": "complete",
        "missing": [],
        "comment": "All parameters found.",
        "sources": [{"param": "BoxSize", "value": 100000, "location": "Section 3", "page": 5}],
    }
    assert out["status"] == "complete"
    assert len(out["missing"]) == 0


def test_extraction_output_incomplete():
    """ExtractionOutput with incomplete status has missing list."""
    out: ExtractionOutput = {
        "genic_parameters": {"BoxSize": 100000},
        "gadget_parameters": {},
        "status": "incomplete",
        "missing": ["Omega0", "HubbleParam"],
        "comment": "Could not find all parameters.",
        "sources": [],
    }
    assert out["status"] == "incomplete"
    assert "Omega0" in out["missing"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/zhangxiaowen/AntigravityProjects/SimAgents && conda run -n langgraph pytest tests/test_types.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'simagents'`

- [ ] **Step 3: Write types.py**

Create: `simagents/types.py`

```python
"""Public input/output contracts for the SimAgents extraction graph."""
from __future__ import annotations

from typing import TypedDict


class ExtractionInput(TypedDict, total=False):
    """Input contract for the extraction graph.

    Provide paper_path, user_parameters, or both (hybrid mode).
    """
    paper_path: str | None
    user_parameters: dict | None
    target_software: str
    custom_prompt: str | None


class ExtractionOutput(TypedDict):
    """Output contract for the extraction graph."""
    genic_parameters: dict
    gadget_parameters: dict
    status: str  # "complete" | "incomplete"
    missing: list[str]
    comment: str
    sources: list[dict]  # [{param, value, location, page}]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/zhangxiaowen/AntigravityProjects/SimAgents && conda run -n langgraph pytest tests/test_types.py -v`
Expected: PASS

- [ ] **Step 5: Write failing tests for config**

Create: `tests/test_config.py`

```python
"""Tests for the configuration system."""
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from simagents.config.settings import Settings, LLMSettings, RAGSettings, ExtractionSettings


def test_default_settings():
    """Settings have sensible defaults."""
    settings = Settings()
    assert settings.llm.provider == "openai"
    assert settings.llm.model == "gpt-4o"
    assert settings.llm.temperature == 0.01
    assert settings.rag.vector_store == "chroma"
    assert settings.rag.pdf_loader == "unstructured"
    assert settings.rag.chunk_size == 1000
    assert settings.extraction.max_iterations == 2
    assert settings.extraction.target_software == "mp-gadget"


def test_settings_from_yaml():
    """Settings can be loaded from a YAML file."""
    yaml_content = {
        "llm": {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "temperature": 0.1},
        "rag": {"vector_store": "faiss", "chunk_size": 500},
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(yaml_content, f)
        yaml_path = f.name

    try:
        settings = Settings.from_yaml(yaml_path)
        assert settings.llm.provider == "anthropic"
        assert settings.llm.model == "claude-sonnet-4-20250514"
        assert settings.rag.vector_store == "faiss"
        assert settings.rag.chunk_size == 500
        # Defaults still apply for unset fields
        assert settings.rag.chunk_overlap == 200
    finally:
        os.unlink(yaml_path)


def test_settings_env_vars_for_api_keys(monkeypatch):
    """API keys come from environment variables."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-456")
    settings = Settings()
    assert settings.openai_api_key == "sk-test-123"
    assert settings.anthropic_api_key == "sk-ant-test-456"


def test_settings_missing_yaml_uses_defaults():
    """Missing YAML file uses all defaults without error."""
    settings = Settings.from_yaml("/nonexistent/path.yaml")
    assert settings.llm.provider == "openai"


def test_llm_settings_validation():
    """LLMSettings validates temperature range."""
    with pytest.raises(ValueError):
        LLMSettings(provider="openai", model="gpt-4o", temperature=3.0)
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `conda run -n langgraph pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 7: Write settings.py**

Create: `simagents/config/settings.py`

```python
"""Configuration system: Pydantic BaseSettings merging YAML + environment variables."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class LLMSettings(BaseModel):
    """LLM provider configuration."""
    provider: str = "openai"
    model: str = "gpt-4o"
    temperature: float = 0.01

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0.0 <= v <= 2.0:
            raise ValueError(f"temperature must be between 0.0 and 2.0, got {v}")
        return v


class RAGSettings(BaseModel):
    """RAG pipeline configuration."""
    pdf_loader: str = "unstructured"
    vector_store: str = "chroma"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"


class ExtractionSettings(BaseModel):
    """Parameter extraction configuration."""
    max_iterations: int = 2
    target_software: str = "mp-gadget"


class PathSettings(BaseModel):
    """Path configuration."""
    output_dir: str = "./output"
    software_docs_dir: str = "./data/software_docs"


class SLURMSettings(BaseModel):
    """Optional SLURM configuration for HPC users."""
    partition: str = "RM"
    nodes: int = 1
    ntasks: int = 2
    cpus_per_task: int = 14
    time: str = "16:00:00"
    mem_per_cpu: str = "8G"


class Settings(BaseSettings):
    """Top-level settings merging YAML config + environment variables."""
    llm: LLMSettings = Field(default_factory=LLMSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    extraction: ExtractionSettings = Field(default_factory=ExtractionSettings)
    paths: PathSettings = Field(default_factory=PathSettings)
    slurm: Optional[SLURMSettings] = None

    # API keys from environment variables
    openai_api_key: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = Field(default=None, validation_alias="GOOGLE_API_KEY")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "Settings":
        """Load settings from a YAML file, falling back to defaults for missing values."""
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            return cls()

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f) or {}

        return cls(**data)
```

- [ ] **Step 8: Write config/__init__.py**

Create: `simagents/config/__init__.py`

```python
"""Configuration package."""
from .settings import Settings, LLMSettings, RAGSettings, ExtractionSettings, PathSettings, SLURMSettings

__all__ = ["Settings", "LLMSettings", "RAGSettings", "ExtractionSettings", "PathSettings", "SLURMSettings"]
```

- [ ] **Step 9: Write config.example.yaml**

Create: `config.example.yaml`

```yaml
# SimAgents Configuration
# Copy this file to config.yaml and edit as needed.

llm:
  provider: "openai"              # "openai" | "anthropic" | "google" | "ollama"
  model: "gpt-4o"                 # Model name for your provider
  temperature: 0.01               # Low temperature for reproducibility

rag:
  pdf_loader: "unstructured"      # "unstructured" | "pymupdf" | "pypdf" | "docling"
  vector_store: "chroma"          # "chroma" | "faiss"
  chunk_size: 1000
  chunk_overlap: 200
  embedding_provider: "openai"    # "openai" | "huggingface"
  embedding_model: "text-embedding-3-small"

extraction:
  max_iterations: 2
  target_software: "mp-gadget"    # "mp-gadget" | "arepo" | "gadget-4" | "enzo"

paths:
  output_dir: "./output"
  software_docs_dir: "./data/software_docs"

# Optional: SLURM settings for HPC users
# slurm:
#   partition: "RM"
#   nodes: 1
#   time: "16:00:00"
```

- [ ] **Step 10: Run tests to verify they pass**

Run: `conda run -n langgraph pytest tests/test_config.py tests/test_types.py -v`
Expected: ALL PASS

- [ ] **Step 11: Commit**

```bash
git add simagents/types.py simagents/config/ tests/test_types.py tests/test_config.py config.example.yaml
git commit -m "feat: add types and config system with YAML + env var merging"
```

---

## Task 2: RAG Tools Layer (PDF Loader + Docs Loader)

**Files:**
- Create: `simagents/tools/pdf_loader.py`
- Create: `simagents/tools/docs_loader.py`
- Create: `simagents/tools/__init__.py`
- Create: `tests/test_tools/test_pdf_loader.py`
- Create: `tests/test_tools/test_docs_loader.py`
- Create: `data/software_docs/mp-gadget/paramfile_reference.md`
- Create: `data/software_docs/mp-gadget/genic_reference.md`

- [ ] **Step 1: Write MP-Gadget reference docs**

These are the source docs the formatter agent will RAG search. Port the domain knowledge from the current hardcoded prompts and any existing MP-Gadget documentation.

Create: `data/software_docs/mp-gadget/paramfile_reference.md`

```markdown
# MP-Gadget Parameter File Reference

## Required Gadget Parameters

### Cosmological Parameters
- **Omega0**: Matter density parameter (Omega_m). Required. Range: 0.0–1.0.
- **OmegaLambda**: Dark energy density parameter. Required. Range: 0.0–1.0.
- **OmegaBaryon**: Baryon density parameter. Required for hydrodynamic runs.
- **HubbleParam**: Hubble parameter h (H0 = 100*h km/s/Mpc). Required. Typical: 0.67–0.72.
- **CMBTemperature**: CMB temperature in Kelvin. Default: 2.7255.

### Simulation Box
- **BoxSize**: Simulation box side length in kpc/h. Required. Note: papers often quote in Mpc/h — multiply by 1000.
- **TimeMax**: Scale factor at end of simulation. Required. Typical: 1.0 (z=0).

### Input/Output
- **InitCondFile**: Path to initial conditions file. Required.
- **OutputDir**: Directory for simulation output. Required.
- **OutputList**: Comma-separated list of scale factors for snapshot output. Required.

### Time Integration
- **MaxSizeTimestep**: Maximum timestep. Default: 0.1.
- **MinSizeTimestep**: Minimum timestep. Default: 0.0.

### Force Accuracy
- **ErrTolForceAcc**: Force accuracy parameter. Default: 0.005.
- **TreeDomainUpdateFrequency**: How often to update domain decomposition. Default: 0.025.

### Memory
- **PartAllocFactor**: Memory allocation factor. Default: 1.5.
- **BufferSize**: Communication buffer in MB. Default: 100.

### Gravity
- **Asmth**: Force softening scale in mesh cells. Default: 1.25.
- **Nmesh**: PM grid size. Must match or exceed particle grid.

## Unit Conventions
- Length: kpc/h (internal) — convert from Mpc/h by multiplying by 1000
- Mass: 10^10 M_sun/h
- Velocity: km/s
```

Create: `data/software_docs/mp-gadget/genic_reference.md`

```markdown
# MP-Gadget GenIC (Initial Conditions) Reference

## Required GenIC Parameters

### Output
- **OutputDir**: Directory to write IC files. Required.
- **FileBase**: Base name for IC files. Required. Default: "IC".

### Box & Resolution
- **BoxSize**: Box side length in kpc/h. Required. Must match Gadget BoxSize.
- **Ngrid**: Number of grid cells per dimension for particle grid. Required. Total particles = Ngrid^3.
- **Nmesh**: FFT mesh size for IC generation. Required. Usually = Ngrid or 2*Ngrid.

### Cosmology
- **Omega0**: Total matter density. Required.
- **OmegaLambda**: Dark energy density. Required.
- **OmegaBaryon**: Baryon density. Required for hydro runs.
- **HubbleParam**: Hubble parameter h. Required.
- **Sigma8**: Power spectrum normalization sigma_8. Required if using power spectrum.
- **PrimordialIndex**: Scalar spectral index n_s. Default: 0.96.

### Initial Redshift
- **Redshift**: Starting redshift for the simulation. Required. Typical: 49–199.

### Power Spectrum
- **FileWithInputSpectrum**: Path to input power spectrum file. Optional — if not provided, uses internal CAMB.
- **FileWithTransferFunction**: Path to transfer function file. Optional.
- **WhichSpectrum**: Power spectrum type. 1 = read from file, 2 = Eisenstein & Hu.

### Particle Types
- **ProduceGas**: Whether to include gas particles. 0 = DM only, 1 = DM + gas.
- **RadiationOn**: Include radiation. Default: 0.

### Random Seed
- **Seed**: Random seed for IC generation. Required for reproducibility.
```

- [ ] **Step 2: Write failing tests for pdf_loader**

Create: `tests/test_tools/test_pdf_loader.py`

```python
"""Tests for PDF loading and retriever construction."""
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from simagents.tools.pdf_loader import get_pdf_loader, build_paper_retriever
from simagents.config.settings import RAGSettings


def test_get_pdf_loader_unstructured():
    """get_pdf_loader returns an Unstructured loader by default."""
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        loader = get_pdf_loader(f.name, "unstructured")
        assert loader is not None


def test_get_pdf_loader_pypdf():
    """get_pdf_loader returns a PyPDF loader."""
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        loader = get_pdf_loader(f.name, "pypdf")
        assert loader is not None


def test_get_pdf_loader_invalid_raises():
    """get_pdf_loader raises ValueError for unknown loader type."""
    with pytest.raises(ValueError, match="Unknown PDF loader"):
        get_pdf_loader("/fake.pdf", "nonexistent_loader")


def test_build_paper_retriever_returns_retriever():
    """build_paper_retriever returns a VectorStoreRetriever."""
    # Mock the actual PDF loading and embedding since we don't want API calls in unit tests
    mock_docs = [MagicMock(page_content="BoxSize is 100 Mpc/h", metadata={"page": 1})]

    with patch("simagents.tools.pdf_loader.get_pdf_loader") as mock_loader_fn:
        mock_loader = MagicMock()
        mock_loader.load.return_value = mock_docs
        mock_loader_fn.return_value = mock_loader

        with patch("simagents.tools.pdf_loader._get_text_splitter") as mock_splitter_fn:
            mock_splitter = MagicMock()
            mock_splitter.split_documents.return_value = mock_docs
            mock_splitter_fn.return_value = mock_splitter

            with patch("simagents.tools.pdf_loader._build_vector_store") as mock_vs:
                mock_retriever = MagicMock()
                mock_vs.return_value.as_retriever.return_value = mock_retriever

                rag_settings = RAGSettings()
                retriever = build_paper_retriever("/fake/paper.pdf", rag_settings)
                assert retriever == mock_retriever
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `conda run -n langgraph pytest tests/test_tools/test_pdf_loader.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Write pdf_loader.py**

Create: `simagents/tools/pdf_loader.py`

```python
"""Configurable PDF loading, chunking, and retriever construction."""
from __future__ import annotations

from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from simagents.config.settings import RAGSettings


def get_pdf_loader(path: str, loader_type: str):
    """Factory for PDF document loaders.

    Args:
        path: Path to the PDF file.
        loader_type: One of "unstructured", "pymupdf", "pypdf", "docling".

    Returns:
        A LangChain document loader instance.

    Raises:
        ValueError: If loader_type is not recognized.
    """
    if loader_type == "unstructured":
        from langchain_unstructured import UnstructuredLoader
        return UnstructuredLoader(path)
    elif loader_type == "pymupdf":
        from langchain_community.document_loaders import PyMuPDFLoader
        return PyMuPDFLoader(path)
    elif loader_type == "pypdf":
        from langchain_community.document_loaders import PyPDFLoader
        return PyPDFLoader(path)
    elif loader_type == "docling":
        from langchain_docling import DoclingLoader
        return DoclingLoader(path)
    else:
        raise ValueError(
            f"Unknown PDF loader: '{loader_type}'. "
            f"Supported: unstructured, pymupdf, pypdf, docling"
        )


def _get_text_splitter(rag_settings: RAGSettings) -> RecursiveCharacterTextSplitter:
    """Create a text splitter from RAG settings."""
    return RecursiveCharacterTextSplitter(
        chunk_size=rag_settings.chunk_size,
        chunk_overlap=rag_settings.chunk_overlap,
    )


def _get_embeddings(rag_settings: RAGSettings):
    """Create embeddings model from RAG settings."""
    if rag_settings.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model=rag_settings.embedding_model)
    elif rag_settings.embedding_provider == "huggingface":
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=rag_settings.embedding_model)
    else:
        raise ValueError(
            f"Unknown embedding provider: '{rag_settings.embedding_provider}'. "
            f"Supported: openai, huggingface"
        )


def _build_vector_store(documents, embeddings, store_type: str):
    """Create a vector store from documents and embeddings."""
    if store_type == "chroma":
        from langchain_chroma import Chroma
        return Chroma.from_documents(documents, embeddings)
    elif store_type == "faiss":
        from langchain_community.vectorstores import FAISS
        return FAISS.from_documents(documents, embeddings)
    else:
        raise ValueError(
            f"Unknown vector store: '{store_type}'. Supported: chroma, faiss"
        )


def build_paper_retriever(paper_path: str, rag_settings: RAGSettings):
    """Build a VectorStoreRetriever from a PDF paper.

    Args:
        paper_path: Path to the PDF file.
        rag_settings: RAG configuration.

    Returns:
        A VectorStoreRetriever for searching the paper.

    Raises:
        FileNotFoundError: If paper_path does not exist.
        RuntimeError: If PDF loading or embedding fails.
    """
    path = Path(paper_path)
    if not path.exists():
        raise FileNotFoundError(f"Paper not found: {paper_path}")

    try:
        loader = get_pdf_loader(str(path), rag_settings.pdf_loader)
        documents = loader.load()
    except Exception as e:
        raise RuntimeError(
            f"Failed to load PDF with '{rag_settings.pdf_loader}' loader: {e}. "
            f"Try a different loader via config.yaml (rag.pdf_loader)."
        ) from e

    splitter = _get_text_splitter(rag_settings)
    chunks = splitter.split_documents(documents)

    embeddings = _get_embeddings(rag_settings)
    vector_store = _build_vector_store(chunks, embeddings, rag_settings.vector_store)
    return vector_store.as_retriever()
```

- [ ] **Step 5: Write failing tests for docs_loader**

Create: `tests/test_tools/test_docs_loader.py`

```python
"""Tests for software docs loading and retriever construction."""
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from simagents.tools.docs_loader import build_docs_retriever
from simagents.config.settings import RAGSettings


def test_build_docs_retriever_loads_markdown_files(tmp_path):
    """build_docs_retriever loads all .md files from the software docs directory."""
    docs_dir = tmp_path / "software_docs" / "mp-gadget"
    docs_dir.mkdir(parents=True)
    (docs_dir / "param_ref.md").write_text("# Params\nBoxSize: kpc/h")
    (docs_dir / "genic_ref.md").write_text("# GenIC\nNgrid: particle count")

    with patch("simagents.tools.docs_loader._get_embeddings") as mock_emb:
        with patch("simagents.tools.docs_loader._build_vector_store") as mock_vs:
            mock_retriever = MagicMock()
            mock_vs.return_value.as_retriever.return_value = mock_retriever

            rag_settings = RAGSettings()
            retriever = build_docs_retriever(
                "mp-gadget", rag_settings, software_docs_dir=str(tmp_path / "software_docs")
            )
            assert retriever == mock_retriever
            # Verify it loaded 2 documents
            call_args = mock_vs.call_args
            docs = call_args[0][0]  # first positional arg = documents
            assert len(docs) >= 2


def test_build_docs_retriever_unknown_software_raises(tmp_path):
    """build_docs_retriever raises FileNotFoundError for unknown software."""
    docs_dir = tmp_path / "software_docs"
    docs_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="No docs found"):
        build_docs_retriever(
            "nonexistent-software", RAGSettings(), software_docs_dir=str(docs_dir)
        )
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `conda run -n langgraph pytest tests/test_tools/ -v`
Expected: FAIL

- [ ] **Step 7: Write docs_loader.py**

Create: `simagents/tools/docs_loader.py`

```python
"""Software documentation loading and retriever construction."""
from __future__ import annotations

from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from simagents.config.settings import RAGSettings
from simagents.tools.pdf_loader import _get_embeddings, _build_vector_store, _get_text_splitter


def build_docs_retriever(
    target_software: str,
    rag_settings: RAGSettings,
    software_docs_dir: str = "./data/software_docs",
):
    """Build a VectorStoreRetriever from software documentation.

    Args:
        target_software: Name of the simulation software (e.g., "mp-gadget").
        rag_settings: RAG configuration.
        software_docs_dir: Base directory for software docs.

    Returns:
        A VectorStoreRetriever for searching the software docs.

    Raises:
        FileNotFoundError: If no docs directory exists for the target software.
    """
    docs_path = Path(software_docs_dir) / target_software
    if not docs_path.exists() or not any(docs_path.glob("*.md")):
        raise FileNotFoundError(
            f"No docs found for '{target_software}' at {docs_path}. "
            f"Add markdown files to {docs_path}/ to support this software."
        )

    loader = DirectoryLoader(
        str(docs_path), glob="**/*.md", loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    documents = loader.load()

    splitter = _get_text_splitter(rag_settings)
    chunks = splitter.split_documents(documents)

    embeddings = _get_embeddings(rag_settings)
    vector_store = _build_vector_store(chunks, embeddings, rag_settings.vector_store)
    return vector_store.as_retriever()
```

- [ ] **Step 8: Write tools/__init__.py**

Create: `simagents/tools/__init__.py`

```python
"""RAG tools for PDF and documentation loading."""
from .pdf_loader import get_pdf_loader, build_paper_retriever
from .docs_loader import build_docs_retriever

__all__ = ["get_pdf_loader", "build_paper_retriever", "build_docs_retriever"]
```

- [ ] **Step 9: Run all tests**

Run: `conda run -n langgraph pytest tests/test_tools/ tests/test_types.py tests/test_config.py -v`
Expected: ALL PASS

- [ ] **Step 10: Commit**

```bash
git add simagents/tools/ tests/test_tools/ data/software_docs/
git commit -m "feat: add RAG tools layer — PDF loader factory, docs loader, MP-Gadget reference docs"
```

---

## Task 3: Prompts

**Files:**
- Create: `simagents/prompts/physics_expert.md`
- Create: `simagents/prompts/formatter.md`

- [ ] **Step 1: Write physics_expert.md**

Create: `simagents/prompts/physics_expert.md`

```markdown
You are an expert in physics, especially cosmology and numerical simulations.

Your task is to extract simulation parameters from the provided source material for {target_software} simulations.

## Input
{input_context}

## Instructions

1. Search the source material for cosmological parameters:
   - Matter density (Omega_m or Omega0)
   - Dark energy density (OmegaLambda)
   - Baryon density (OmegaBaryon)
   - Hubble parameter (h or H0)
   - Power spectrum normalization (sigma8 or Sigma8)
   - Scalar spectral index (n_s or PrimordialIndex)
   - CMB temperature

2. Search for simulation box properties:
   - Box size (note the units — Mpc/h, kpc/h, etc.)
   - Particle count or grid resolution (Ngrid, Npart)
   - Mass resolution

3. Search for initial conditions:
   - Starting redshift
   - Power spectrum source (file, Eisenstein & Hu, CAMB)
   - Transfer function settings
   - Random seed if specified

4. Search for output specifications:
   - Output redshifts or scale factors
   - Final redshift (TimeMax as scale factor)
   - Snapshot configuration

5. Search for special physics:
   - Neutrino settings
   - Star formation / feedback
   - Black hole models
   - Modified gravity

## Rules
- For each parameter, cite where you found it (section, page, table, equation number)
- Include units as specified in the source
- If a value must be calculated from other values, show the calculation
- Distinguish between directly stated values and inferred/calculated values
- **Do NOT guess or assume values** — if a parameter is not found, explicitly state it is missing
- If multiple values are possible (e.g., different simulation runs in the same paper), extract all and note which run each belongs to

{custom_prompt}

## Output Format
Respond with a structured list of all found parameters:
- Parameter name
- Value (with units)
- Source location (page, section, table)
- Notes (calculated, assumed, directly stated)
- Confidence (high: directly stated, medium: calculated, low: inferred)
```

- [ ] **Step 2: Write formatter.md**

Create: `simagents/prompts/formatter.md`

```markdown
You are an expert in {target_software} simulation software configuration.
You have access to {target_software} documentation through search to ensure proper parameter formatting.

## Your Tasks

1. **Search the documentation** for parameter requirements, valid ranges, default values, and unit conventions
2. **Organize** the extracted parameters into the correct configuration sections as defined by {target_software} documentation
3. **Validate** all required parameters are present by checking the documentation
4. **Convert units** as needed (e.g., Mpc/h → kpc/h for BoxSize)
5. **Flag missing parameters** that are required but not found

## Input Parameters
{raw_parameters}

## Rules
- Search the documentation for EVERY parameter to verify its name, format, and valid range
- Do NOT hardcode parameter lists — discover what is required from the documentation
- If a parameter value is outside the documented valid range, flag it
- Use documentation defaults for truly optional parameters that are not specified
- Preserve the source citations from the physics expert

## Completion Control
You control when extraction is complete. Set the "status" field:
- `"incomplete"`: Required parameters are missing. List them in `missing_parameters`.
- `"needs_user_input"`: Parameters cannot be found in the paper and require user input. List questions in `user_questions`.
- `"complete"`: All required parameters are present and validated.

## Output Format
Respond with ONLY this JSON (no additional text):

```json
{{
  "genic": {{
    "parameter_name": "value"
  }},
  "gadget": {{
    "parameter_name": "value"
  }},
  "comment": "Explanation of parameter values, sources, unit conversions, and any assumptions",
  "sources": [
    {{"param": "name", "value": "val", "location": "Section X, Page Y", "page": 0}}
  ],
  "status": "complete|incomplete|needs_user_input",
  "missing_parameters": [],
  "user_questions": []
}}
```
```

- [ ] **Step 3: Commit**

```bash
git add simagents/prompts/
git commit -m "feat: add externalized prompt templates for physics_expert and formatter"
```

---

## Task 4: Graph State & Node Functions

**Files:**
- Create: `simagents/graph/state.py`
- Create: `simagents/nodes/parse_input.py`
- Create: `simagents/nodes/physics_expert.py`
- Create: `simagents/nodes/formatter.py`
- Create: `simagents/nodes/check_done.py`
- Create: `simagents/nodes/ask_user.py`
- Create: `simagents/nodes/save_output.py`
- Create: `tests/test_nodes/test_parse_input.py`
- Create: `tests/test_nodes/test_check_done.py`
- Create: `tests/test_nodes/test_save_output.py`
- Create: `tests/test_nodes/test_physics_expert.py`
- Create: `tests/test_nodes/test_formatter.py`

This is the largest task. It builds all 6 graph nodes with tests.

### Sub-task 4a: State definition

- [ ] **Step 1: Write graph/state.py**

Create: `simagents/graph/state.py`

```python
"""LangGraph state definition for the parameter extraction graph."""
from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ExtractionState(TypedDict):
    """Internal state for the extraction graph.

    Note: Retrievers are NOT stored in state (not serializable).
    They are passed via LangGraph's configurable dict.

    All fields must be provided in the initial invoke() call.
    Use None/empty defaults where appropriate.
    """
    # Input
    input_mode: str  # "paper" | "chat" | "hybrid"
    paper_path: str | None
    user_parameters: dict | None
    target_software: str
    custom_prompt: str | None

    # Extraction state
    raw_parameters: str
    formatted_parameters: dict
    status: str  # "complete" | "incomplete" | "needs_user_input"
    missing_parameters: list[str]
    user_questions: list[str]
    user_answers: list[dict]
    iteration: int
    max_iterations: int
    messages: Annotated[list[BaseMessage], add_messages]  # Reducer: auto-accumulates
```

Note: Since `total=True` (default), the initial `graph.invoke()` call must provide all fields. The graph construction in `parameter_extraction.py` will set defaults for fields not provided by the user (see Task 5).

### Sub-task 4b: parse_input node

- [ ] **Step 2: Write failing test for parse_input**

Create: `tests/test_nodes/test_parse_input.py`

```python
"""Tests for parse_input node."""
from simagents.nodes.parse_input import parse_input


def test_parse_input_paper_mode():
    state = {"paper_path": "/path/paper.pdf", "user_parameters": None}
    result = parse_input(state)
    assert result["input_mode"] == "paper"


def test_parse_input_chat_mode():
    state = {"paper_path": None, "user_parameters": {"BoxSize": 100000}}
    result = parse_input(state)
    assert result["input_mode"] == "chat"


def test_parse_input_hybrid_mode():
    state = {"paper_path": "/path/paper.pdf", "user_parameters": {"BoxSize": 100000}}
    result = parse_input(state)
    assert result["input_mode"] == "hybrid"


def test_parse_input_no_input_raises():
    state = {"paper_path": None, "user_parameters": None}
    import pytest
    with pytest.raises(ValueError, match="No input provided"):
        parse_input(state)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `conda run -n langgraph pytest tests/test_nodes/test_parse_input.py -v`
Expected: FAIL

- [ ] **Step 4: Write parse_input.py**

Create: `simagents/nodes/parse_input.py`

```python
"""Parse input node — detects paper/chat/hybrid mode."""
from __future__ import annotations

from simagents.graph.state import ExtractionState


def parse_input(state: ExtractionState) -> dict:
    """Detect input mode from the presence of paper_path and/or user_parameters.

    Returns:
        State update with input_mode and iteration initialized.
    """
    has_paper = bool(state.get("paper_path"))
    has_params = bool(state.get("user_parameters"))

    if has_paper and has_params:
        mode = "hybrid"
    elif has_paper:
        mode = "paper"
    elif has_params:
        mode = "chat"
    else:
        raise ValueError(
            "No input provided. Supply paper_path, user_parameters, or both."
        )

    return {"input_mode": mode, "iteration": 0}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `conda run -n langgraph pytest tests/test_nodes/test_parse_input.py -v`
Expected: PASS

### Sub-task 4c: check_done node

- [ ] **Step 6: Write failing test for check_done**

Create: `tests/test_nodes/test_check_done.py`

```python
"""Tests for check_done routing node."""
from simagents.nodes.check_done import check_done


def test_check_done_complete():
    state = {"status": "complete", "iteration": 1, "max_iterations": 2}
    assert check_done(state) == "done"


def test_check_done_max_iterations_reached():
    state = {"status": "incomplete", "iteration": 2, "max_iterations": 2}
    assert check_done(state) == "done"


def test_check_done_needs_user_input():
    state = {"status": "needs_user_input", "iteration": 0, "max_iterations": 2}
    assert check_done(state) == "needs_user_input"


def test_check_done_loop():
    state = {"status": "incomplete", "iteration": 0, "max_iterations": 2}
    assert check_done(state) == "loop"
```

- [ ] **Step 7: Run test to verify it fails**

Run: `conda run -n langgraph pytest tests/test_nodes/test_check_done.py -v`
Expected: FAIL

- [ ] **Step 8: Write check_done.py**

Create: `simagents/nodes/check_done.py`

```python
"""check_done routing node — pure logic, no LLM call."""
from __future__ import annotations

from simagents.graph.state import ExtractionState


def check_done(state: ExtractionState) -> str:
    """Determine the next step based on extraction status.

    Returns:
        "done" — extraction complete or max iterations reached
        "needs_user_input" — required params missing, ask the user
        "loop" — retry with missing parameter context
    """
    status = state.get("status", "incomplete")
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 2)

    if status == "complete":
        return "done"

    if iteration >= max_iterations:
        return "done"

    if status == "needs_user_input":
        return "needs_user_input"

    return "loop"
```

- [ ] **Step 9: Run test to verify it passes**

Run: `conda run -n langgraph pytest tests/test_nodes/test_check_done.py -v`
Expected: PASS

### Sub-task 4d: save_output node

- [ ] **Step 10: Write failing test for save_output**

Create: `tests/test_nodes/test_save_output.py`

```python
"""Tests for save_output node."""
import json
from pathlib import Path

from simagents.nodes.save_output import save_output


def test_save_output_writes_json_files(tmp_path):
    state = {
        "formatted_parameters": {
            "genic": {"BoxSize": 100000, "Ngrid": 64},
            "gadget": {"Omega0": 0.3, "TimeMax": 1.0},
            "comment": "Test extraction",
            "sources": [{"param": "BoxSize", "value": 100000, "location": "Table 1", "page": 3}],
        },
        "status": "complete",
        "missing_parameters": [],
        "paper_path": "/path/to/my_paper.pdf",
    }

    config = {"configurable": {"output_dir": str(tmp_path)}}
    result = save_output(state, config)

    # Check files were written
    genic_path = tmp_path / "my_paper_genic.json"
    gadget_path = tmp_path / "my_paper_gadget.json"
    assert genic_path.exists()
    assert gadget_path.exists()

    genic_data = json.loads(genic_path.read_text())
    assert genic_data["parameters"]["BoxSize"] == 100000

    gadget_data = json.loads(gadget_path.read_text())
    assert gadget_data["parameters"]["Omega0"] == 0.3

    assert result["status"] == "complete"
```

- [ ] **Step 11: Run test to verify it fails**

Run: `conda run -n langgraph pytest tests/test_nodes/test_save_output.py -v`
Expected: FAIL

- [ ] **Step 12: Write save_output.py**

Create: `simagents/nodes/save_output.py`

```python
"""save_output node — writes extraction results to JSON files."""
from __future__ import annotations

import json
from pathlib import Path

from simagents.graph.state import ExtractionState


def save_output(state: ExtractionState, config: dict) -> dict:
    """Write formatted parameters to genic and gadget JSON files.

    Args:
        state: Current extraction state.
        config: LangGraph config with configurable.output_dir.

    Returns:
        State update with file paths.
    """
    output_dir = Path(config.get("configurable", {}).get("output_dir", "./output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    # Derive paper name from path
    paper_path = state.get("paper_path")
    if paper_path:
        paper_name = Path(paper_path).stem
    else:
        paper_name = "extraction"

    formatted = state.get("formatted_parameters", {})
    comment = formatted.get("comment", "")
    sources = formatted.get("sources", [])

    # Write genic parameters
    genic_file = output_dir / f"{paper_name}_genic.json"
    genic_data = {
        "source": paper_path or "user_input",
        "parameters": formatted.get("genic", {}),
        "comment": comment,
        "sources": sources,
    }
    genic_file.write_text(json.dumps(genic_data, indent=2))

    # Write gadget parameters
    gadget_file = output_dir / f"{paper_name}_gadget.json"
    gadget_data = {
        "source": paper_path or "user_input",
        "parameters": formatted.get("gadget", {}),
        "comment": comment,
        "sources": sources,
    }
    gadget_file.write_text(json.dumps(gadget_data, indent=2))

    return {
        "status": state.get("status", "incomplete"),
    }
```

- [ ] **Step 13: Run test to verify it passes**

Run: `conda run -n langgraph pytest tests/test_nodes/test_save_output.py -v`
Expected: PASS

### Sub-task 4e: physics_expert node

- [ ] **Step 14: Write failing test for physics_expert**

Create: `tests/test_nodes/test_physics_expert.py`

```python
"""Tests for physics_expert node."""
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from simagents.nodes.physics_expert import physics_expert


def test_physics_expert_paper_mode():
    """physics_expert extracts parameters and returns raw_parameters."""
    state = {
        "input_mode": "paper",
        "target_software": "mp-gadget",
        "custom_prompt": None,
        "iteration": 0,
        "missing_parameters": [],
        "user_answers": [],
    }

    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = [
        MagicMock(page_content="BoxSize = 100 Mpc/h (Table 1)")
    ]

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content="- BoxSize: 100 Mpc/h (Table 1, page 5)\n- Omega0: 0.3 (Section 2)"
    )

    config = {"configurable": {"paper_retriever": mock_retriever, "llm": mock_llm}}
    result = physics_expert(state, config)

    assert "raw_parameters" in result
    assert len(result["raw_parameters"]) > 0
    assert result["iteration"] == 1


def test_physics_expert_chat_mode():
    """physics_expert in chat mode uses user_parameters directly."""
    state = {
        "input_mode": "chat",
        "target_software": "mp-gadget",
        "custom_prompt": None,
        "user_parameters": {"BoxSize": 100000, "Omega0": 0.3},
        "iteration": 0,
        "missing_parameters": [],
        "user_answers": [],
    }

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content="- BoxSize: 100000 kpc/h (user provided)\n- Omega0: 0.3 (user provided)"
    )

    config = {"configurable": {"paper_retriever": None, "llm": mock_llm}}
    result = physics_expert(state, config)

    assert "raw_parameters" in result
```

- [ ] **Step 15: Run test to verify it fails**

Run: `conda run -n langgraph pytest tests/test_nodes/test_physics_expert.py -v`
Expected: FAIL

- [ ] **Step 16: Write physics_expert.py**

Create: `simagents/nodes/physics_expert.py`

```python
"""physics_expert node — extracts parameters from paper or user input via RAG."""
from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from simagents.graph.state import ExtractionState


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "physics_expert.md"


def _load_prompt(target_software: str, input_context: str, custom_prompt: str | None) -> str:
    """Load and render the physics expert prompt template."""
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    return template.format(
        target_software=target_software,
        input_context=input_context,
        custom_prompt=custom_prompt or "",
    )


def _build_input_context(state: ExtractionState) -> str:
    """Build the input context string based on input mode."""
    mode = state.get("input_mode", "paper")
    parts = []

    if mode in ("paper", "hybrid"):
        parts.append("A scientific paper has been provided. Use the search tool to find parameter values.")

    if mode in ("chat", "hybrid"):
        user_params = state.get("user_parameters", {})
        parts.append(f"User-provided parameters: {user_params}")
        if mode == "hybrid":
            parts.append("User-provided values take precedence over paper values.")

    # Add context from previous iterations
    missing = state.get("missing_parameters", [])
    if missing:
        parts.append(f"\nPrevious iteration found these parameters MISSING: {', '.join(missing)}")
        parts.append("Please search specifically for these missing parameters.")

    user_answers = state.get("user_answers", [])
    if user_answers:
        parts.append(f"\nUser provided these answers: {user_answers}")

    return "\n".join(parts)


def physics_expert(state: ExtractionState, config: dict) -> dict:
    """Extract simulation parameters from paper/user input.

    Accesses paper_retriever and llm from config["configurable"].
    """
    configurable = config.get("configurable", {})
    llm = configurable["llm"]
    paper_retriever = configurable.get("paper_retriever")

    target_software = state.get("target_software", "mp-gadget")
    input_context = _build_input_context(state)
    system_prompt = _load_prompt(target_software, input_context, state.get("custom_prompt"))

    # Build the user message
    user_msg_parts = ["Please extract the simulation parameters from the provided source."]

    # If we have a paper retriever, search for relevant chunks
    if paper_retriever and state.get("input_mode") in ("paper", "hybrid"):
        search_queries = [
            "cosmological parameters simulation",
            "box size resolution particle number",
            "initial conditions redshift",
        ]
        # Add targeted searches for missing params
        missing = state.get("missing_parameters", [])
        if missing:
            search_queries.append(" ".join(missing))

        retrieved_chunks = []
        for query in search_queries:
            docs = paper_retriever.invoke(query)
            for doc in docs:
                retrieved_chunks.append(doc.page_content)

        if retrieved_chunks:
            context = "\n---\n".join(retrieved_chunks)
            user_msg_parts.append(f"\n## Relevant sections from the paper:\n{context}")

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="\n".join(user_msg_parts)),
    ]

    response = llm.invoke(messages)
    iteration = state.get("iteration", 0)

    return {
        "raw_parameters": response.content,
        "iteration": iteration + 1,
        "messages": [HumanMessage(content=f"[Iteration {iteration + 1}] Extract parameters"),
                     response],
    }
```

- [ ] **Step 17: Run test to verify it passes**

Run: `conda run -n langgraph pytest tests/test_nodes/test_physics_expert.py -v`
Expected: PASS

### Sub-task 4f: formatter node

- [ ] **Step 18: Write failing test for formatter**

Create: `tests/test_nodes/test_formatter.py`

```python
"""Tests for formatter node."""
import json
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from simagents.nodes.formatter import formatter


def test_formatter_complete():
    """formatter returns formatted_parameters with status complete."""
    json_output = json.dumps({
        "genic": {"BoxSize": 100000, "Ngrid": 64},
        "gadget": {"Omega0": 0.3, "TimeMax": 1.0},
        "comment": "All params found",
        "sources": [{"param": "BoxSize", "value": 100000, "location": "Table 1", "page": 3}],
        "status": "complete",
        "missing_parameters": [],
        "user_questions": [],
    })

    state = {
        "raw_parameters": "- BoxSize: 100 Mpc/h\n- Omega0: 0.3",
        "target_software": "mp-gadget",
    }

    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = [
        MagicMock(page_content="BoxSize: kpc/h. Required.")
    ]
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content=json_output)

    config = {"configurable": {"docs_retriever": mock_retriever, "llm": mock_llm}}
    result = formatter(state, config)

    assert result["status"] == "complete"
    assert result["formatted_parameters"]["genic"]["BoxSize"] == 100000


def test_formatter_incomplete():
    """formatter returns incomplete status with missing parameters."""
    json_output = json.dumps({
        "genic": {"BoxSize": 100000},
        "gadget": {},
        "comment": "Missing required params",
        "sources": [],
        "status": "incomplete",
        "missing_parameters": ["Omega0", "HubbleParam"],
        "user_questions": [],
    })

    state = {
        "raw_parameters": "- BoxSize: 100 Mpc/h",
        "target_software": "mp-gadget",
    }

    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = []
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content=json_output)

    config = {"configurable": {"docs_retriever": mock_retriever, "llm": mock_llm}}
    result = formatter(state, config)

    assert result["status"] == "incomplete"
    assert "Omega0" in result["missing_parameters"]
```

- [ ] **Step 19: Run test to verify it fails**

Run: `conda run -n langgraph pytest tests/test_nodes/test_formatter.py -v`
Expected: FAIL

- [ ] **Step 20: Write formatter.py**

Create: `simagents/nodes/formatter.py`

```python
"""formatter node — validates and formats parameters against software docs via RAG."""
from __future__ import annotations

import json
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from simagents.graph.state import ExtractionState


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "formatter.md"


def _load_prompt(target_software: str, raw_parameters: str) -> str:
    """Load and render the formatter prompt template."""
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    return template.format(
        target_software=target_software,
        raw_parameters=raw_parameters,
    )


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling code blocks and raw JSON."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try code block extraction
    code_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_match:
        try:
            return json.loads(code_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding any JSON object
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON from response: {text[:200]}...")


def formatter(state: ExtractionState, config: dict) -> dict:
    """Validate and format extracted parameters against software documentation.

    Accesses docs_retriever and llm from config["configurable"].
    """
    configurable = config.get("configurable", {})
    llm = configurable["llm"]
    docs_retriever = configurable["docs_retriever"]

    target_software = state.get("target_software", "mp-gadget")
    raw_parameters = state.get("raw_parameters", "")

    system_prompt = _load_prompt(target_software, raw_parameters)

    # Search docs for parameter requirements
    search_queries = [
        f"{target_software} required parameters",
        f"{target_software} parameter format units",
        "cosmological parameters configuration",
    ]
    retrieved_docs = []
    for query in search_queries:
        docs = docs_retriever.invoke(query)
        for doc in docs:
            retrieved_docs.append(doc.page_content)

    doc_context = "\n---\n".join(retrieved_docs) if retrieved_docs else "No documentation found."

    user_msg = (
        f"## Documentation Reference\n{doc_context}\n\n"
        f"## Extracted Parameters\n{raw_parameters}\n\n"
        f"Please validate and format these parameters according to {target_software} documentation."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_msg),
    ]

    response = llm.invoke(messages)

    # Parse the JSON response
    try:
        parsed = _extract_json(response.content)
    except ValueError:
        # Retry once with explicit instruction
        retry_msg = HumanMessage(
            content="Your response was not valid JSON. Please respond with ONLY the JSON object, no other text."
        )
        response = llm.invoke(messages + [response, retry_msg])
        try:
            parsed = _extract_json(response.content)
        except ValueError:
            return {
                "formatted_parameters": {"genic": {}, "gadget": {}, "comment": response.content, "sources": []},
                "status": "incomplete",
                "missing_parameters": ["JSON_PARSE_FAILED"],
                "messages": [response],
            }

    return {
        "formatted_parameters": parsed,
        "status": parsed.get("status", "incomplete"),
        "missing_parameters": parsed.get("missing_parameters", []),
        "user_questions": parsed.get("user_questions", []),
        "messages": [response],
    }
```

- [ ] **Step 21: Run test to verify it passes**

Run: `conda run -n langgraph pytest tests/test_nodes/test_formatter.py -v`
Expected: PASS

### Sub-task 4g: ask_user node

- [ ] **Step 22: Write ask_user.py**

Create: `simagents/nodes/ask_user.py`

```python
"""ask_user node — human-in-the-loop interrupt for missing parameters."""
from __future__ import annotations

from langgraph.types import interrupt

from simagents.graph.state import ExtractionState


def ask_user(state: ExtractionState) -> dict:
    """Pause the graph and ask the user for missing parameter values.

    Uses LangGraph's interrupt() to suspend execution until the user responds.
    """
    questions = state.get("user_questions", [])
    missing = state.get("missing_parameters", [])

    prompt_parts = []
    if questions:
        prompt_parts.append("The following questions need your input:")
        for q in questions:
            prompt_parts.append(f"  - {q}")
    if missing:
        prompt_parts.append(f"\nMissing required parameters: {', '.join(missing)}")
        prompt_parts.append("Please provide values for these parameters.")

    prompt = "\n".join(prompt_parts)

    # This suspends the graph and waits for user input
    user_response = interrupt(prompt)

    # user_response is expected to be a dict of parameter values
    answers = state.get("user_answers", [])
    if isinstance(user_response, dict):
        answers = answers + [user_response]
    else:
        answers = answers + [{"raw_response": user_response}]

    return {"user_answers": answers}
```

### Sub-task 4h: ask_user and _extract_json tests

- [ ] **Step 23: Write test for ask_user node**

Create: `tests/test_nodes/test_ask_user.py`

```python
"""Tests for ask_user node."""
from unittest.mock import patch, MagicMock

from simagents.nodes.ask_user import ask_user


def test_ask_user_builds_prompt_and_returns_answers():
    """ask_user constructs a prompt from missing params and returns user answers."""
    state = {
        "user_questions": ["What BoxSize do you want?"],
        "missing_parameters": ["BoxSize", "Omega0"],
        "user_answers": [],
    }

    # Mock interrupt() to simulate user responding with a dict
    with patch("simagents.nodes.ask_user.interrupt", return_value={"BoxSize": 100000, "Omega0": 0.3}):
        result = ask_user(state)

    assert len(result["user_answers"]) == 1
    assert result["user_answers"][0]["BoxSize"] == 100000


def test_ask_user_handles_string_response():
    """ask_user wraps non-dict responses in a raw_response key."""
    state = {
        "user_questions": [],
        "missing_parameters": ["BoxSize"],
        "user_answers": [],
    }

    with patch("simagents.nodes.ask_user.interrupt", return_value="BoxSize should be 100000"):
        result = ask_user(state)

    assert result["user_answers"][0]["raw_response"] == "BoxSize should be 100000"
```

- [ ] **Step 24: Write test for _extract_json helper**

Create: `tests/test_nodes/test_extract_json.py`

```python
"""Tests for the _extract_json helper in formatter."""
import pytest

from simagents.nodes.formatter import _extract_json


def test_extract_json_raw():
    """Parses raw JSON string."""
    result = _extract_json('{"genic": {"BoxSize": 100000}, "status": "complete"}')
    assert result["genic"]["BoxSize"] == 100000


def test_extract_json_code_block():
    """Extracts JSON from markdown code block."""
    text = 'Here is the result:\n```json\n{"genic": {}, "status": "complete"}\n```'
    result = _extract_json(text)
    assert result["status"] == "complete"


def test_extract_json_embedded_in_prose():
    """Extracts JSON embedded in prose text."""
    text = 'The parameters are: {"genic": {"Ngrid": 64}, "status": "incomplete"} as shown above.'
    result = _extract_json(text)
    assert result["genic"]["Ngrid"] == 64


def test_extract_json_failure():
    """Raises ValueError when no JSON found."""
    with pytest.raises(ValueError, match="Could not extract JSON"):
        _extract_json("This has no JSON at all.")
```

- [ ] **Step 25: Run new tests**

Run: `conda run -n langgraph pytest tests/test_nodes/test_ask_user.py tests/test_nodes/test_extract_json.py -v`
Expected: ALL PASS

### Sub-task 4i: nodes __init__.py

- [ ] **Step 26: Write nodes/__init__.py**

Create: `simagents/nodes/__init__.py`

```python
"""Graph node functions."""
from .parse_input import parse_input
from .physics_expert import physics_expert
from .formatter import formatter
from .check_done import check_done
from .ask_user import ask_user
from .save_output import save_output

__all__ = ["parse_input", "physics_expert", "formatter", "check_done", "ask_user", "save_output"]
```

- [ ] **Step 27: Run all node tests**

Run: `conda run -n langgraph pytest tests/test_nodes/ -v`
Expected: ALL PASS

- [ ] **Step 28: Commit**

```bash
git add simagents/graph/state.py simagents/nodes/ tests/test_nodes/
git commit -m "feat: add all graph nodes — parse_input, physics_expert, formatter, check_done, ask_user, save_output"
```

---

## Task 5: Graph Construction & Factory Function

**Files:**
- Create: `simagents/graph/parameter_extraction.py`
- Create: `simagents/graph/__init__.py`
- Create: `simagents/__init__.py`
- Create: `tests/test_graph/test_parameter_extraction.py`

- [ ] **Step 1: Write failing test for graph construction**

Create: `tests/test_graph/test_parameter_extraction.py`

```python
"""Tests for the parameter extraction graph."""
import json
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from simagents.graph.parameter_extraction import create_extraction_graph
from simagents.config.settings import Settings


def test_create_extraction_graph_returns_compiled_graph():
    """create_extraction_graph returns a runnable graph."""
    settings = Settings()
    graph = create_extraction_graph(settings, checkpointer=MemorySaver())
    assert graph is not None
    # Graph should be invokable
    assert hasattr(graph, "invoke")


def test_graph_paper_mode_complete():
    """Full graph run with mocked LLM produces complete output."""
    settings = Settings()
    graph = create_extraction_graph(settings, checkpointer=MemorySaver())

    # Mock LLM that returns extraction then complete JSON
    mock_llm = MagicMock()
    extraction_response = AIMessage(content="- BoxSize: 100 Mpc/h (Table 1)\n- Omega0: 0.3 (Section 2)")
    formatter_response = AIMessage(content=json.dumps({
        "genic": {"BoxSize": 100000, "Ngrid": 64},
        "gadget": {"Omega0": 0.3, "TimeMax": 1.0},
        "comment": "Extracted from paper",
        "sources": [{"param": "BoxSize", "value": 100000, "location": "Table 1", "page": 3}],
        "status": "complete",
        "missing_parameters": [],
        "user_questions": [],
    }))
    mock_llm.invoke.side_effect = [extraction_response, formatter_response]

    mock_paper_retriever = MagicMock()
    mock_paper_retriever.invoke.return_value = [
        MagicMock(page_content="BoxSize = 100 Mpc/h")
    ]

    mock_docs_retriever = MagicMock()
    mock_docs_retriever.invoke.return_value = [
        MagicMock(page_content="BoxSize: kpc/h. Required.")
    ]

    result = graph.invoke(
        {
            "paper_path": "/fake/paper.pdf",
            "user_parameters": None,
            "target_software": "mp-gadget",
            "custom_prompt": None,
            "max_iterations": 2,
            # Required defaults for total=True state
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
                "llm": mock_llm,
                "paper_retriever": mock_paper_retriever,
                "docs_retriever": mock_docs_retriever,
                "output_dir": "/tmp/simagents_test",
                "thread_id": "test-1",
            }
        },
    )

    assert result["status"] == "complete"
    assert result["formatted_parameters"]["genic"]["BoxSize"] == 100000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n langgraph pytest tests/test_graph/test_parameter_extraction.py -v`
Expected: FAIL

- [ ] **Step 3: Write parameter_extraction.py**

Create: `simagents/graph/parameter_extraction.py`

```python
"""Parameter extraction StateGraph construction."""
from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from simagents.config.settings import Settings
from simagents.graph.state import ExtractionState
from simagents.nodes import (
    parse_input,
    physics_expert,
    formatter,
    check_done,
    ask_user,
    save_output,
)


def create_extraction_graph(
    settings: Settings,
    checkpointer: BaseCheckpointSaver | None = None,
):
    """Build and compile the parameter extraction StateGraph.

    Args:
        settings: Application settings.
        checkpointer: LangGraph checkpointer for interrupt() support.
            Use MemorySaver() for CLI, SqliteSaver/PostgresSaver for production.

    Returns:
        A compiled LangGraph StateGraph.
    """
    graph = StateGraph(ExtractionState)

    # Add nodes
    graph.add_node("parse_input", parse_input)
    graph.add_node("physics_expert", physics_expert)
    graph.add_node("formatter", formatter)
    graph.add_node("ask_user", ask_user)
    graph.add_node("save_output", save_output)

    # Set entry point
    graph.set_entry_point("parse_input")

    # Edges
    graph.add_edge("parse_input", "physics_expert")
    graph.add_edge("physics_expert", "formatter")

    # Conditional routing from formatter via check_done
    graph.add_conditional_edges(
        "formatter",
        check_done,
        {
            "done": "save_output",
            "loop": "physics_expert",
            "needs_user_input": "ask_user",
        },
    )

    # After user answers, go back to physics_expert
    graph.add_edge("ask_user", "physics_expert")

    # save_output is terminal
    graph.add_edge("save_output", END)

    return graph.compile(checkpointer=checkpointer)
```

- [ ] **Step 4: Write graph/__init__.py**

Create: `simagents/graph/__init__.py`

```python
"""Graph package."""
from .parameter_extraction import create_extraction_graph

__all__ = ["create_extraction_graph"]
```

- [ ] **Step 5: Write simagents/__init__.py**

Create: `simagents/__init__.py`

```python
"""SimAgents — Multi-agent parameter extraction for cosmological simulations."""
from simagents.graph.parameter_extraction import create_extraction_graph
from simagents.types import ExtractionInput, ExtractionOutput

__all__ = ["create_extraction_graph", "ExtractionInput", "ExtractionOutput"]
```

- [ ] **Step 6: Run test to verify it passes**

Run: `conda run -n langgraph pytest tests/test_graph/test_parameter_extraction.py -v`
Expected: PASS

- [ ] **Step 7: Run full test suite**

Run: `conda run -n langgraph pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 8: Commit**

```bash
git add simagents/graph/ simagents/__init__.py tests/test_graph/
git commit -m "feat: add LangGraph extraction graph with factory function and full test coverage"
```

---

## Task 6: CLI Entry Point

**Files:**
- Create: `main.py`

- [ ] **Step 1: Write main.py**

Create: `main.py`

```python
"""CLI entry point for SimAgents parameter extraction."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver

from simagents.config.settings import Settings
from simagents.graph.parameter_extraction import create_extraction_graph
from simagents.tools.pdf_loader import build_paper_retriever
from simagents.tools.docs_loader import build_docs_retriever


def _get_llm(settings: Settings):
    """Initialize the LLM from settings."""
    from langchain.chat_models import init_chat_model

    kwargs = {"temperature": settings.llm.temperature}

    # Pass API key based on provider
    if settings.llm.provider == "openai" and settings.openai_api_key:
        kwargs["api_key"] = settings.openai_api_key
    elif settings.llm.provider == "anthropic" and settings.anthropic_api_key:
        kwargs["api_key"] = settings.anthropic_api_key
    elif settings.llm.provider == "google" and settings.google_api_key:
        kwargs["api_key"] = settings.google_api_key

    return init_chat_model(
        model=settings.llm.model,
        model_provider=settings.llm.provider,
        **kwargs,
    )


def main():
    parser = argparse.ArgumentParser(description="SimAgents: Extract simulation parameters from papers")
    parser.add_argument("--paper", type=str, help="Path to the PDF paper")
    parser.add_argument("--software", type=str, default=None, help="Target simulation software")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config YAML")
    parser.add_argument("--output", type=str, default=None, help="Output directory")
    parser.add_argument("--prompt", type=str, default=None, help="Custom extraction instructions")
    args = parser.parse_args()

    # Load env and config
    load_dotenv()
    settings = Settings.from_yaml(args.config)

    if args.software:
        settings.extraction.target_software = args.software
    if args.output:
        settings.paths.output_dir = args.output

    # Build components
    print(f"Using LLM: {settings.llm.provider}/{settings.llm.model}")
    llm = _get_llm(settings)

    paper_retriever = None
    if args.paper:
        print(f"Loading paper: {args.paper}")
        paper_retriever = build_paper_retriever(args.paper, settings.rag)

    print(f"Loading {settings.extraction.target_software} docs...")
    docs_retriever = build_docs_retriever(
        settings.extraction.target_software,
        settings.rag,
        software_docs_dir=settings.paths.software_docs_dir,
    )

    # Build and run graph
    graph = create_extraction_graph(settings, checkpointer=MemorySaver())

    print("Starting parameter extraction...")
    result = graph.invoke(
        {
            "paper_path": args.paper,
            "user_parameters": None,
            "target_software": settings.extraction.target_software,
            "custom_prompt": args.prompt,
            "max_iterations": settings.extraction.max_iterations,
            # State defaults
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
                "output_dir": settings.paths.output_dir,
                "thread_id": "cli-main",
            }
        },
    )

    print(f"\nExtraction status: {result.get('status', 'unknown')}")
    if result.get("missing_parameters"):
        print(f"Missing parameters: {', '.join(result['missing_parameters'])}")
    print(f"Output saved to: {settings.paths.output_dir}/")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add main.py
git commit -m "feat: add CLI entry point for parameter extraction"
```

---

## Task 7: Visualization (Standalone Cleanup)

**Files:**
- Create: `simagents/visualization/__init__.py`
- Create: `simagents/visualization/power_spectrum.py`
- Create: `simagents/visualization/density_field.py`

- [ ] **Step 1: Write power_spectrum.py**

Port the plotting logic from the existing `agents/visualization_agent.py`, removing ag2 dependency and using `init_chat_model()`:

Create: `simagents/visualization/power_spectrum.py`

```python
"""Standalone power spectrum plotter — model-agnostic, no ag2 dependency."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from simagents.config.settings import Settings

SYSTEM_PROMPT = """You are a scientific visualization expert. Generate a complete, self-contained Python script
that creates a power spectrum plot from MP-Gadget simulation output.

Requirements:
- Use matplotlib for plotting
- Use loglog scale for both axes
- Label axes: k [h/Mpc] and P(k) [(Mpc/h)^3]
- Calculate redshift from scale factor: z = 1/a - 1
- Create publication-quality plots with legends
- Save the plot to the specified output path
- The script must be fully self-contained (all imports included)
"""


class PowerSpectrumPlotter:
    """Generate and execute power spectrum plots from simulation output."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = init_chat_model(
            model=settings.llm.model,
            model_provider=settings.llm.provider,
            temperature=settings.llm.temperature,
        )

    def plot(self, output_dir: str, output_filename: str = "power_spectrum.png") -> str:
        """Generate a power spectrum plot.

        Args:
            output_dir: Directory containing powerspectrum-*.txt files.
            output_filename: Name for the output PNG.

        Returns:
            Path to the saved plot.
        """
        output_path = Path(output_dir)
        ps_files = sorted(output_path.glob("powerspectrum-*.txt"))
        if not ps_files:
            raise FileNotFoundError(f"No powerspectrum-*.txt files in {output_dir}")

        # Read Snapshots.txt if available
        snapshots_info = ""
        snapshots_file = output_path / "Snapshots.txt"
        if snapshots_file.exists():
            snapshots_info = f"Snapshots.txt content:\n{snapshots_file.read_text()}\n"

        file_list = "\n".join(str(f) for f in ps_files[:20])  # Limit for context
        save_path = str(output_path / output_filename)

        user_msg = (
            f"Create a power spectrum plot from these files:\n{file_list}\n\n"
            f"{snapshots_info}\n"
            f"Save the plot to: {save_path}"
        )

        response = self.llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ])

        # Extract and execute the Python code
        code = self._extract_code(response.content)
        return self._execute_code(code)

    def _extract_code(self, text: str) -> str:
        """Extract Python code from LLM response."""
        import re
        match = re.search(r"```python\s*(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1)
        return text

    def _execute_code(self, code: str) -> str:
        """Execute Python code in a subprocess."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            script_path = f.name

        result = subprocess.run(
            ["python", script_path],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Plot script failed:\n{result.stderr}")
        return script_path
```

- [ ] **Step 2: Write density_field.py**

Create: `simagents/visualization/density_field.py`

```python
"""Standalone density field plotter — model-agnostic, no ag2 dependency."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from simagents.config.settings import Settings

SYSTEM_PROMPT = """You are a gaepsi2 visualization expert. Generate a complete Python script
for creating 3D density field plots from MP-Gadget simulation data.

Key components:
- BigFile for loading PART_* particle data
- gaepsi2.camera for 3D transformations
- gaepsi2.painter.paint for rendering density fields
- matplotlib for final plots

The script must be fully self-contained and executable.
"""


class DensityFieldPlotter:
    """Generate and execute density field plots from simulation output."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = init_chat_model(
            model=settings.llm.model,
            model_provider=settings.llm.provider,
            temperature=settings.llm.temperature,
        )

    def plot(
        self,
        simulation_dir: str,
        snapshot: str = "PART_000",
        particle_type: int = 1,
        output_filename: str = "density_field.png",
    ) -> str:
        """Generate a density field plot.

        Args:
            simulation_dir: Directory containing simulation output.
            snapshot: Snapshot directory name (e.g., PART_000).
            particle_type: Particle type (0=gas, 1=dark matter).
            output_filename: Name for the output PNG.

        Returns:
            Path to the saved plot.
        """
        sim_path = Path(simulation_dir)
        save_path = str(sim_path / output_filename)

        user_msg = (
            f"Create a 3D density field visualization from:\n"
            f"- Simulation directory: {simulation_dir}\n"
            f"- Snapshot: {snapshot}\n"
            f"- Particle type: {particle_type} ({'dark matter' if particle_type == 1 else 'gas'})\n"
            f"- Save to: {save_path}\n"
        )

        response = self.llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ])

        code = self._extract_code(response.content)
        return self._execute_code(code)

    def _extract_code(self, text: str) -> str:
        import re
        match = re.search(r"```python\s*(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1)
        return text

    def _execute_code(self, code: str) -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            script_path = f.name

        result = subprocess.run(
            ["python", script_path],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Density field script failed:\n{result.stderr}")
        return script_path
```

- [ ] **Step 3: Write visualization/__init__.py**

Create: `simagents/visualization/__init__.py`

```python
"""Standalone visualization tools."""
from .power_spectrum import PowerSpectrumPlotter
from .density_field import DensityFieldPlotter

__all__ = ["PowerSpectrumPlotter", "DensityFieldPlotter"]
```

- [ ] **Step 4: Commit**

```bash
git add simagents/visualization/
git commit -m "feat: add standalone visualization tools — power spectrum and density field plotters"
```

---

## Task 8: Utils & Final Wiring

**Files:**
- Create: `simagents/utils/file_utils.py`
- Create: `simagents/utils/slurm_utils.py`
- Create: `simagents/utils/__init__.py`

- [ ] **Step 1: Write file_utils.py**

Port from existing `utils/file_utils.py`, removing hardcoded paths:

Create: `simagents/utils/file_utils.py`

```python
"""File utility functions."""
from __future__ import annotations

import json
from pathlib import Path


def read_json(path: str | Path) -> dict:
    """Read a JSON file and return its contents."""
    with open(path, "r") as f:
        return json.load(f)


def write_json(data: dict, path: str | Path, indent: int = 2) -> None:
    """Write data to a JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=indent)
```

- [ ] **Step 2: Write slurm_utils.py**

Port from existing, using config instead of hardcoded defaults:

Create: `simagents/utils/slurm_utils.py`

```python
"""SLURM job submission utilities."""
from __future__ import annotations

from pathlib import Path

from simagents.config.settings import SLURMSettings


def generate_slurm_script(
    job_name: str,
    genic_param_file: str,
    gadget_param_file: str,
    mp_gadget_root: str,
    slurm_settings: SLURMSettings,
    output_dir: str = ".",
) -> str:
    """Generate a SLURM batch script for running MP-Gadget.

    Args:
        job_name: SLURM job name.
        genic_param_file: Path to GenIC parameter file.
        gadget_param_file: Path to Gadget parameter file.
        mp_gadget_root: Path to MP-Gadget installation.
        slurm_settings: SLURM configuration.
        output_dir: Directory for SLURM output files.

    Returns:
        The SLURM script as a string.
    """
    script = f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --partition={slurm_settings.partition}
#SBATCH --nodes={slurm_settings.nodes}
#SBATCH --ntasks-per-node={slurm_settings.ntasks}
#SBATCH --cpus-per-task={slurm_settings.cpus_per_task}
#SBATCH --time={slurm_settings.time}
#SBATCH --mem-per-cpu={slurm_settings.mem_per_cpu}
#SBATCH --output={output_dir}/{job_name}_%j.out

# Run GenIC to generate initial conditions
mpirun -np $SLURM_NTASKS {mp_gadget_root}/genic/MP-GenIC {genic_param_file}

# Run MP-Gadget simulation
mpirun -np $SLURM_NTASKS {mp_gadget_root}/gadget/MP-Gadget {gadget_param_file}
"""
    return script
```

- [ ] **Step 3: Write utils/__init__.py**

Create: `simagents/utils/__init__.py`

```python
"""Utility functions."""
from .file_utils import read_json, write_json

__all__ = ["read_json", "write_json"]
```

- [ ] **Step 4: Run full test suite**

Run: `conda run -n langgraph pytest tests/ -v --tb=short`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add simagents/utils/ requirements.txt
git commit -m "feat: add utils, finalize package structure"
```

---

## Task 9: Update .gitignore & Final Cleanup

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Update .gitignore**

Add to `.gitignore`:

```
# Config with secrets
config.yaml
.env

# Chroma persistent storage
chroma_db/

# Output
output/

# Python
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
build/
```

- [ ] **Step 2: Run full test suite one final time**

Run: `conda run -n langgraph pytest tests/ -v --tb=short`
Expected: ALL PASS

- [ ] **Step 3: Final commit**

```bash
git add .gitignore
git commit -m "chore: update gitignore for langgraph branch"
```

- [ ] **Step 4: Verify branch state**

```bash
git log --oneline feature/langgraph-rewrite
```

Expected: Clean chain of commits from scaffold through final cleanup.
