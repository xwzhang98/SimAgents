"""Software profile loader — reads profile.yaml and validates with Pydantic."""
from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel
import yaml


class OutputSection(BaseModel):
    name: str
    description: str = ""
    filename_template: str = "{paper}_{name}.json"
    native_template: str | None = None


class SoftwareProfile(BaseModel):
    slug: str
    name: str
    description: str = ""
    family: str  # gadget | swift | enzo
    output_format: str = "key-value"  # key-value | yaml | ini
    output_sections: list[OutputSection]
    comment_prefix: str = "#"
    units: dict[str, str] = {}
    ic_generator: str = "none"  # builtin | external | none
    ic_note: str = ""
    parameter_names: dict[str, str] = {}  # canonical -> software-specific
    docs_dir: Path
    templates_dir: Path
    profile_dir: Path

    model_config = {"arbitrary_types_allowed": True}


def load_profile(software_name: str, profiles_dir: str = "data/software_profiles") -> SoftwareProfile:
    profile_path = Path(profiles_dir) / software_name
    yaml_path = profile_path / "profile.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"No profile found for '{software_name}' at {yaml_path}")
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)
    if not data:
        raise ValueError(f"Empty profile.yaml for '{software_name}'")
    docs_dir = profile_path / "docs"
    if not docs_dir.exists() or not any(docs_dir.glob("*.md")):
        raise FileNotFoundError(f"No docs found for '{software_name}' at {docs_dir}")
    output = data.get("output", {})
    sections = [
        OutputSection(
            name=s["name"],
            description=s.get("description", ""),
            filename_template=s.get("filename_template", f"{{paper}}_{s['name']}.json"),
            native_template=s.get("native_template"),
        )
        for s in output.get("sections", [])
    ]
    return SoftwareProfile(
        slug=software_name,
        name=data.get("name", software_name),
        description=data.get("description", ""),
        family=data.get("family", "unknown"),
        output_format=output.get("format", "key-value"),
        output_sections=sections,
        comment_prefix=output.get("comment_prefix", "#"),
        units=data.get("units", {}),
        ic_generator=data.get("ic_generator", "none"),
        ic_note=data.get("ic_note", ""),
        parameter_names=data.get("parameter_names", {}),
        docs_dir=docs_dir,
        templates_dir=profile_path / "templates",
        profile_dir=profile_path,
    )


def list_profiles(profiles_dir: str = "data/software_profiles") -> list[dict]:
    profiles = []
    base = Path(profiles_dir)
    if not base.exists():
        return profiles
    for d in sorted(base.iterdir()):
        if d.is_dir() and (d / "profile.yaml").exists():
            try:
                p = load_profile(d.name, profiles_dir)
                profiles.append({
                    "slug": p.slug,
                    "name": p.name,
                    "description": p.description,
                    "family": p.family,
                    "ic_generator": p.ic_generator,
                })
            except (FileNotFoundError, ValueError):
                pass
    return profiles
