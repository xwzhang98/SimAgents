# SimAgents GUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web GUI (Next.js + FastAPI) for the SimAgents parameter extraction system with a three-panel layout: sidebar navigation, chat with agent streaming, and live parameter panel.

**Architecture:** FastAPI backend wraps the existing `simagents` package with SSE streaming endpoints. Next.js frontend with React components for the chat interface, parameter display, and settings. Communication via REST (actions) and SSE (agent event streaming).

**Tech Stack:** FastAPI, uvicorn, sse-starlette, Next.js 14, React 18, Tailwind CSS, TypeScript

**Spec:** `docs/superpowers/specs/2026-03-18-gui-design.md`

---

## File Structure

### Backend (Python — additions to simagents/)

```
simagents/
├── api/
│   ├── __init__.py
│   ├── server.py              # FastAPI app, CORS, include routers
│   ├── session.py             # ExtractionSession, SessionManager
│   └── routes/
│       ├── __init__.py
│       ├── extract.py         # POST /api/extract, GET /api/stream/{id}, POST /api/respond/{id}
│       ├── upload.py          # POST /api/upload
│       ├── settings_routes.py # GET/PUT /api/settings (named to avoid shadowing config.settings)
│       └── parameters.py      # GET/PUT /api/parameters/{id}, GET /api/parameters/{id}/export
├── config/
│   └── settings.py            # Modify: add to_yaml() method
```

### Frontend (TypeScript — new frontend/ directory)

```
frontend/
├── package.json
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── postcss.config.js
├── src/
│   ├── app/
│   │   ├── layout.tsx         # Root layout: dark theme, font, full-height
│   │   ├── page.tsx           # Main page: sidebar + conditional chat/params or settings
│   │   └── globals.css        # Tailwind directives + custom styles
│   ├── components/
│   │   ├── Sidebar.tsx        # Icon nav: chat, params, settings
│   │   ├── ChatPanel.tsx      # Message list + input area
│   │   ├── MessageBubble.tsx  # Agent message (left) or user message (right)
│   │   ├── QuickReply.tsx     # HITL question with orange border + inline input
│   │   ├── ParameterPanel.tsx # Tabs, param table, edit, export, status bar
│   │   ├── FileUpload.tsx     # Paperclip button + drag-drop
│   │   └── SettingsView.tsx   # Settings form with save/cancel
│   └── lib/
│       ├── api.ts             # Typed fetch wrappers for all endpoints
│       ├── sse.ts             # EventSource wrapper with reconnect
│       └── types.ts           # Shared TypeScript types
└── public/
```

---

## Task 0: Backend Dependencies & Scaffold

**Files:**
- Modify: `pyproject.toml` — add FastAPI deps to optional `[gui]` group
- Create: `simagents/api/__init__.py`
- Create: `simagents/api/routes/__init__.py`

- [ ] **Step 1: Add GUI dependencies to pyproject.toml**

Add to `pyproject.toml` under `[project.optional-dependencies]`:

```toml
gui = ["fastapi>=0.104.0", "uvicorn>=0.24.0", "python-multipart>=0.0.6", "sse-starlette>=1.6.0"]
```

- [ ] **Step 2: Install GUI deps**

```bash
conda run -n langgraph pip install -e ".[gui]"
```

- [ ] **Step 3: Create API package scaffold**

```bash
mkdir -p simagents/api/routes
touch simagents/api/__init__.py simagents/api/routes/__init__.py
```

- [ ] **Step 4: Add Settings.to_yaml() method**

Modify `simagents/config/settings.py` — add this method to the `Settings` class:

```python
def to_yaml(self, yaml_path: str | Path) -> None:
    """Write settings to a YAML file (excludes API keys)."""
    yaml_path = Path(yaml_path)
    data = {}
    for field_name in ["llm", "rag", "extraction", "paths", "slurm"]:
        value = getattr(self, field_name)
        if value is not None:
            data[field_name] = value.model_dump()
    with open(yaml_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
```

- [ ] **Step 5: Add test for to_yaml**

Add to `tests/test_config.py`:

```python
def test_settings_to_yaml(tmp_path):
    """Settings can be written to YAML and read back."""
    settings = Settings()
    settings.llm.provider = "anthropic"
    settings.llm.model = "claude-sonnet-4-20250514"
    yaml_path = tmp_path / "config.yaml"
    settings.to_yaml(str(yaml_path))
    loaded = Settings.from_yaml(str(yaml_path))
    assert loaded.llm.provider == "anthropic"
    assert loaded.llm.model == "claude-sonnet-4-20250514"
    # Only named subsections should be in the YAML (not API keys)
    content = yaml_path.read_text()
    assert "openai_api_key" not in content
    assert "anthropic_api_key" not in content
    assert "google_api_key" not in content
    # Verify subsections are present
    assert "llm:" in content
    assert "anthropic" in content
```

- [ ] **Step 6: Run tests, commit**

```bash
conda run -n langgraph pytest tests/test_config.py -v
git add pyproject.toml simagents/api/ simagents/config/settings.py tests/test_config.py
git commit -m "chore: scaffold API package, add GUI deps, add Settings.to_yaml()"
```

---

## Task 1: Session Manager

**Files:**
- Create: `simagents/api/session.py`
- Create: `tests/test_api/test_session.py`

- [ ] **Step 1: Create test directory**

```bash
mkdir -p tests/test_api
touch tests/test_api/__init__.py
```

- [ ] **Step 2: Write tests for SessionManager**

Create: `tests/test_api/test_session.py`

```python
"""Tests for the API session manager."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from simagents.api.session import ExtractionSession, SessionManager


def test_session_manager_create_session():
    mgr = SessionManager()
    sid = mgr.create_session(
        graph=MagicMock(),
        config={"configurable": {}},
        file_path="/fake/paper.pdf",
    )
    assert sid is not None
    session = mgr.get_session(sid)
    assert session is not None
    assert session.file_path == "/fake/paper.pdf"
    assert session.status == "idle"


def test_session_manager_one_active_session():
    mgr = SessionManager()
    sid1 = mgr.create_session(graph=MagicMock(), config={}, file_path=None)
    sid2 = mgr.create_session(graph=MagicMock(), config={}, file_path=None)
    assert mgr.get_session(sid1) is None  # replaced
    assert mgr.get_session(sid2) is not None


def test_session_manager_get_current():
    mgr = SessionManager()
    assert mgr.get_current() is None
    sid = mgr.create_session(graph=MagicMock(), config={}, file_path=None)
    assert mgr.get_current() is not None
    assert mgr.get_current().session_id == sid
```

- [ ] **Step 3: Write SessionManager**

Create: `simagents/api/session.py`

```python
"""Extraction session management for the API."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class ExtractionSession:
    session_id: str
    graph: object  # CompiledGraph
    config: dict
    file_path: str | None = None
    parameters: dict = field(default_factory=lambda: {"genic": {}, "gadget": {}})
    messages: list[dict] = field(default_factory=list)
    status: str = "idle"  # idle | running | waiting_input | complete


class SessionManager:
    """Manages extraction sessions. One active session at a time."""

    def __init__(self):
        self._sessions: dict[str, ExtractionSession] = {}
        self._current_id: str | None = None

    def create_session(self, graph, config: dict, file_path: str | None = None) -> str:
        """Create a new session, replacing any existing one."""
        # Clean up previous session
        if self._current_id and self._current_id in self._sessions:
            del self._sessions[self._current_id]

        session_id = str(uuid.uuid4())
        self._sessions[session_id] = ExtractionSession(
            session_id=session_id,
            graph=graph,
            config=config,
            file_path=file_path,
        )
        self._current_id = session_id
        return session_id

    def get_session(self, session_id: str) -> ExtractionSession | None:
        return self._sessions.get(session_id)

    def get_current(self) -> ExtractionSession | None:
        if self._current_id:
            return self._sessions.get(self._current_id)
        return None

    def cleanup(self):
        """Clean up temp files from all sessions."""
        import os
        for session in self._sessions.values():
            if session.file_path and os.path.exists(session.file_path):
                try:
                    os.unlink(session.file_path)
                except OSError:
                    pass
        self._sessions.clear()
        self._current_id = None


# Module-level singleton — imported by route modules (avoids circular import with server.py)
session_manager = SessionManager()
```

- [ ] **Step 4: Run tests, commit**

```bash
conda run -n langgraph pytest tests/test_api/test_session.py -v
git add simagents/api/session.py tests/test_api/
git commit -m "feat: add SessionManager for API extraction sessions"
```

---

## Task 2: FastAPI Server & Upload Route

**Files:**
- Create: `simagents/api/server.py`
- Create: `simagents/api/routes/upload.py`

- [ ] **Step 1: Write upload route**

Create: `simagents/api/routes/upload.py`

```python
"""File upload route."""
from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter()

# Store uploaded files in a temp directory
_upload_dir = Path(tempfile.mkdtemp(prefix="simagents_uploads_"))
_uploads: dict[str, Path] = {}


def get_upload_path(file_id: str) -> Path | None:
    return _uploads.get(file_id)


@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_id = str(uuid.uuid4())
    dest = _upload_dir / f"{file_id}.pdf"

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    _uploads[file_id] = dest
    return {"file_id": file_id, "filename": file.filename}
```

- [ ] **Step 2: Write server.py**

Create: `simagents/api/server.py`

```python
"""FastAPI application for SimAgents GUI."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from simagents.api.routes import upload
from simagents.api.session import session_manager  # singleton from session.py

app = FastAPI(title="SimAgents API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
def shutdown_cleanup():
    """Clean up temp files on server shutdown."""
    session_manager.cleanup()


app.include_router(upload.router)
```

- [ ] **Step 3: Smoke test — start server**

```bash
conda run -n langgraph uvicorn simagents.api.server:app --port 8000 &
sleep 2
curl -s http://localhost:8000/docs | head -5  # Should return OpenAPI HTML
kill %1
```

- [ ] **Step 4: Commit**

```bash
git add simagents/api/server.py simagents/api/routes/upload.py
git commit -m "feat: add FastAPI server with file upload endpoint"
```

---

## Task 3: Settings & Parameters Routes

**Files:**
- Create: `simagents/api/routes/settings_routes.py`
- Create: `simagents/api/routes/parameters.py`
- Modify: `simagents/api/server.py` — include new routers

- [ ] **Step 1: Write settings routes**

Create: `simagents/api/routes/settings_routes.py`

```python
"""Settings routes — read/write config.yaml."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from simagents.config.settings import Settings

router = APIRouter()

CONFIG_PATH = os.environ.get("SIMAGENTS_CONFIG", str(Path(__file__).resolve().parents[3] / "config.yaml"))


@router.get("/api/settings")
async def get_settings():
    settings = Settings.from_yaml(CONFIG_PATH)
    return {
        "llm": settings.llm.model_dump(),
        "rag": settings.rag.model_dump(),
        "extraction": settings.extraction.model_dump(),
        "paths": settings.paths.model_dump(),
        "slurm": settings.slurm.model_dump() if settings.slurm else None,
    }


@router.put("/api/settings")
async def update_settings(data: dict):
    settings = Settings.from_yaml(CONFIG_PATH)
    # Merge incoming data
    if "llm" in data:
        for k, v in data["llm"].items():
            setattr(settings.llm, k, v)
    if "rag" in data:
        for k, v in data["rag"].items():
            setattr(settings.rag, k, v)
    if "extraction" in data:
        for k, v in data["extraction"].items():
            setattr(settings.extraction, k, v)
    if "paths" in data:
        for k, v in data["paths"].items():
            setattr(settings.paths, k, v)
    settings.to_yaml(CONFIG_PATH)
    return await get_settings()
```

- [ ] **Step 2: Write parameters routes**

Create: `simagents/api/routes/parameters.py`

```python
"""Parameters routes — read/edit/export extracted parameters."""
from __future__ import annotations

import io
import json
import zipfile

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from simagents.api.session import session_manager

router = APIRouter()


@router.get("/api/parameters/{session_id}")
async def get_parameters(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "genic": session.parameters.get("genic", {}),
        "gadget": session.parameters.get("gadget", {}),
        "status": session.status,
        "missing": session.parameters.get("missing", []),
        "sources": session.parameters.get("sources", []),
    }


@router.put("/api/parameters/{session_id}")
async def update_parameters(session_id: str, data: dict):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if "genic" in data:
        session.parameters["genic"] = data["genic"]
    if "gadget" in data:
        session.parameters["gadget"] = data["gadget"]
    return await get_parameters(session_id)


@router.get("/api/parameters/{session_id}/export")
async def export_parameters(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("genic.json", json.dumps(session.parameters.get("genic", {}), indent=2))
        zf.writestr("gadget.json", json.dumps(session.parameters.get("gadget", {}), indent=2))
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": "attachment; filename=parameters.zip"})
```

- [ ] **Step 3: Update server.py to include new routers**

Add to `simagents/api/server.py`:

```python
from simagents.api.routes import settings_routes, parameters

app.include_router(settings_routes.router)
app.include_router(parameters.router)
```

- [ ] **Step 4: Commit**

```bash
git add simagents/api/routes/settings_routes.py simagents/api/routes/parameters.py simagents/api/server.py
git commit -m "feat: add settings and parameters API routes"
```

---

## Task 4: Extract & Stream Routes (SSE)

**Files:**
- Create: `simagents/api/routes/extract.py`
- Modify: `simagents/api/server.py` — include extract router

This is the core task — SSE streaming of LangGraph execution.

- [ ] **Step 1: Write extract routes**

Create: `simagents/api/routes/extract.py`

```python
"""Extraction routes — start, stream, respond."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver

from simagents.api.session import session_manager
from simagents.api.routes.upload import get_upload_path
from simagents.config.settings import Settings
from simagents.graph.parameter_extraction import create_extraction_graph
from simagents.tools.pdf_loader import build_paper_retriever
from simagents.tools.docs_loader import build_docs_retriever

router = APIRouter()
CONFIG_PATH = os.environ.get("SIMAGENTS_CONFIG", str(Path(__file__).resolve().parents[3] / "config.yaml"))


class ExtractRequest(BaseModel):
    file_id: str | None = None
    user_parameters: dict | None = None
    target_software: str | None = None
    custom_prompt: str | None = None


@router.post("/api/extract")
async def start_extraction(req: ExtractRequest):
    settings = Settings.from_yaml(CONFIG_PATH)
    target = req.target_software or settings.extraction.target_software

    # Build LLM
    llm_kwargs = {"temperature": settings.llm.temperature}
    if settings.llm.provider == "openai" and settings.openai_api_key:
        llm_kwargs["api_key"] = settings.openai_api_key
    elif settings.llm.provider == "anthropic" and settings.anthropic_api_key:
        llm_kwargs["api_key"] = settings.anthropic_api_key
    elif settings.llm.provider == "google" and settings.google_api_key:
        llm_kwargs["api_key"] = settings.google_api_key

    llm = init_chat_model(model=settings.llm.model, model_provider=settings.llm.provider, **llm_kwargs)

    # Build retrievers
    paper_retriever = None
    file_path = None
    if req.file_id:
        file_path_obj = get_upload_path(req.file_id)
        if not file_path_obj:
            raise HTTPException(status_code=404, detail="Uploaded file not found")
        file_path = str(file_path_obj)
        paper_retriever = build_paper_retriever(file_path, settings.rag)

    docs_retriever = build_docs_retriever(target, settings.rag, settings.paths.software_docs_dir)

    # Build graph
    graph = create_extraction_graph(settings, checkpointer=MemorySaver())

    config = {
        "configurable": {
            "llm": llm,
            "paper_retriever": paper_retriever,
            "docs_retriever": docs_retriever,
            "output_dir": settings.paths.output_dir,
            "thread_id": "gui-session",
        }
    }

    session_id = session_manager.create_session(graph=graph, config=config, file_path=file_path)
    session = session_manager.get_session(session_id)
    session.status = "running"

    # Store initial state for streaming
    session._initial_state = {
        "paper_path": file_path,
        "user_parameters": req.user_parameters,
        "target_software": target,
        "custom_prompt": req.custom_prompt,
        "max_iterations": settings.extraction.max_iterations,
        "input_mode": "",
        "raw_parameters": "",
        "formatted_parameters": {},
        "status": "",
        "missing_parameters": [],
        "user_questions": [],
        "user_answers": [],
        "iteration": 0,
        "messages": [],
    }

    return {"session_id": session_id}


async def _stream_events(session) -> AsyncGenerator[dict, None]:
    """Stream LangGraph execution as SSE events.

    Handles both initial runs and resumed runs (after interrupt).
    """
    try:
        # Determine if this is a resume or initial run
        if hasattr(session, "_resume_value") and session._resume_value is not None:
            from langgraph.types import Command
            input_val = Command(resume=session._resume_value)
            session._resume_value = None  # consume it
        else:
            input_val = session._initial_state

        async for event in session.graph.astream(input_val, config=session.config):
            if "parse_input" in event:
                yield {"event": "message", "data": json.dumps({
                    "type": "status", "message": f"Mode: {event['parse_input'].get('input_mode', 'unknown')}"
                })}
            elif "physics_expert" in event:
                data = event["physics_expert"]
                msg = {"type": "agent_message", "role": "physics_expert", "content": data.get("raw_parameters", "")}
                session.messages.append(msg)
                yield {"event": "message", "data": json.dumps(msg)}
            elif "formatter" in event:
                data = event["formatter"]
                fmt = data.get("formatted_parameters", {})
                # Agent message
                msg = {"type": "agent_message", "role": "formatter", "content": fmt.get("comment", "")}
                session.messages.append(msg)
                yield {"event": "message", "data": json.dumps(msg)}
                # Parameters update
                params = {
                    "genic": fmt.get("genic", {}),
                    "gadget": fmt.get("gadget", {}),
                    "status": data.get("status", "incomplete"),
                    "missing": data.get("missing_parameters", []),
                    "sources": fmt.get("sources", []),
                }
                session.parameters = params
                yield {"event": "message", "data": json.dumps({"type": "parameters_update", "data": params})}
                # Check if needs input
                if data.get("user_questions") or data.get("status") == "needs_user_input":
                    session.status = "waiting_input"
                    yield {"event": "message", "data": json.dumps({
                        "type": "needs_input",
                        "questions": data.get("user_questions", []),
                        "missing": data.get("missing_parameters", []),
                    })}
            elif "save_output" in event:
                session.status = "complete"
                yield {"event": "message", "data": json.dumps({
                    "type": "complete", "status": event["save_output"].get("status", "complete")
                })}
    except Exception as e:
        session.status = "complete"
        yield {"event": "message", "data": json.dumps({"type": "error", "message": str(e)})}


@router.get("/api/stream/{session_id}")
async def stream(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return EventSourceResponse(_stream_events(session))


class RespondRequest(BaseModel):
    answers: dict | None = None
    raw_response: str | None = None


@router.post("/api/respond/{session_id}")
async def respond(session_id: str, req: RespondRequest):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "waiting_input":
        raise HTTPException(status_code=400, detail="Session is not waiting for input")

    # Prepare the resume value
    resume_value = req.answers if req.answers else {"raw_response": req.raw_response}

    # Store for next stream call — the graph will be resumed when stream is reconnected
    session._resume_value = resume_value
    session.status = "running"

    return {"status": "resumed"}


@router.get("/api/session/status")
async def session_status():
    session = session_manager.get_current()
    if not session:
        return {"status": None, "session_id": None}
    return {
        "status": session.status,
        "session_id": session.session_id,
        "messages": session.messages,
        "parameters": session.parameters,
    }
```

- [ ] **Step 2: Update server.py**

Add to `simagents/api/server.py`:

```python
from simagents.api.routes import extract
app.include_router(extract.router)
```

- [ ] **Step 3: Commit**

```bash
git add simagents/api/routes/extract.py simagents/api/server.py
git commit -m "feat: add extraction, streaming, and respond API routes with SSE"
```

---

## Task 5: Frontend Scaffold (Next.js)

**Files:**
- Create: `frontend/` — full Next.js project via `create-next-app`

- [ ] **Step 1: Create Next.js project**

```bash
cd /Users/zhangxiaowen/AntigravityProjects/SimAgents
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --no-import-alias --use-npm
```

When prompted, accept defaults (App Router, src/ directory, Tailwind).

- [ ] **Step 2: Verify it runs**

```bash
cd frontend && npm run dev &
sleep 5
curl -s http://localhost:3000 | head -5
kill %1
cd ..
```

- [ ] **Step 3: Commit**

```bash
git add frontend/
git commit -m "chore: scaffold Next.js frontend with Tailwind CSS"
```

---

## Task 6: Frontend Types & API Client

**Files:**
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/sse.ts`

- [ ] **Step 1: Write shared types**

Create: `frontend/src/lib/types.ts`

```typescript
export interface Message {
  type: "agent_message" | "status" | "needs_input" | "complete" | "error" | "user";
  role?: "physics_expert" | "formatter" | "user" | "system";
  content?: string;
  questions?: string[];
  missing?: string[];
  status?: string;
  message?: string;
}

export interface ParametersData {
  genic: Record<string, unknown>;
  gadget: Record<string, unknown>;
  status: string;
  missing: string[];
  sources: Array<{ param: string; value: unknown; location: string; page: number }>;
}

export interface SSEEvent {
  type: string;
  role?: string;
  content?: string;
  data?: ParametersData;
  questions?: string[];
  missing?: string[];
  status?: string;
  message?: string;
}

export interface SettingsData {
  llm: { provider: string; model: string; temperature: number };
  rag: { pdf_loader: string; vector_store: string; chunk_size: number; chunk_overlap: number; embedding_provider: string; embedding_model: string };
  extraction: { max_iterations: number; target_software: string };
  paths: { output_dir: string; software_docs_dir: string };
  slurm: Record<string, unknown> | null;
}

export type View = "chat" | "settings";
```

- [ ] **Step 2: Write API client**

Create: `frontend/src/lib/api.ts`

```typescript
const API_BASE = "http://localhost:8000";

export async function uploadFile(file: File): Promise<{ file_id: string; filename: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function startExtraction(params: {
  file_id?: string | null;
  user_parameters?: Record<string, unknown> | null;
  target_software?: string | null;
  custom_prompt?: string | null;
}): Promise<{ session_id: string }> {
  const res = await fetch(`${API_BASE}/api/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function respondToQuestion(sessionId: string, answers: Record<string, unknown>): Promise<void> {
  const res = await fetch(`${API_BASE}/api/respond/${sessionId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers }),
  });
  if (!res.ok) throw new Error(await res.text());
}

export async function getSettings(): Promise<import("./types").SettingsData> {
  const res = await fetch(`${API_BASE}/api/settings`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateSettings(data: Partial<import("./types").SettingsData>): Promise<import("./types").SettingsData> {
  const res = await fetch(`${API_BASE}/api/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getParameters(sessionId: string): Promise<import("./types").ParametersData> {
  const res = await fetch(`${API_BASE}/api/parameters/${sessionId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateParameters(sessionId: string, data: { genic?: Record<string, unknown>; gadget?: Record<string, unknown> }): Promise<import("./types").ParametersData> {
  const res = await fetch(`${API_BASE}/api/parameters/${sessionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function getExportUrl(sessionId: string): string {
  return `${API_BASE}/api/parameters/${sessionId}/export`;
}

export async function getSessionStatus(): Promise<{ status: string | null; session_id: string | null; messages: import("./types").Message[]; parameters: Record<string, unknown> }> {
  const res = await fetch(`${API_BASE}/api/session/status`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function getStreamUrl(sessionId: string): string {
  return `${API_BASE}/api/stream/${sessionId}`;
}
```

- [ ] **Step 3: Write SSE client**

Create: `frontend/src/lib/sse.ts`

```typescript
import type { SSEEvent } from "./types";

export function connectSSE(
  url: string,
  onEvent: (event: SSEEvent) => void,
  onClose: () => void,
  onError: (err: Event) => void,
): EventSource {
  const source = new EventSource(url);

  source.onmessage = (e) => {
    try {
      const data: SSEEvent = JSON.parse(e.data);
      onEvent(data);
    } catch {
      console.error("Failed to parse SSE event:", e.data);
    }
  };

  source.onerror = (e) => {
    source.close();
    onError(e);
  };

  // EventSource auto-closes when server ends the stream
  // We detect this via the error handler (readyState === CLOSED)

  return source;
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/
git commit -m "feat: add TypeScript types, API client, and SSE helper"
```

---

## Task 7: Frontend Layout & Sidebar

**Files:**
- Modify: `frontend/src/app/globals.css`
- Modify: `frontend/src/app/layout.tsx`
- Create: `frontend/src/components/Sidebar.tsx`
- Modify: `frontend/src/app/page.tsx`

NOTE: Use the `frontend-design` skill for this task to produce polished, high-quality UI components. The design should be dark-themed, modern, with the three-panel layout from the spec mockup.

- [ ] **Step 1: Set up globals.css with dark theme**

Replace `frontend/src/app/globals.css` with Tailwind directives and a dark theme base.

- [ ] **Step 2: Write Sidebar component**

Create: `frontend/src/components/Sidebar.tsx` — vertical icon sidebar with Chat, Parameters, Settings icons. Active state highlight. "S" logo at top.

- [ ] **Step 3: Write root layout**

Update `frontend/src/app/layout.tsx` — full-height dark background, import globals.css.

- [ ] **Step 4: Write main page with view switching**

Update `frontend/src/app/page.tsx` — manages `view` state (`"chat"` | `"settings"`), renders Sidebar + conditional content. For now, placeholder divs for ChatPanel, ParameterPanel, and SettingsView.

- [ ] **Step 5: Verify layout renders**

```bash
cd frontend && npm run dev
# Open http://localhost:3000 in browser — should see dark sidebar with icons
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: add dark theme layout with sidebar navigation"
```

---

## Task 8: Chat Panel & Message Components

**Files:**
- Create: `frontend/src/components/ChatPanel.tsx`
- Create: `frontend/src/components/MessageBubble.tsx`
- Create: `frontend/src/components/QuickReply.tsx`
- Create: `frontend/src/components/FileUpload.tsx`

NOTE: Use the `frontend-design` skill. The chat panel should follow the spec mockup: agent messages left-aligned with role avatar/label, user messages right-aligned, HITL questions with orange border and inline input.

- [ ] **Step 1: Write MessageBubble**

Agent messages (left, with role avatar and colored label) and user messages (right, purple background).

- [ ] **Step 2: Write QuickReply**

HITL question with orange border, "Input Required" label, inline text input + Send button.

- [ ] **Step 3: Write FileUpload**

Paperclip button that opens file picker. Accepts `.pdf` files only.

- [ ] **Step 4: Write ChatPanel**

Scrollable message list, input area at bottom with FileUpload button + text input + Send button. Manages message state, file upload, and sends messages via API.

- [ ] **Step 5: Integrate into page.tsx**

Replace chat placeholder with real ChatPanel component.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/
git commit -m "feat: add ChatPanel, MessageBubble, QuickReply, FileUpload components"
```

---

## Task 9: Parameter Panel

**Files:**
- Create: `frontend/src/components/ParameterPanel.tsx`

NOTE: Use the `frontend-design` skill. Three tabs (GenIC/Gadget/Sources), parameter table with name/value rows, Edit/Export buttons, status bar.

- [ ] **Step 1: Write ParameterPanel**

- Tab switching (GenIC, Gadget, Sources)
- Parameter table: name on left, monospace green value on right
- Missing params shown in red
- Edit mode: values become editable input fields
- Export button: opens ZIP download URL
- Status bar: colored dot + "N/M parameters found" + source filename

- [ ] **Step 2: Integrate into page.tsx**

Replace parameter placeholder with real ParameterPanel component.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ParameterPanel.tsx frontend/src/app/page.tsx
git commit -m "feat: add ParameterPanel with tabs, edit mode, and export"
```

---

## Task 10: Settings View

**Files:**
- Create: `frontend/src/components/SettingsView.tsx`

- [ ] **Step 1: Write SettingsView**

Form with sections:
- LLM: provider dropdown (openai/anthropic/google/ollama), model text input, temperature slider (0-2)
- RAG: pdf_loader dropdown, vector_store dropdown, chunk_size number, embedding fields
- Extraction: target_software dropdown, max_iterations number
- Paths: output_dir text input

Save button → calls `updateSettings()`. Cancel button → switches view back to chat.

- [ ] **Step 2: Integrate into page.tsx**

Wire up settings view toggle when sidebar settings icon is clicked.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SettingsView.tsx frontend/src/app/page.tsx
git commit -m "feat: add SettingsView with form for all config sections"
```

---

## Task 11: Wire Everything Together — Full E2E Flow

**Files:**
- Modify: `frontend/src/app/page.tsx` — connect all state, SSE streaming, API calls

- [ ] **Step 1: Implement full extraction flow in page.tsx**

Wire up the complete flow:
1. User uploads PDF → `uploadFile()` → gets `file_id`
2. Auto-start extraction → `startExtraction({file_id})` → gets `session_id`
3. Connect SSE → `connectSSE(getStreamUrl(session_id), ...)` → receive events
4. Agent messages → append to messages list → ChatPanel renders them
5. Parameters updates → update params state → ParameterPanel renders live
6. `needs_input` → show QuickReply in chat
7. User submits answer → `respondToQuestion()` → reconnect SSE
8. `complete` → update status
9. User can also type messages directly to start chat-mode extraction

- [ ] **Step 2: Test full flow manually**

Start both servers:
```bash
conda run -n langgraph uvicorn simagents.api.server:app --port 8000 --reload &
cd frontend && npm run dev &
```

Open http://localhost:3000, upload a PDF, verify the chat shows agent messages and parameters update live.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat: wire full E2E extraction flow — upload, stream, respond, parameters"
```

---

## Task 12: Final Polish & Cleanup

- [ ] **Step 1: Update .gitignore**

Add:
```
frontend/node_modules/
frontend/.next/
```

- [ ] **Step 2: Update README**

Add GUI section to README.md:

```markdown
## GUI

### Running the GUI

```bash
# Terminal 1: Start the backend
conda activate langgraph
pip install -e ".[gui]"
uvicorn simagents.api.server:app --port 8000 --reload

# Terminal 2: Start the frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 in your browser.
```

- [ ] **Step 3: Run full backend test suite**

```bash
conda run -n langgraph pytest tests/ -v
```

- [ ] **Step 4: Push**

```bash
git add -A
git commit -m "chore: final polish — gitignore, README, cleanup"
git push
```
