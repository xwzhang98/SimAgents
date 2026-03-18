"""File utility functions."""
from __future__ import annotations
import json
from pathlib import Path


def read_json(path: str | Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def write_json(data: dict, path: str | Path, indent: int = 2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=indent)
