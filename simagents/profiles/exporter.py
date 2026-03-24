"""Native param file export via Jinja2 templates."""
from __future__ import annotations
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from simagents.profiles.loader import SoftwareProfile


def export_native(profile: SoftwareProfile, sections: dict, paper_name: str) -> dict[str, str]:
    """Render native param files from Jinja2 templates.
    Returns: {filename: rendered_content} dict. Empty if no templates exist.
    """
    if not profile.templates_dir.exists():
        return {}
    env = Environment(loader=FileSystemLoader(str(profile.templates_dir)), keep_trailing_newline=True)
    results = {}
    for section in profile.output_sections:
        if not section.native_template:
            continue
        template_path = profile.templates_dir / section.native_template
        if not template_path.exists():
            continue
        template = env.get_template(section.native_template)
        rendered = template.render(
            sections=sections,
            section=sections.get(section.name, {}),
            paper=paper_name,
            source=paper_name,
            profile=profile,
        )
        # Generate native filename
        native_ext = ".yml" if profile.output_format == "yaml" else ".txt"
        filename = f"{paper_name}_{section.name}{native_ext}"
        results[filename] = rendered
    return results
