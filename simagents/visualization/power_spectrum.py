"""Standalone power spectrum plotter — model-agnostic, no ag2 dependency."""
from __future__ import annotations
import subprocess
import tempfile
import re
from pathlib import Path
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from simagents.config.settings import Settings

SYSTEM_PROMPT = """You are a scientific visualization expert. Generate a complete, self-contained Python script
that creates a power spectrum plot from MP-Gadget simulation output.

Requirements:
- Use matplotlib for plotting
- Use loglog scale for both axes
- Label axes: k [h/Mpc] and P(k) [(Mpc/h)^3]
- Calculate redshift from scale factor: z = 1/a - 1
- Create publication-quality plots with legends
- Save the plot to the specified output path
- The script must be fully self-contained (all imports included)
"""


class PowerSpectrumPlotter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = init_chat_model(model=settings.llm.model, model_provider=settings.llm.provider, temperature=settings.llm.temperature)

    def plot(self, output_dir: str, output_filename: str = "power_spectrum.png") -> str:
        output_path = Path(output_dir)
        ps_files = sorted(output_path.glob("powerspectrum-*.txt"))
        if not ps_files:
            raise FileNotFoundError(f"No powerspectrum-*.txt files in {output_dir}")
        snapshots_info = ""
        snapshots_file = output_path / "Snapshots.txt"
        if snapshots_file.exists():
            snapshots_info = f"Snapshots.txt content:\n{snapshots_file.read_text()}\n"
        file_list = "\n".join(str(f) for f in ps_files[:20])
        save_path = str(output_path / output_filename)
        user_msg = f"Create a power spectrum plot from these files:\n{file_list}\n\n{snapshots_info}\nSave the plot to: {save_path}"
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
            raise RuntimeError(f"Plot script failed:\n{result.stderr}")
        return script_path
