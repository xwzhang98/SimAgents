"""Standalone density field plotter — model-agnostic, no ag2 dependency."""
from __future__ import annotations
import subprocess
import tempfile
import re
from pathlib import Path
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from simagents.config.settings import Settings

SYSTEM_PROMPT = """You are a gaepsi2 visualization expert. Generate a complete Python script
for creating 3D density field plots from MP-Gadget simulation data.

Key components:
- BigFile for loading PART_* particle data
- gaepsi2.camera for 3D transformations
- gaepsi2.painter.paint for rendering density fields
- matplotlib for final plots

The script must be fully self-contained and executable.
"""


class DensityFieldPlotter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = init_chat_model(model=settings.llm.model, model_provider=settings.llm.provider, temperature=settings.llm.temperature)

    def plot(self, simulation_dir: str, snapshot: str = "PART_000", particle_type: int = 1, output_filename: str = "density_field.png") -> str:
        sim_path = Path(simulation_dir)
        save_path = str(sim_path / output_filename)
        user_msg = f"Create a 3D density field visualization from:\n- Simulation directory: {simulation_dir}\n- Snapshot: {snapshot}\n- Particle type: {particle_type} ({'dark matter' if particle_type == 1 else 'gas'})\n- Save to: {save_path}\n"
        response = self.llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_msg)])
        code = self._extract_code(response.content)
        return self._execute_code(code)

    def _extract_code(self, text: str) -> str:
        match = re.search(r"```python\s*(.*?)```", text, re.DOTALL)
        return match.group(1) if match else text

    def _execute_code(self, code: str) -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            script_path = f.name
        result = subprocess.run(["python", script_path], capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"Density field script failed:\n{result.stderr}")
        return script_path
