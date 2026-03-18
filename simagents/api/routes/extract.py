"""Extraction routes — start, stream, respond."""
from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from simagents.api.session import session_manager
from simagents.api.routes.upload import get_upload_path
from simagents.config.settings import Settings
from simagents.graph.parameter_extraction import create_extraction_graph

router = APIRouter()
CONFIG_PATH = os.environ.get("SIMAGENTS_CONFIG", str(Path(__file__).resolve().parents[3] / "config.yaml"))


class ExtractRequest(BaseModel):
    file_id: str | None = None
    user_parameters: dict | None = None
    target_software: str | None = None
    custom_prompt: str | None = None


@router.post("/api/extract")
async def start_extraction(req: ExtractRequest):
    """Return session_id immediately. Heavy work (retrievers, LLM) deferred to stream."""
    settings = Settings.from_yaml(CONFIG_PATH)
    target = req.target_software or settings.extraction.target_software

    file_path = None
    if req.file_id:
        file_path_obj = get_upload_path(req.file_id)
        if not file_path_obj:
            raise HTTPException(status_code=404, detail="Uploaded file not found")
        file_path = str(file_path_obj)

    # Create a lightweight session — no LLM or retriever building yet
    session_id = session_manager.create_session(graph=None, config={}, file_path=file_path)
    session = session_manager.get_session(session_id)
    session.status = "running"

    # Store request params for deferred setup in _stream_events
    session._extract_request = {
        "file_path": file_path,
        "target_software": target,
        "custom_prompt": req.custom_prompt,
        "user_parameters": req.user_parameters,
        "settings": settings,
    }

    return {"session_id": session_id}


def _build_graph_and_config(session):
    """Build LLM, retrievers, and graph. Called from stream (blocking is OK there)."""
    from langchain.chat_models import init_chat_model
    from langgraph.checkpoint.memory import MemorySaver
    from simagents.tools.pdf_loader import build_paper_retriever
    from simagents.tools.docs_loader import build_docs_retriever

    req = session._extract_request
    settings = req["settings"]
    target = req["target_software"]

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
    if req["file_path"]:
        paper_retriever = build_paper_retriever(req["file_path"], settings.rag)

    docs_retriever = build_docs_retriever(target, settings.rag, settings.paths.software_docs_dir)

    # Build graph
    graph = create_extraction_graph(settings, checkpointer=MemorySaver())

    session.graph = graph
    session.config = {
        "configurable": {
            "llm": llm,
            "paper_retriever": paper_retriever,
            "docs_retriever": docs_retriever,
            "output_dir": settings.paths.output_dir,
            "thread_id": "gui-session",
        }
    }
    session._initial_state = {
        "paper_path": req["file_path"],
        "user_parameters": req["user_parameters"],
        "target_software": target,
        "custom_prompt": req["custom_prompt"],
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


async def _stream_events(session) -> AsyncGenerator[dict, None]:
    """Stream LangGraph execution as SSE events."""
    try:
        # Deferred setup: build retrievers and graph (heavy, blocking)
        if not session.graph:
            yield {"event": "message", "data": json.dumps({"type": "status", "message": "Loading paper and building indexes..."})}
            await asyncio.to_thread(_build_graph_and_config, session)
            yield {"event": "message", "data": json.dumps({"type": "status", "message": "Starting extraction..."})}

        # Determine if this is a resume or initial run
        if hasattr(session, "_resume_value") and session._resume_value is not None:
            from langgraph.types import Command
            input_val = Command(resume=session._resume_value)
            session._resume_value = None
        else:
            input_val = session._initial_state

        async for event in session.graph.astream(input_val, config=session.config):
            if "parse_input" in event:
                yield {"event": "message", "data": json.dumps({"type": "status", "message": f"Mode: {event['parse_input'].get('input_mode', 'unknown')}"})}
            elif "physics_expert" in event:
                data = event["physics_expert"]
                msg = {"type": "agent_message", "role": "physics_expert", "content": data.get("raw_parameters", "")}
                session.messages.append(msg)
                yield {"event": "message", "data": json.dumps(msg)}
            elif "formatter" in event:
                data = event["formatter"]
                fmt = data.get("formatted_parameters", {})
                msg = {"type": "agent_message", "role": "formatter", "content": fmt.get("comment", "")}
                session.messages.append(msg)
                yield {"event": "message", "data": json.dumps(msg)}
                params = {
                    "genic": fmt.get("genic", {}),
                    "gadget": fmt.get("gadget", {}),
                    "status": data.get("status", "incomplete"),
                    "missing": data.get("missing_parameters", []),
                    "sources": fmt.get("sources", []),
                }
                session.parameters = params
                yield {"event": "message", "data": json.dumps({"type": "parameters_update", "data": params})}
                if data.get("user_questions") or data.get("status") == "needs_user_input":
                    session.status = "waiting_input"
                    yield {"event": "message", "data": json.dumps({"type": "needs_input", "questions": data.get("user_questions", []), "missing": data.get("missing_parameters", [])})}
            elif "save_output" in event:
                session.status = "complete"
                yield {"event": "message", "data": json.dumps({"type": "complete", "status": event["save_output"].get("status", "complete")})}
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
    session._resume_value = req.answers if req.answers else {"raw_response": req.raw_response}
    session.status = "running"
    return {"status": "resumed"}


@router.get("/api/session/status")
async def session_status():
    session = session_manager.get_current()
    if not session:
        return {"status": None, "session_id": None}
    return {"status": session.status, "session_id": session.session_id, "messages": session.messages, "parameters": session.parameters}
