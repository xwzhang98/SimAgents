"""File upload route."""
from __future__ import annotations
import shutil
import tempfile
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter()
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
