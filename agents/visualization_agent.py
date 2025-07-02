from typing import Optional, Any
from autogen import LLMConfig
from agents.base_agent import BaseAgent


VISUALIZATION_SYSTEM_MESSAGE = """
You are a helpful AI assistant.
Solve tasks using your coding and language skills.
You suggest codes to help physicists plot power spectrum based on files in a directory, make sure you use the correct scale for each axis and label the redshift on the plot.
In the following cases, suggest python code (in a python coding block) for the user to execute.
1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
Reply 'TERMINATE' in the end when everything is done.
"""


class VisualizationAgent(BaseAgent):
    """Agent for creating visualizations."""
    
    def __init__(
        self,
        name: str = "visualization_agent",
        llm_config: Optional[LLMConfig] = None,
        **kwargs
    ):
        """
        Initialize visualization agent.
        
        Args:
            name: Agent name
            llm_config: LLM configuration
            **kwargs: Additional arguments
        """
        super().__init__(
            name=name,
            system_message=VISUALIZATION_SYSTEM_MESSAGE,
            llm_config=llm_config,
            **kwargs
        )
    
    def setup(self) -> None:
        """Setup the visualization agent."""
        pass
    
    def execute(self, message: str, executor_agent) -> Any:
        """
        Create visualization.
        
        Args:
            message: Message containing visualization request
            executor_agent: Executor agent to run the code
            
        Returns:
            Chat result
        """
        return executor_agent.initiate_chat(self.agent, message=message)
    
    def create_power_spectrum_message(
        self,
        output_dir: str,
        redshift: float = 0,
        output_filename: str = "pspec.png"
    ) -> str:
        """
        Create a message for power spectrum plotting.
        
        Args:
            output_dir: Directory containing simulation output
            redshift: Redshift to plot
            output_filename: Output file name
            
        Returns:
            Message string
        """
        return f"""I would like to plot power spectrum at redshifts {redshift}, using power spectrum file in this folder:
{output_dir}/sim_output/
The name of power spectrum file is powerspectrum-<scale_factor>.txt, you can find the scale factor in the file name and convert it to redshift using the following formula:
redshift = 1 / scale_factor - 1
if you can't find the specific redshift in the file name, you can use the nearest redshift in the file name.
the output file name should be "{output_filename}", make sure you use the correct file name and label the redshift on the plot."""