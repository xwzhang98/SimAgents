from typing import Optional, Any
from autogen import LLMConfig
from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent
from agents.base_agent import BaseAgent


GAEPSI2_INSTRUCTIONS = """
# === role_prompt: RAG-Code-Snippet-Agent ===
Role
• You search local gaepsi2 source files **and** propose runnable Python code
  that sets up and plots a 3D density field (SPH-style) with gaepsi2.

Mission (do all five)
1. **Retrieve**: locate the most relevant functions/classes in gaepsi2
   (e.g. `painter.paint`, `camera.data_to_device`, `color.Colormap`).
2. **Extract**: copy their docstrings *verbatim* and highlight units,
   array shapes, and return types.
3. **Summarise** each item in 40 words (purpose + key params).
4. **Compose** a minimal, self-contained Python snippet (≤ 100 lines)
   that demonstrates a working density-plot pipeline.  
    Use only numpy + matplotlib beyond gaepsi2.   
    The code must `import` without NameErrors.
5. **Return** the output must be a self-contained Python script
"""


class DensityFieldAgent(BaseAgent):
    """Agent for creating density field visualizations using gaepsi2."""
    
    def __init__(
        self,
        name: str = "density_field_agent",
        llm_config: Optional[LLMConfig] = None,
        vector_store_id: str = "vs_682cacef802c81919d54918a7d9c9b42",
        **kwargs
    ):
        """
        Initialize density field agent.
        
        Args:
            name: Agent name
            llm_config: LLM configuration
            vector_store_id: Vector store ID for file search
            **kwargs: Additional arguments
        """
        self.name = name
        self.vector_store_id = vector_store_id
        self.llm_config = llm_config
        
        if llm_config is None:
            raise ValueError("llm_config is required for DensityFieldAgent")
        
        # For GPTAssistantAgent, we don't use the base class constructor
        self._setup_gpt_assistant()
    
    def _setup_gpt_assistant(self):
        """Setup the GPT Assistant agent."""
        assistant_config = {
            "assistant_id": None,
            "tools": [{"type": "file_search"}],
            "tool_resources": {
                "file_search": {
                    "vector_store_ids": [self.vector_store_id],
                }
            },
        }
        
        self._agent = GPTAssistantAgent(
            name="assistant",
            instructions=GAEPSI2_INSTRUCTIONS,
            llm_config=self.llm_config,
            assistant_config=assistant_config,
        )
        self._agent.llm_config["check_every_ms"] = 1000
    
    def setup(self) -> None:
        """Setup method (already done in __init__)."""
        pass
    
    def execute(self, message: str, executor_agent) -> Any:
        """
        Create density field visualization.
        
        Args:
            message: Message containing visualization request
            executor_agent: Executor agent to run the code
            
        Returns:
            Chat result
        """
        return executor_agent.initiate_chat(self._agent, message=message)
    
    def create_density_field_message(
        self,
        lr_snapshot_path: str,
        sr_snapshot_path: str = None,
        output_filename: str = "density_field.png",
        side_by_side: bool = False
    ) -> str:
        """
        Create a message for density field plotting.
        
        Args:
            lr_snapshot_path: Path to low-resolution snapshot
            sr_snapshot_path: Path to super-resolution snapshot
            output_filename: Output file name
            side_by_side: Whether to create side-by-side comparison
            
        Returns:
            Message string
        """
        if sr_snapshot_path and side_by_side:
            return f"""
Write Python code (using the bigfile and gaepsi2 libraries) that loads the snapshots located at
{lr_snapshot_path} and {sr_snapshot_path}, computes a 3-D density field for each snapshot with the full simulation volume and constant smoothing length, put the center at the center of the box, and saves the plot as {output_filename}. You have 2 subplots, one for the lr snapshot and one for the sr snapshot. Put them side by side. Make sure the background is black and label the redshift on the plot.
"""
        elif sr_snapshot_path:
            return f"""
Write Python code (using the bigfile and gaepsi2 libraries) that loads the snapshot located at
{lr_snapshot_path} and {sr_snapshot_path}, computes a 3-D density field for the full simulation volume with constant smoothing length, put the center at the center of the box, and saves the plot as {output_filename}. Make sure the background is black and label the redshift on the plot.
"""
        else:
            return f"""
Write Python code (using the bigfile and gaepsi2 libraries) that loads the snapshot located at
{lr_snapshot_path} (redshift = 0), computes a 3-D density field for the full simulation volume, and saves the plot as {output_filename}.
"""
    
    @property
    def agent(self):
        """Get the underlying agent."""
        return self._agent