"""Parameters routes — read/edit/export extracted parameters."""
from __future__ import annotations
import io
import json
import zipfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from simagents.api.session import session_manager
from simagents.profiles import export_native

router = APIRouter()


@router.get("/api/parameters/{session_id}")
async def get_parameters(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "sections": session.parameters.get("sections", {}),
        "ic_notes": session.parameters.get("ic_notes", []),
        "status": session.status,
        "missing": session.parameters.get("missing", []),
        "sources": session.parameters.get("sources", []),
    }


@router.put("/api/parameters/{session_id}")
async def update_parameters(session_id: str, data: dict):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if "sections" in data:
        existing = session.parameters.get("sections", {})
        for section_name, params in data["sections"].items():
            if section_name in existing:
                existing[section_name].update(params)
            else:
                existing[section_name] = params
        session.parameters["sections"] = existing
    return await get_parameters(session_id)


@router.get("/api/parameters/{session_id}/export")
async def export_parameters(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    sections = session.parameters.get("sections", {})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Write each section as a JSON file
        for section_name, params in sections.items():
            zf.writestr(f"{section_name}.json", json.dumps(params, indent=2))
        # Write native param files if profile is available
        req = getattr(session, "_extract_request", None)
        if req and "profile" in req:
            profile = req["profile"]
            paper_name = "extraction"
            if req.get("file_path"):
                from pathlib import Path
                paper_name = Path(req["file_path"]).stem
            native_files = export_native(profile, sections, paper_name)
            for filename, content in native_files.items():
                zf.writestr(filename, content)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=parameters.zip"})
