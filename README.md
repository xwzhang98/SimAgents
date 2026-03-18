# SimAgents

A model-agnostic multi-agent framework for automating cosmological simulation workflows. SimAgents extracts simulation parameters from scientific papers, validates them against software documentation, and generates ready-to-run configuration files.

Built with [LangGraph](https://github.com/langchain-ai/langgraph) for orchestration and [LangChain](https://github.com/langchain-ai/langchain) for RAG and LLM abstraction.

## Features

- **Parameter Extraction**: Extract simulation parameters from PDF papers using RAG-powered multi-agent workflow
- **Model Agnostic**: Use any LLM provider — OpenAI, Anthropic Claude, Google Gemini, or local models via Ollama
- **Multi-Software Support**: Target different simulation software (MP-Gadget, Arepo, Gadget-4, Enzo) by adding docs
- **Human-in-the-Loop**: When parameters are missing, the system asks you instead of guessing
- **Composable**: Use as a CLI tool or import as a Python library / LangGraph subgraph
- **Visualization**: Standalone power spectrum and density field plotters

## Architecture

```
[Paper PDF / User Input]
         |
    parse_input          ← detect paper/chat/hybrid mode
         |
    physics_expert       ← RAG search paper → extract parameters
         |
    formatter            ← RAG search software docs → validate & format
         |
    check_done           ← complete? loop? ask user?
    /    |    \
loop  ask_user  done
         |       |
    [interrupt]  save_output → genic.json + gadget.json
```

## Installation

### Prerequisites

- Python 3.11+
- An API key for your chosen LLM provider

### Setup

```bash
git clone https://github.com/xwzhang98/SimAgents.git
cd SimAgents
git checkout feature/langgraph-rewrite

# Create environment (conda recommended)
conda create -n langgraph python=3.11 -y
conda activate langgraph

# Install with your preferred LLM provider
pip install -e ".[dev,openai]"        # For OpenAI GPT models
pip install -e ".[dev,anthropic]"     # For Anthropic Claude
pip install -e ".[dev,google]"        # For Google Gemini
pip install -e ".[dev,ollama]"        # For local models via Ollama

# Optional: better PDF parsing (heavy dependency)
pip install -e ".[unstructured]"
```

### Configuration

```bash
# Copy templates
cp config.example.yaml config.yaml
cp .env.example .env

# Edit .env with your API key
echo 'OPENAI_API_KEY=sk-...' > .env
```

Edit `config.yaml` to set your provider and model:

```yaml
llm:
  provider: "openai"          # or "anthropic", "google", "ollama"
  model: "gpt-4o"             # or "claude-sonnet-4-20250514", "gemini-pro", etc.
  temperature: 0.01

rag:
  pdf_loader: "pypdf"         # or "unstructured" (better but heavier)
  vector_store: "chroma"
```

## Usage

### CLI

```bash
# Extract parameters from a paper
python main.py --paper path/to/paper.pdf

# Target different simulation software
python main.py --paper paper.pdf --software arepo

# Custom output directory
python main.py --paper paper.pdf --output ./results

# Add custom instructions
python main.py --paper paper.pdf --prompt "Extract parameters for the low-resolution run"
```

### Python Library

```python
from simagents import create_extraction_graph
from simagents.config import Settings
from simagents.tools import build_paper_retriever, build_docs_retriever
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver

settings = Settings.from_yaml("config.yaml")
llm = init_chat_model("gpt-4o", model_provider="openai")

paper_retriever = build_paper_retriever("paper.pdf", settings.rag)
docs_retriever = build_docs_retriever("mp-gadget", settings.rag)

graph = create_extraction_graph(settings, checkpointer=MemorySaver())
result = graph.invoke(
    {
        "paper_path": "paper.pdf",
        "target_software": "mp-gadget",
        "custom_prompt": None,
        "user_parameters": None,
        "max_iterations": 2,
        "input_mode": "", "raw_parameters": "", "formatted_parameters": {},
        "status": "", "missing_parameters": [], "user_questions": [],
        "user_answers": [], "iteration": 0, "messages": [],
    },
    config={
        "configurable": {
            "llm": llm,
            "paper_retriever": paper_retriever,
            "docs_retriever": docs_retriever,
            "output_dir": "./output",
            "thread_id": "my-session",
        }
    },
)
```

### As a Subgraph (e.g., inside Denario)

```python
from simagents import create_extraction_graph

parent_graph.add_node("parameter_extraction", create_extraction_graph(config, checkpointer=...))
```

## Output

The system produces two JSON files per extraction:

**`<paper>_genic.json`** — Initial conditions parameters:
```json
{
  "source": "path/to/paper.pdf",
  "parameters": {
    "BoxSize": 100000,
    "Ngrid": 64,
    "Omega0": 0.2814,
    "OmegaLambda": 0.7186,
    "HubbleParam": 0.697,
    "Redshift": 99
  }
}
```

**`<paper>_gadget.json`** — Runtime simulation parameters.

## Adding New Simulation Software

Add a docs folder with markdown reference files:

```
data/software_docs/
  my-software/
    parameter_reference.md
    other_docs.md
```

Then run with `--software my-software`.

## Golden Standard Database

Includes validated parameter configurations from major simulations for benchmarking:
IllustrisTNG, Millennium, MTNG, Magneticum, ASTRID, BlueTides, and more.

## Testing

```bash
conda activate langgraph
pytest tests/ -v
```

## Project Structure

```
simagents/
  config/         Settings (YAML + env vars)
  tools/          PDF loader, docs loader (RAG)
  prompts/        Externalized prompt templates
  nodes/          LangGraph node functions
  graph/          StateGraph construction
  visualization/  Standalone plotters
  utils/          File helpers, SLURM utils
```

## GUI

### Quick Start (one command)

```bash
conda activate langgraph
pip install -r requirements.txt
./start.sh
```

This starts both backend and frontend, and opens the browser automatically.

### Manual Start (two terminals)

```bash
# Terminal 1: Backend
conda activate langgraph
pip install -e ".[gui]"
uvicorn simagents.api.server:app --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

## Citation

If you use SimAgents in your research, please cite:

> Zhang et al., "SimAgents: A Multi-Agent Framework for Cosmological Simulation Automation", IJCNLP 2025 Demo. [ACL Anthology](https://aclanthology.org/2025.ijcnlp-demo.7/)

## Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) — Multi-agent orchestration
- [LangChain](https://github.com/langchain-ai/langchain) — LLM abstraction and RAG
- [MP-Gadget](https://github.com/MP-Gadget/MP-Gadget) — Cosmological simulation code
- [gaepsi2](https://github.com/rainwoodman/gaepsi2) — 3D visualization
