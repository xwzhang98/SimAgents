import os
from dataclasses import dataclass
from typing import Dict, Any, Optional
from autogen import LLMConfig


@dataclass
class LLMSettings:
    """LLM configuration settings."""
    api_type: str = "openai"
    model: str = "gpt-4o"
    temperature: float = 0.01
    top_p: float = 0.9
    api_key: Optional[str] = None
    
    def to_llm_config(self) -> LLMConfig:
        """Convert to autogen LLMConfig."""
        api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
        return LLMConfig(
            api_type=self.api_type,
            model=self.model,
            temperature=self.temperature,
            top_p=self.top_p,
            api_key=api_key
        )


@dataclass
class SLURMSettings:
    """SLURM configuration settings."""
    default_partition: str = "RM"
    default_email: str = "xiaowen4@andrew.cmu.edu"
    default_nodes: int = 1
    default_ntasks: int = 2
    default_cpus_per_task: int = 14
    default_time: str = "16:00:00"
    default_mem_per_cpu: str = "8G"
    mp_gadget_root: str = "/hildafs/projects/phy200018p/xzhangn/source/MP-Gadget"


@dataclass
class PathSettings:
    """File path settings."""
    camb_data_path: str = "/hildafs/home/xzhangn/xzhangn/LLM/5-multiagent/cmbagent_data/data/camb/"
    default_output_base: str = "/hildafs/home/xzhangn/xzhangn/LLM/5-multiagent/output/"
    temp_dir_base: str = "/hildafs/home/xzhangn/xzhangn/LLM/5-multiagent/temp_dir"
    sr_code_path: str = "/hildafs/home/xzhangn/xzhangn/LLM/5-multiagent/sr_code/"


@dataclass
class AgentSettings:
    """Agent-specific settings."""
    executor_timeout: int = 120
    human_input_mode: str = "ALWAYS"
    density_field_vector_store_id: str = "vs_682cacef802c81919d54918a7d9c9b42"


@dataclass
class SimAgentConfig:
    """Main configuration class."""
    llm: LLMSettings = None
    slurm: SLURMSettings = None
    paths: PathSettings = None
    agents: AgentSettings = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.llm is None:
            self.llm = LLMSettings()
        if self.slurm is None:
            self.slurm = SLURMSettings()
        if self.paths is None:
            self.paths = PathSettings()
        if self.agents is None:
            self.agents = AgentSettings()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'SimAgentConfig':
        """Create config from dictionary."""
        return cls(
            llm=LLMSettings(**config_dict.get('llm', {})),
            slurm=SLURMSettings(**config_dict.get('slurm', {})),
            paths=PathSettings(**config_dict.get('paths', {})),
            agents=AgentSettings(**config_dict.get('agents', {}))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'llm': self.llm.__dict__,
            'slurm': self.slurm.__dict__,
            'paths': self.paths.__dict__,
            'agents': self.agents.__dict__
        }