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
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=parameters.zip"})
