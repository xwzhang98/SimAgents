from typing import Optional, Any, Dict
import os
import tempfile
from autogen import LLMConfig, ConversableAgent
from autogen.coding import LocalCommandLineCodeExecutor
from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent
from agents.base_agent import BaseAgent
from agents.code_executor import SharedCodeExecutor


GAEPSI2_INSTRUCTIONS = """
You are a gaepsi2 visualization expert that helps create 3D density field plots from MP-Gadget simulation data.

Your tasks:
1. **Use RAG**: Search the uploaded gaepsi2 demo file to understand the visualization pipeline
2. **Adapt Code**: Modify the demo code to work with the user's specific PART_* files
3. **Generate Scripts**: Create complete, runnable Python scripts for density field visualization
4. **Handle Paths**: Automatically detect and use the correct PART_* directories in simulation output
5. **Save Output**: Ensure plots are saved to the specified output directory

Key gaepsi2 components to use:
- `BigFile` for loading PART_* particle data
- `camera` module for 3D transformations and projections  
- `painter.paint` for rendering density fields
- `matplotlib` for final plot generation

Requirements:
- Code must be self-contained and executable
- Use the gaepsi2 pipeline from the demo file as a template
- Adapt particle loading for BigFile PART_* format
- Save visualization output as PNG files
- Handle different particle types (dark matter, gas, etc.)

Always provide complete, working Python scripts that can be executed directly.
"""


class DensityFieldAgent:
    """Agent for creating density field visualizations using gaepsi2 with RAG."""
    
    def __init__(
        self,
        name: str = "density_field_agent",
        llm_config: Optional[LLMConfig] = None,
        gaepsi2_demo_path: str = None,
        **kwargs
    ):
        """
        Initialize density field agent.
        
        Args:
            name: Agent name
            llm_config: LLM configuration (if None, uses default settings)
            gaepsi2_demo_path: Path to gaepsi2 demo file (if None, uses default)
            **kwargs: Additional arguments
        """
        self.name = name
        self.gaepsi2_demo_path = gaepsi2_demo_path or self._get_default_demo_path()
        
        # Set default LLM config if none provided
        if llm_config is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable must be set")
            
            llm_config = {
                "model": "gpt-4o",
                "temperature": 0.01,
                "top_p": 0.1,
                "api_key": api_key
            }
        
        self.llm_config = llm_config
        self._vector_store_id = None
        self._assistant_id = None
        
        # Setup GPT Assistant with RAG
        self._setup_gpt_assistant()
    
    def _get_default_demo_path(self):
        """Get the default path to gaepsi2_demo.py."""
        # Assume the demo file is in the data directory relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        return os.path.join(project_root, "data", "gaepsi2_demo.py")
    
    def _create_vector_store(self):
        """Create vector store and upload gaepsi2 demo file."""
        from openai import OpenAI
        
        client = OpenAI(api_key=self.llm_config["api_key"])
        
        # Create vector store
        vector_store = client.vector_stores.create(
            name="Gaepsi2 Demo Code"
        )
        
        # Upload demo file
        if os.path.exists(self.gaepsi2_demo_path):
            with open(self.gaepsi2_demo_path, 'rb') as f:
                file_batch = client.vector_stores.file_batches.upload_and_poll(
                    vector_store_id=vector_store.id,
                    files=[f]
                )
            print(f"✅ Uploaded gaepsi2 demo file: {self.gaepsi2_demo_path}")
        else:
            print(f"⚠️ Warning: Demo file not found: {self.gaepsi2_demo_path}")
        
        return vector_store.id
    
    def _setup_gpt_assistant(self):
        """Setup the GPT Assistant agent with RAG."""
        from openai import OpenAI
        
        client = OpenAI(api_key=self.llm_config["api_key"])
        
        # Create vector store and upload demo file
        self._vector_store_id = self._create_vector_store()
        
        # Create assistant with file search
        assistant = client.beta.assistants.create(
            name="Gaepsi2 Density Field Visualizer",
            instructions=GAEPSI2_INSTRUCTIONS,
            model=self.llm_config["model"],
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [self._vector_store_id]
                }
            },
            temperature=self.llm_config.get("temperature", 0.01),
            top_p=self.llm_config.get("top_p", 0.1)
        )
        
        self._assistant_id = assistant.id
        print(f"✅ Created GPT Assistant: {self._assistant_id}")
    
    def _run_assistant(self, message: str) -> str:
        """Run the assistant with a message and return response."""
        from openai import OpenAI
        import time
        
        client = OpenAI(api_key=self.llm_config["api_key"])
        
        # Create thread
        thread = client.beta.threads.create()
        
        # Add message
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=message
        )
        
        # Run assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self._assistant_id
        )
        
        # Wait for completion
        max_wait = 300  # 5 minutes
        start_time = time.time()
        
        while run.status not in ["completed", "failed", "cancelled"]:
            if time.time() - start_time > max_wait:
                client.beta.threads.runs.cancel(thread_id=thread.id, run_id=run.id)
                raise TimeoutError("Assistant run timed out")
            
            time.sleep(2)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
        
        if run.status != "completed":
            raise Exception(f"Assistant run failed with status: {run.status}")
        
        # Get response
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        for msg in messages.data:
            if msg.role == "assistant":
                return msg.content[0].text.value
        
        raise ValueError("No assistant response found")
    
    def setup(self) -> None:
        """Setup method (already done in __init__)."""
        pass
    
    def generate_density_field_code(
        self,
        part_dir: str,
        output_file: str = "density_field.png",
        particle_type: int = 1
    ) -> str:
        """
        Generate Python code for creating density field visualization.
        
        Args:
            part_dir: Path to PART_* directory containing particle data
            output_file: Output image filename
            particle_type: Particle type to visualize (1=dark matter, 0=gas, etc.)
            
        Returns:
            Generated Python code as string
        """
        message = f"""
Using the gaepsi2 demo code as a reference, create a complete Python script that:

1. Loads particle data from BigFile directory: {part_dir}
2. Uses particle type {particle_type} (1=dark matter, 0=gas, etc.)
3. Creates a 3D density field visualization using gaepsi2
4. Saves the output as: {output_file}

Requirements:
- Use the gaepsi2 pipeline from the uploaded demo file
- Adapt the particle loading for BigFile PART_* format
- Set appropriate visualization parameters for the simulation box
- Include proper error handling and logging
- Make the script self-contained and executable

The script should handle the BigFile structure where particle data is stored in subdirectories like:
- Position/
- Velocity/  
- Mass/
- ID/

Generate complete, working Python code that can be executed directly.
"""
        
        return self._run_assistant(message)
    
    def create_density_field_visualization(
        self,
        simulation_output_dir: str,
        output_dir: str,
        snapshot_name: str = "PART_000",
        particle_type: int = 1
    ) -> str:
        """
        Create density field visualization from simulation output.
        
        Args:
            simulation_output_dir: Directory containing PART_* snapshots
            output_dir: Directory to save visualization output
            snapshot_name: Name of snapshot directory (e.g., "PART_000")
            particle_type: Particle type to visualize
            
        Returns:
            Path to generated visualization script
        """
        import os
        
        # Find the PART directory
        part_dir = os.path.join(simulation_output_dir, snapshot_name, str(particle_type))
        if not os.path.exists(part_dir):
            raise FileNotFoundError(f"PART directory not found: {part_dir}")
        
        # Generate output filename
        output_file = os.path.join(output_dir, f"density_field_{snapshot_name}_type{particle_type}.png")
        
        # Generate the code
        print(f"🎨 Generating density field code for {part_dir}")
        code = self.generate_density_field_code(part_dir, output_file, particle_type)
        
        # Save the generated script
        script_path = os.path.join(output_dir, f"density_field_script_{snapshot_name}.py")
        with open(script_path, 'w') as f:
            f.write(code)
        
        print(f"✅ Generated script: {script_path}")
        print(f"📊 Output will be saved to: {output_file}")
        
        return script_path
    
    def generate_and_execute_density_field(
        self,
        simulation_output_dir: str,
        output_dir: str,
        snapshot_name: str = "PART_000",
        particle_type: int = 1
    ) -> Any:
        """
        Generate and execute density field visualization code automatically.
        
        Args:
            simulation_output_dir: Directory containing PART_* snapshots
            output_dir: Directory to save visualization output
            snapshot_name: Name of snapshot directory (e.g., "PART_000")
            particle_type: Particle type to visualize
            
        Returns:
            Execution result from the code executor
        """
        import os
        
        # Find the PART directory
        part_dir = os.path.join(simulation_output_dir, snapshot_name, str(particle_type))
        if not os.path.exists(part_dir):
            raise FileNotFoundError(f"PART directory not found: {part_dir}")
        
        # Generate output filename
        output_file = os.path.join(output_dir, f"density_field_{snapshot_name}_type{particle_type}.png")
        
        # Create message for code generation
        message = f"""
Using the gaepsi2 demo code as a reference, create and execute a complete Python script that:

1. Loads particle data from BigFile directory: {part_dir}
2. Uses particle type {particle_type} (1=dark matter, 0=gas, etc.)
3. Creates a 3D density field visualization using gaepsi2
4. Saves the output as: {output_file}

Requirements:
- Use the gaepsi2 pipeline from the uploaded demo file
- Adapt the particle loading for BigFile PART_* format
- Set appropriate visualization parameters for the simulation box
- Include proper error handling and logging
- Make the script self-contained and executable

The script should handle the BigFile structure where particle data is stored in subdirectories like:
- Position/
- Velocity/  
- Mass/
- ID/

Generate complete, working Python code that can be executed directly.
"""
        
        print(f"🎯 Generating and executing density field code for {part_dir}")
        
        # Get shared code executor
        code_executor = SharedCodeExecutor.get_executor()
        
        # Execute through the assistant
        result = self._run_assistant_with_execution(message, code_executor)
        
        print(f"✅ Density field visualization completed")
        print(f"📊 Output saved to: {output_file}")
        
        return result
    
    def _run_assistant_with_execution(self, message: str, code_executor) -> Any:
        """
        Run the assistant with a message and execute generated code.
        
        Args:
            message: Message to send to the assistant
            code_executor: Code executor instance
            
        Returns:
            Execution result
        """
        try:
            # Get code from assistant
            assistant_response = self._run_assistant(message)
            
            # Extract Python code from response
            code = self._extract_python_code(assistant_response)
            
            if code:
                print("💾 Executing generated code...")
                result = code_executor.execute_code(code)
                
                # Check if execution was successful
                if result.get("success", False):
                    print("✅ Code executed successfully")
                else:
                    print("⚠️ Code execution had issues")
                    print(f"Output: {result.get('output', 'No output')}")
                
                return result
            else:
                print("⚠️ No Python code found in assistant response")
                return {"success": False, "output": "No code generated", "response": assistant_response}
                
        except Exception as e:
            print(f"💥 Error during execution: {e}")
            return {"success": False, "error": str(e)}
    
    def _extract_python_code(self, response: str) -> Optional[str]:
        """
        Extract Python code from assistant response.
        
        Args:
            response: Assistant response text
            
        Returns:
            Extracted Python code or None if not found
        """
        import re
        
        # Look for code blocks marked with ```python
        pattern = r'```python\s*\n(.*?)\n```'
        matches = re.findall(pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # Look for code blocks marked with just ```
        pattern = r'```\s*\n(.*?)\n```'
        matches = re.findall(pattern, response, re.DOTALL)
        
        if matches:
            # Check if it looks like Python code
            code = matches[0].strip()
            if any(keyword in code for keyword in ['import', 'def ', 'if __name__', 'plt.', 'np.']):
                return code
        
        return None
    
    def create_density_field_message(
        self,
        lr_snapshot_path: str,
        sr_snapshot_path: str = None,
        output_filename: str = "density_field.png",
        side_by_side: bool = False
    ) -> str:
        """
        Create a message for density field plotting (legacy compatibility).
        
        Args:
            lr_snapshot_path: Path to low-resolution snapshot
            sr_snapshot_path: Path to super-resolution snapshot
            output_filename: Output file name
            side_by_side: Whether to create side-by-side comparison
            
        Returns:
            Message string
        """
        if sr_snapshot_path and side_by_side:
            message = f"""
Create Python code using gaepsi2 and BigFile to visualize density fields from:
- LR snapshot: {lr_snapshot_path}
- SR snapshot: {sr_snapshot_path}

Create side-by-side comparison plots and save as {output_filename}.
Use the gaepsi2 demo as reference for the visualization pipeline.
"""
        else:
            message = f"""
Create Python code using gaepsi2 and BigFile to visualize density field from:
- Snapshot: {lr_snapshot_path}

Save the visualization as {output_filename}.
Use the gaepsi2 demo as reference for the visualization pipeline.
"""
        
        return self._run_assistant(message)
    
    def cleanup(self):
        """Clean up resources."""
        from openai import OpenAI
        
        try:
            client = OpenAI(api_key=self.llm_config["api_key"])
            
            # Delete vector store
            if self._vector_store_id:
                client.vector_stores.delete(vector_store_id=self._vector_store_id)
                print(f"✅ Cleaned up vector store: {self._vector_store_id}")
                
            # Note: Assistant cleanup is optional as they can be reused
            
        except Exception as e:
            print(f"⚠️ Warning: Cleanup failed: {e}")
    
    def execute_with_code(self, message: str) -> Any:
        """
        Execute a density field request with automatic code generation and execution.
        
        Args:
            message: Message containing density field request
            
        Returns:
            Execution result
        """
        # Get shared code executor
        code_executor = SharedCodeExecutor.get_executor()
        
        # Execute through the assistant with code execution
        return self._run_assistant_with_execution(message, code_executor)
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except:
            pass