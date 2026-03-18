# SimAgents LangGraph Rewrite — Design Spec

## Overview

Rewrite SimAgents from ag2/AutoGen + OpenAI Assistants to LangGraph + LangChain. Goals:
1. **Switch orchestration** from ag2 to LangGraph
2. **Decouple from OpenAI** — support any LLM provider (Claude, GPT, Gemini, open-source)
3. **Clean up code** — externalize prompts, remove hardcoded values, proper config system
4. **Remove baselines** — this branch is for users, not research comparison

Work happens on a **new git branch** (`langgraph`). Clean rewrite, not incremental migration.

---

## 1. Project Structure

```
SimAgents/
├── simagents/                    # Importable package
│   ├── __init__.py               # Exports create_extraction_graph, types
│   ├── types.py                  # ExtractionInput, ExtractionOutput contracts
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py              # LangGraph internal state definition
│   │   └── parameter_extraction.py  # Main StateGraph construction
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── parse_input.py        # Detect input mode (paper/chat/hybrid)
│   │   ├── physics_expert.py     # Extract parameters from paper/user input
│   │   ├── formatter.py          # Validate & format against target software docs
│   │   ├── check_done.py         # Routing logic: done / loop / needs_user_input
│   │   ├── ask_user.py           # Human-in-the-loop interrupt for missing params
│   │   └── save_output.py        # Write genic/gadget JSON files
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── pdf_loader.py         # Configurable PDF loading + chunking
│   │   └── docs_loader.py        # Software docs RAG builder
│   ├── prompts/
│   │   ├── physics_expert.md     # Externalized, templatized prompt
│   │   └── formatter.md          # Externalized, templatized prompt
│   ├── visualization/
│   │   ├── __init__.py
│   │   ├── power_spectrum.py     # Standalone power spectrum plotter
│   │   └── density_field.py      # Standalone density field plotter
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py           # Pydantic BaseSettings, merges YAML + env
│   └── utils/
│       ├── __init__.py
│       ├── file_utils.py
│       └── slurm_utils.py
├── data/
│   ├── software_docs/            # Docs per simulation software
│   │   ├── mp-gadget/
│   │   ├── arepo/
│   │   ├── gadget-4/
│   │   └── enzo/
│   └── gaepsi2_demo.py
├── golden_standard/              # Reference parameter database (unchanged)
├── example/                      # Example data (unchanged)
├── config.yaml                   # User config (gitignored)
├── config.example.yaml           # Template shipped with repo
├── .env                          # API keys (gitignored)
├── requirements.txt
└── main.py                       # Thin CLI entry point
```

Key decisions:
- Everything inside `simagents/` package — importable as library or usable as CLI
- No `baseline/` directory on this branch
- `golden_standard/`, `example/` carry over unchanged
- `data/software_docs/` is **new** — must be created and populated with reference docs for each supported simulation software (MP-Gadget docs exist in the current system via OpenAI vector stores; these need to be exported/written as markdown files)
- Prompts in markdown files, not hardcoded in Python

---

## 2. Configuration System

### Layered: YAML + env vars

**`config.yaml`** — non-secret settings:
```yaml
llm:
  provider: "anthropic"           # "openai" | "anthropic" | "google" | "ollama" | etc.
  model: "claude-sonnet-4-20250514"
  temperature: 0.01

rag:
  pdf_loader: "unstructured"      # "unstructured" | "pymupdf" | "pypdf" | "docling"
  vector_store: "chroma"          # "chroma" | "faiss"
  chunk_size: 1000
  chunk_overlap: 200
  embedding_provider: "openai"    # or "huggingface" for fully local
  embedding_model: "text-embedding-3-small"

extraction:
  max_iterations: 2
  target_software: "mp-gadget"    # default target

paths:
  output_dir: "./output"

slurm:                            # optional, for HPC users
  partition: "RM"
  nodes: 1
  time: "16:00:00"
```

**`.env`** — secrets only:
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
```

**`settings.py`** — Pydantic `BaseSettings` merges both sources with validation.

---

## 3. LLM Abstraction

Uses LangChain's `init_chat_model()`:

```python
from langchain.chat_models import init_chat_model

llm = init_chat_model(
    model=config.llm.model,
    model_provider=config.llm.provider,
    temperature=config.llm.temperature,
)
```

Users install only the provider package they need:
- `langchain-openai` for GPT models
- `langchain-anthropic` for Claude
- `langchain-google-genai` for Gemini
- `langchain-ollama` for local open-source models

---

## 4. RAG & Tools Layer

### PDF loading pipeline

Configurable loader factory:

```python
def get_pdf_loader(path: str, loader_type: str):
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
```

Default: Unstructured (best for academic papers with equations/tables).

### Vector store

Default: Chroma (easy install, built-in persistence). FAISS available as option.

Pipeline: Loader → `RecursiveCharacterTextSplitter` → Embeddings → Chroma/FAISS → `VectorStoreRetriever`

### Software docs

```
data/software_docs/
  mp-gadget/
    paramfile_reference.md
    genic_reference.md
  arepo/
    config_reference.md
  ...
```

Same pipeline as PDF but from markdown files. One index per software target. Adding new software support = add a docs folder.

### Retriever as tool

Retrievers wrapped as LangChain tools so the LLM picks its own search queries:

```python
paper_search = create_retriever_tool(
    paper_retriever,
    "search_paper",
    "Search the uploaded scientific paper for parameter values"
)
```

---

## 5. LangGraph State & Graph

### Input/Output contract (public API)

```python
class ExtractionInput(TypedDict):
    paper_path: str | None          # PDF path, or None for chat mode
    user_parameters: dict | None    # User-provided params, or None
    target_software: str            # "mp-gadget" | "arepo" | "gadget-4" | etc.
    custom_prompt: str | None       # Optional additional instructions

class ExtractionOutput(TypedDict):
    genic_parameters: dict
    gadget_parameters: dict
    status: str                     # "complete" | "incomplete"
    missing: list[str]
    comment: str
    sources: list[dict]             # Provenance: [{param, value, location, page}]
```

### Internal state (superset of input/output)

```python
from typing import Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class ExtractionState(TypedDict):
    # Input
    input_mode: str                         # "paper" | "chat" | "hybrid"
    paper_path: str | None
    user_parameters: dict | None
    target_software: str
    custom_prompt: str | None               # Optional — defaults to None

    # Extraction state
    raw_parameters: str
    formatted_parameters: dict
    status: str                             # "complete" | "incomplete" | "needs_user_input"
    missing_parameters: list[str]
    user_questions: list[str]
    user_answers: list[dict]
    iteration: int
    max_iterations: int
    messages: Annotated[list[BaseMessage], add_messages]  # Auto-accumulates across iterations
```

**Note on RAG resources:** Retrievers (`VectorStoreRetriever`) are **not** stored in state — they are not serializable, and LangGraph requires serializable state for checkpointing (needed by `interrupt()`). Instead, retrievers are built **before** graph invocation and passed via LangGraph's `configurable` dict:

```python
# In create_extraction_graph() or the CLI entry point:
paper_retriever = build_paper_retriever(paper_path, config)  # returns VectorStoreRetriever
docs_retriever = build_docs_retriever(target_software, config)  # returns VectorStoreRetriever

graph.invoke(
    {"paper_path": "paper.pdf", "target_software": "mp-gadget"},
    config={"configurable": {"paper_retriever": paper_retriever, "docs_retriever": docs_retriever}}
)
```

Nodes access retrievers via `config` parameter, not state. This means the `load_sources` node is a **pre-graph setup step**, not a graph node — it runs before `graph.invoke()`. The graph itself starts at `parse_input`.

### Checkpointer

The graph requires a checkpointer for `interrupt()` to work. Default: `MemorySaver` (in-memory, sufficient for CLI usage). For web/API deployments, swap to `SqliteSaver` or `PostgresSaver`:

```python
from langgraph.checkpoint.memory import MemorySaver

graph = create_extraction_graph(config, checkpointer=MemorySaver())
```

### Graph topology

```
    [Pre-graph: build_paper_retriever + build_docs_retriever → passed via configurable]
                     │
              ┌──────▼────────┐
              │  parse_input   │  detect mode: paper/chat/hybrid
              └──────┬────────┘
                     │
              ┌──────▼────────┐
          ┌──►│physics_expert  │  RAG search paper → extract parameters
          │   └──────┬────────┘
          │          │
          │   ┌──────▼────────┐
          │   │  formatter     │  RAG search docs → validate & format JSON
          │   └──────┬────────┘
          │          │
          │   ┌──────▼────────┐
          │   │  check_done    │  routing: done / loop / needs_user_input
          │   └──┬───┬───┬────┘
          │      │   │   │
          │ loop │   │   │ done
          └──────┘   │   │
                     │   ├──────►┌──────────────┐
                     │           │  save_output  │
                     │           └──────────────┘
                     │ needs_user_input
              ┌──────▼────────┐
              │  ask_user      │  LangGraph interrupt() for human-in-the-loop
              └──────┬────────┘
                     │ user responds
                     └──► back to physics_expert
```

### Node behavior

- **`parse_input`** — detects input mode from presence of `paper_path` and/or `user_parameters`
- **`physics_expert`** — loads prompt from `prompts/physics_expert.md`, injects `target_software` and `custom_prompt`, uses `paper_retriever` tool. On subsequent iterations, includes `missing_parameters` and prior `messages` for context. Writes `raw_parameters`.
- **`formatter`** — loads prompt from `prompts/formatter.md`, uses `docs_retriever` tool to look up parameter requirements for target software. Validates `raw_parameters`, outputs structured JSON. Writes `formatted_parameters`, `status`, `missing_parameters`.
- **`check_done`** — pure logic, no LLM. Returns `"done"` if status is complete or max iterations reached. Returns `"needs_user_input"` if required params are missing and can't be found. Returns `"loop"` otherwise.
- **`ask_user`** — uses LangGraph's built-in `interrupt()` to pause the graph, surface questions to the user, and resume with answers.
- **`save_output`** — splits `formatted_parameters` into separate JSON files per config section, writes to output dir.

---

## 6. Prompt Strategy

Prompts live in `prompts/*.md` with template variables:

### physics_expert.md
- Generic physics extraction — not specific to any simulation software
- Template vars: `{target_software}`, `{input_context}`, `{custom_prompt}`
- Explicit instruction: "do not guess values — report missing parameters"
- No hardcoded parameter lists — the formatter handles software-specific requirements

### formatter.md
- Software-aware validation via RAG on target software docs
- Template vars: `{target_software}`, `{raw_parameters}`
- Discovers required parameters from docs (not hardcoded lists)
- Controls completion via `status` field in JSON output
- Explicit output format specification

---

## 7. Extensibility

### SimAgents as a composable subgraph

The extraction graph is built via a factory function:

```python
# Standalone usage:
from simagents import create_extraction_graph
graph = create_extraction_graph(config, checkpointer=MemorySaver())
result = graph.invoke({"paper_path": "paper.pdf", "target_software": "mp-gadget"})

# As subgraph in a larger system (e.g., Denario):
from simagents import create_extraction_graph
parent_graph.add_node("parameter_extraction", create_extraction_graph(config, checkpointer=MemorySaver()))
```

### Design principles for extensibility
- **Typed input/output contract** — `ExtractionInput` / `ExtractionOutput` are the only public interface. Internal state stays hidden.
- **Package structure** — `simagents/` is importable as a library, `main.py` is a thin CLI wrapper
- **No hardcoded downstream** — the graph emits results, doesn't dictate what happens next
- **Software-agnostic** — adding new simulation software = adding a docs folder in `data/software_docs/`

### Future integration points (not built now)
| Future need | How current design supports it |
|---|---|
| Plug into Denario/CMBagent | Import `create_extraction_graph()` as subgraph node |
| Add execution agent | New subgraph taking `ExtractionOutput` as input |
| Add feedback loop | Parent graph routes execution results back |
| Web/Slack UI | Input/Output are plain dicts — any frontend works |

---

## 8. Visualization (Standalone)

Visualization agents are cleaned up but NOT part of the LangGraph graph:

```python
# visualization/power_spectrum.py
class PowerSpectrumPlotter:
    def __init__(self, config): ...
    def plot(self, output_dir, output_filename) -> str: ...

# visualization/density_field.py
class DensityFieldPlotter:
    def __init__(self, config): ...
    def plot(self, simulation_dir, snapshot, ...) -> str: ...
```

Changes from current:
- Use `init_chat_model()` instead of hardcoded GPT-4o
- Use config system instead of hardcoded paths
- Remove ag2 dependency — direct LLM calls + `subprocess`/`langchain_experimental.tools.PythonREPL` for code execution
- Same model-agnostic design as the main graph

---

## 9. Error Handling

**Philosophy: fail fast with clear messages.** This is a research tool — silent degradation is worse than a clear error.

- **PDF loading failure** (corrupted PDF, scanned-only images): Raise with a clear message suggesting alternative loaders. If in hybrid mode, fall back to chat-only extraction.
- **Embedding API failure** (rate limit, network): Raise with retry suggestion. Do not silently skip RAG.
- **Retriever returns no results**: The node proceeds but includes a note in its output that no relevant content was found. The formatter will flag these as missing parameters.
- **LLM returns unparseable JSON** (formatter output): Retry once with a more explicit prompt. If still fails, return raw output with `status: "incomplete"`.
- **Max iterations reached with incomplete status**: Save what was extracted, return with `status: "incomplete"` and `missing` list populated. Do not silently pretend it's complete.

---

## 10. Testing Strategy

- **Unit tests**: Test each node independently with mock state dicts. No LLM calls needed — mock the LLM responses.
- **Integration tests**: Test the full graph with a sample paper from `example/`. Requires API keys.
- **RAG tests**: Test PDF loading + chunking + retrieval pipeline independently from the graph.
- **Config tests**: Test that YAML + env var merging works, that missing required fields raise clear errors.

---

## 11. Dependencies

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

# LLM providers (user installs what they need)
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
# langchain-experimental>=0.3.0  # PythonREPL for code execution
# gaepsi2
# bigfile

# Dev
pytest>=7.0.0
pytest-cov>=4.0.0
black>=23.0.0
ruff>=0.1.0
mypy>=1.0.0
```

---

## 12. What Gets Deleted

From the new `langgraph` branch, remove:
- `baseline/` — entire directory (comparison retrievers)
- `agents/base_agent.py` — ag2 base class
- `agents/parameter_retriever.py` — OpenAI Assistants implementation
- `agents/visualization_agent.py` — ag2 visualization agent
- `agents/density_field_agent.py` — OpenAI Assistants density field agent
- `agents/code_executor.py` — ag2 code executor
- `agents/base_retriever.py` — ag2 base retriever
- `workflows/` — entire directory (ag2 orchestration)
- Hardcoded assistant IDs, cluster paths, OpenAI-specific config
- Hardcoded parameter validation lists (e.g., required genic/gadget fields in `base_retriever.py`) — **intentionally replaced** by RAG-driven validation where the formatter discovers required parameters from the target software's docs
