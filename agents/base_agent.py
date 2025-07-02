from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from autogen import ConversableAgent, LLMConfig


class BaseAgent(ABC):
    """Base class for all agents in the simulation system."""
    
    def __init__(
        self,
        name: str,
        system_message: str,
        llm_config: Optional[LLMConfig] = None,
        human_input_mode: str = "NEVER",
        **kwargs
    ):
        """
        Initialize a base agent.
        
        Args:
            name: Agent name
            system_message: System message for the agent
            llm_config: LLM configuration
            human_input_mode: Human input mode (NEVER, ALWAYS, TERMINATE)
            **kwargs: Additional arguments for ConversableAgent
        """
        self.name = name
        self.system_message = system_message
        self.llm_config = llm_config
        self.human_input_mode = human_input_mode
        
        self._agent = self._create_agent(**kwargs)
    
    def _create_agent(self, **kwargs) -> ConversableAgent:
        """Create the underlying ConversableAgent."""
        return ConversableAgent(
            name=self.name,
            system_message=self.system_message,
            llm_config=self.llm_config,
            human_input_mode=self.human_input_mode,
            **kwargs
        )
    
    @abstractmethod
    def setup(self) -> None:
        """Setup method to be implemented by subclasses."""
        pass
    
    @abstractmethod
    def execute(self, message: str, **kwargs) -> Any:
        """Execute method to be implemented by subclasses."""
        pass
    
    @property
    def agent(self) -> ConversableAgent:
        """Get the underlying ConversableAgent."""
        return self._agent


class ExecutorAgent(BaseAgent):
    """Base class for executor agents."""
    
    def __init__(
        self,
        name: str,
        executor,
        work_dir: str,
        timeout: int = 120,
        **kwargs
    ):
        """
        Initialize an executor agent.
        
        Args:
            name: Agent name
            executor: Code executor instance
            work_dir: Working directory
            timeout: Execution timeout in seconds
            **kwargs: Additional arguments
        """
        self.executor = executor
        self.work_dir = work_dir
        self.timeout = timeout
        
        super().__init__(
            name=name,
            system_message="",
            llm_config=False,
            code_execution_config={"executor": executor},
            **kwargs
        )
    
    def setup(self) -> None:
        """Setup the executor agent."""
        pass
    
    def execute(self, message: str, target_agent=None) -> Any:
        """Execute code through the executor."""
        if target_agent:
            return self.agent.initiate_chat(target_agent, message=message)
        return None