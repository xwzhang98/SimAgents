"""Settings routes — read/write config.yaml."""
from __future__ import annotations
import os
from pathlib import Path
from fastapi import APIRouter
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
