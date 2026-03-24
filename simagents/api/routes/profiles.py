"""Profiles routes — list and get software profiles."""
from __future__ import annotations
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from simagents.profiles import load_profile, list_profiles
from simagents.config.settings import Settings

router = APIRouter()
CONFIG_PATH = os.environ.get("SIMAGENTS_CONFIG", str(Path(__file__).resolve().parents[3] / "config.yaml"))


@router.get("/api/profiles")
async def get_profiles():
    settings = Settings.from_yaml(CONFIG_PATH)
    return list_profiles(settings.paths.software_profiles_dir)


@router.get("/api/profiles/{software}")
async def get_profile(software: str):
    settings = Settings.from_yaml(CONFIG_PATH)
    try:
        p = load_profile(software, settings.paths.software_profiles_dir)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "slug": p.slug,
        "name": p.name,
        "description": p.description,
        "family": p.family,
        "output_format": p.output_format,
        "sections": [{"name": s.name, "description": s.description} for s in p.output_sections],
        "units": p.units,
        "ic_generator": p.ic_generator,
        "ic_note": p.ic_note,
        "parameter_names": p.parameter_names,
    }
