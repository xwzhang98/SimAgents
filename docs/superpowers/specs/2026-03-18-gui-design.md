# SimAgents GUI — Design Spec

## Overview

A local-first web GUI for the SimAgents parameter extraction system. Daily research tool for extracting simulation parameters from papers via a chat interface with live parameter updates.

**Stack:** Next.js (React + Tailwind CSS) frontend + FastAPI backend with SSE streaming.

---

## 1. Architecture

```
Browser (localhost:3000)              FastAPI (localhost:8000)
┌──────┬────────────┬──────────┐     ┌──────────────────────┐
│Sidebar│ Chat Panel │ Params   │     │ simagents.api.server │
│      │            │ Panel    │────▶│                      │
│ 💬📄⚙️│ SSE ←──────│          │     │ Routes:              │
│      │ POST ─────▶│          │     │  /api/extract        │
└──────┴────────────┴──────────┘     │  /api/stream/{id}    │
                                      │  /api/respond/{id}   │
                                      │  /api/upload         │
                                      │  /api/settings       │
                                      │  /api/parameters/{id}│
                                      │                      │
                                      │ Uses: simagents pkg  │
                                      └──────────────────────┘
```

Two processes:
- `cd frontend && npm run dev` → Next.js on port 3000
- `uvicorn simagents.api.server:app` → FastAPI on port 8000

Local-first (single user, sessions in memory), but structured for future deployment.

CORS: FastAPI middleware allows `http://localhost:3000` origin.

---

## 2. Layout

Three-panel layout with icon sidebar navigation:

- **Sidebar (left, 60px):** Vertical icon navigation — Chat (default), Parameters (full-page view), Settings. Active state indicated by highlight. App logo at top.
- **Chat Panel (center, flex:3):** Conversation thread with agent messages, user messages, file upload. Header shows extraction status.
- **Parameters Panel (right, flex:2):** Live parameter table with GenIC/Gadget/Sources tabs. Edit/Export buttons. Status bar showing parameter count and source file.

### Chat Panel Details
- Agent messages: left-aligned with role avatar and colored label (Physics Expert = green, Formatter = purple)
- User messages: right-aligned, purple background
- Human-in-the-loop questions: visually distinct with orange border, role label "Input Required", inline text input + Send button embedded in the message bubble
- Chat input at bottom: text field + paperclip icon for PDF upload + Send button
- Drag-and-drop PDF upload supported

### Parameters Panel Details
- Three tabs: GenIC, Gadget, Sources
- Each parameter shown as a row: name (left) + value (right, monospace, green)
- Missing parameters shown in red
- Edit mode: clicking "Edit" makes values editable inline
- Export button: downloads a ZIP containing genic.json + gadget.json (single download)
- Status bar: colored dot (green=complete, orange=in-progress, red=missing) + "7/8 parameters found" + source filename

### Settings View
- Rendered as conditional content in `page.tsx` (NOT a separate Next.js route) — clicking the settings icon swaps the center+right panels for the settings form, clicking back or cancel restores chat+params
- Sections: LLM (provider dropdown, model text, temperature slider), RAG (PDF loader, vector store, chunk size, embedding), Extraction (target software, max iterations), Paths (output dir)
- Save button persists to `config.yaml` via `PUT /api/settings` (requires `Settings.to_yaml()` method — must be added to `settings.py`)
- Cancel returns to chat view

---

## 3. API Endpoints

### `POST /api/upload`
Upload a PDF paper.
- Request: multipart file upload
- Response: `{"file_id": "uuid", "filename": "paper.pdf"}`
- Files stored in temp directory

### `POST /api/extract`
Start a parameter extraction.
- Request: `{"file_id": "uuid" | null, "user_parameters": {} | null, "target_software": "mp-gadget", "custom_prompt": null}`
- `target_software` in the request overrides the value from `config.yaml`. If omitted, uses `settings.extraction.target_software`.
- Response: `{"session_id": "uuid"}`
- Backend: replaces any existing session (one active session at a time), then:
  1. Loads `Settings` from `config.yaml`
  2. Builds LLM via `init_chat_model(settings.llm.model, model_provider=settings.llm.provider, ...)`
  3. Builds `paper_retriever` via `build_paper_retriever(file_path, settings.rag)` if PDF provided
  4. Builds `docs_retriever` via `build_docs_retriever(target_software, settings.rag, settings.paths.software_docs_dir)`
  5. Creates graph via `create_extraction_graph(settings, checkpointer=MemorySaver())`
  6. Passes `llm`, `paper_retriever`, `docs_retriever`, `output_dir`, `thread_id` via the `configurable` dict
  7. Starts graph execution in a background async task

### `GET /api/stream/{session_id}`
SSE stream of extraction events.
- Events:
  - `{"type": "agent_message", "role": "physics_expert"|"formatter", "content": "..."}`
  - `{"type": "parameters_update", "data": {"genic": {...}, "gadget": {...}, "status": "...", "missing": [...]}}`
  - `{"type": "needs_input", "questions": [...], "missing": [...]}`
  - `{"type": "complete", "status": "complete"|"incomplete"}`
  - `{"type": "error", "message": "..."}`

### `POST /api/respond/{session_id}`
Answer a human-in-the-loop question.
- Request: `{"answers": {"Seed": 42}}` or `{"raw_response": "Use Seed = 42"}`
- Response: `{"status": "resumed"}`
- Backend: resumes the graph with user input

### `GET /api/settings`
Read current settings.
- Response: full Settings object as JSON

### `PUT /api/settings`
Update settings.
- Request: partial or full settings JSON
- Response: updated Settings object
- Side effect: writes to `config.yaml`

### `GET /api/parameters/{session_id}`
Get current extraction parameters.
- Response: `{"genic": {...}, "gadget": {...}, "status": "...", "missing": [...], "sources": [...]}`

### `PUT /api/parameters/{session_id}`
Edit parameters manually.
- Request: `{"genic": {...}, "gadget": {...}}`
- Response: updated parameters

### `GET /api/parameters/{session_id}/export`
Download parameter files.
- Response: ZIP containing `*_genic.json` + `*_gadget.json`

---

## 4. Backend Session Management

```python
# simagents/api/session.py
class ExtractionSession:
    session_id: str
    graph: CompiledGraph        # The LangGraph instance
    config: dict                # LangGraph configurable (llm, retrievers, etc.)
    parameters: dict            # Current extracted parameters
    messages: list[dict]        # Chat message history
    status: str                 # "idle" | "running" | "waiting_input" | "complete"
    file_path: str | None       # Uploaded PDF path

class SessionManager:
    sessions: dict[str, ExtractionSession]

    def create_session(...) -> str: ...
    def get_session(session_id) -> ExtractionSession: ...
    def run_extraction(session_id) -> AsyncGenerator[dict]: ...  # yields SSE events
    def resume_with_input(session_id, answers) -> None: ...
```

### Session lifecycle
- **One active session at a time.** Starting a new extraction replaces the previous session.
- Uploaded temp files are cleaned up when the session is replaced or the server shuts down.
- Sessions live in memory. Single-user local tool — no database, no auth.
- If the user uploads a new PDF while an extraction is running, the current extraction is cancelled and a new session starts.

### Additional endpoint
- `GET /api/session/status` — returns current session state (`idle`, `running`, `waiting_input`, `complete`, or `null` if no session). Frontend calls this on page load to restore state after browser refresh.

---

## 5. SSE Streaming Implementation

### Streaming API choice

Use LangGraph's `astream()` (node-level granularity). Each yield is a dict keyed by node name (e.g., `{"physics_expert": {"raw_parameters": "..."}}`). This is simpler than `astream_events()` (token-level) and sufficient for this UI — the user sees one message per agent step, not token-by-token streaming.

### Node-to-SSE event mapping

The graph has 5 nodes: `parse_input`, `physics_expert`, `formatter`, `ask_user`, `save_output`. Note: `check_done` is a conditional edge router, NOT a node — it never appears in `astream()` output.

```python
async def stream_extraction(session: ExtractionSession):
    """Generator that yields SSE events from graph execution."""
    async for event in session.graph.astream(state, config=session.config):
        if "parse_input" in event:
            yield {"type": "status", "message": f"Mode: {event['parse_input']['input_mode']}"}
        elif "physics_expert" in event:
            data = event["physics_expert"]
            yield {"type": "agent_message", "role": "physics_expert", "content": data["raw_parameters"]}
        elif "formatter" in event:
            data = event["formatter"]
            yield {"type": "agent_message", "role": "formatter", "content": data.get("formatted_parameters", {}).get("comment", "")}
            # Assemble parameters_update from multiple state fields
            yield {"type": "parameters_update", "data": {
                "genic": data.get("formatted_parameters", {}).get("genic", {}),
                "gadget": data.get("formatted_parameters", {}).get("gadget", {}),
                "status": data.get("status", "incomplete"),
                "missing": data.get("missing_parameters", []),
                "sources": data.get("formatted_parameters", {}).get("sources", []),
            }}
            # Check if human input is needed (from state, not from check_done)
            if data.get("status") == "needs_user_input" or data.get("user_questions"):
                yield {"type": "needs_input", "questions": data.get("user_questions", []), "missing": data.get("missing_parameters", [])}
        elif "save_output" in event:
            yield {"type": "complete", "status": event["save_output"].get("status", "complete")}
    # If graph ended without save_output (e.g., interrupt), stream ends naturally
```

### Interrupt/resume flow

When the graph hits `interrupt()` in `ask_user`, `astream()` ends (the generator completes). The SSE stream closes. The flow is:

1. SSE stream sends `needs_input` event, then closes
2. Frontend displays the HITL question with inline input
3. User submits answer → `POST /api/respond/{session_id}` with answers
4. Backend calls `graph.invoke(Command(resume=answers), config=session.config)` wrapped in a new `astream()` call
5. Frontend reconnects to `GET /api/stream/{session_id}` to receive resumed events

The frontend's SSE handler must detect stream close and, if the last event was `needs_input`, show the input UI and wait. After posting the response, it reconnects to the same SSE endpoint.

### Frontend SSE client

Use native `EventSource` API (sufficient since the SSE endpoint is a simple GET with no auth). The `sse.ts` helper wraps `EventSource` with:
- Auto-reconnect with exponential backoff (only after unexpected disconnects, not after `needs_input`)
- Event type dispatching to React state updates

---

## 6. Frontend Components

| Component | Responsibility |
|---|---|
| `Sidebar.tsx` | Icon navigation, active state, app logo |
| `ChatPanel.tsx` | Message list, scroll management, input area |
| `MessageBubble.tsx` | Single message: agent (left) or user (right) |
| `QuickReply.tsx` | HITL question with orange border + inline input |
| `ParameterPanel.tsx` | Tabs, parameter table, edit mode, export |
| `FileUpload.tsx` | Drag-drop zone + paperclip button |
| `SettingsView.tsx` | Settings form with save/cancel (conditional render, not a route) |

---

## 7. Project Structure

```
SimAgents/
├── simagents/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py           # FastAPI app, CORS, mount routes
│   │   ├── session.py          # ExtractionSession, SessionManager
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── extract.py      # /api/extract, /api/stream, /api/respond
│   │       ├── upload.py       # /api/upload
│   │       ├── settings.py     # /api/settings
│   │       └── parameters.py   # /api/parameters
│   └── ... (existing package)
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx      # Root layout with sidebar
│   │   │   └── page.tsx        # Main page: conditionally renders chat+params or settings
│   │   ├── components/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── QuickReply.tsx
│   │   │   ├── ParameterPanel.tsx
│   │   │   ├── FileUpload.tsx
│   │   │   └── SettingsView.tsx  # Rendered conditionally in page.tsx, NOT a separate route
│   │   └── lib/
│   │       ├── api.ts          # Typed API client (fetch wrappers)
│   │       └── sse.ts          # EventSource wrapper, event dispatching
│   └── public/
└── ...
```

---

## 8. Error Handling

- **PDF upload failure:** Toast notification with error message
- **LLM API failure:** Error event in SSE stream → displayed as red message in chat
- **SSE connection lost:** Auto-reconnect with exponential backoff, "Reconnecting..." indicator
- **Settings validation failure:** Inline form errors (red text under invalid fields)
- **Backend not running:** Frontend shows "Cannot connect to backend. Is `uvicorn` running?" banner

---

## 9. Dependencies

### Backend (additions to existing)
```
fastapi>=0.104.0
uvicorn>=0.24.0
python-multipart>=0.0.6   # file upload
sse-starlette>=1.6.0       # SSE support
```

### Frontend
```
next >= 14.0
react >= 18.0
tailwindcss >= 3.0
typescript >= 5.0
```
