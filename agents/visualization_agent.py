from typing import Optional, Any, List
import os
import glob
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from autogen import LLMConfig
from agents.base_agent import BaseAgent
from agents.code_executor import SharedCodeExecutor


VISUALIZATION_SYSTEM_MESSAGE = """
You are a helpful AI assistant specialized in creating scientific visualizations for cosmological simulations.
You help physicists plot power spectra from MP-Gadget simulation outputs using matplotlib.

Your main tasks:
1. Load power spectrum files with format: powerspectrum-{scale_factor}.txt
2. Use Snapshots.txt to determine which scale factors to plot (if available)
3. Plot power spectra using loglog scale
4. Calculate and label redshifts: z = 1/scale_factor - 1
5. Create publication-quality plots with proper axis labels and legends

The Snapshots.txt file contains lines like "000 0.3333" where the first number is the snapshot index
and the second number is the scale factor. Only plot power spectra for scale factors listed in this file.

Always use matplotlib for plotting and ensure proper scientific formatting.
Reply 'TERMINATE' when the visualization is complete.
"""


class VisualizationAgent(BaseAgent):
    """Agent for creating power spectrum visualizations from MP-Gadget simulation outputs."""
    
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
            llm_config: LLM configuration (if None, uses default reproducible settings)
            **kwargs: Additional arguments
        """
        # Set default LLM config for reproducibility if none provided
        if llm_config is None:
            import os
            llm_config = {
                "model": "gpt-4o",
                "temperature": 0.01,
                "top_p": 0.1,
                "api_key": os.environ.get("OPENAI_API_KEY")
            }
        
        super().__init__(
            name=name,
            system_message=VISUALIZATION_SYSTEM_MESSAGE,
            llm_config=llm_config,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            **kwargs
        )
    
    def setup(self) -> None:
        """Setup the visualization agent."""
        pass
    
    def execute(self, message: str, **kwargs) -> Any:
        """
        Execute visualization request (required by BaseAgent).
        
        Args:
            message: Message containing visualization request
            **kwargs: Additional arguments
            
        Returns:
            Response from the agent
        """
        return self.agent.generate_reply([{"role": "user", "content": message}])
    
    def execute_with_code(self, message: str) -> Any:
        """
        Execute visualization request with automatic code generation and execution.
        
        Args:
            message: Message containing visualization request
            
        Returns:
            Chat result from the code execution
        """
        # Get shared code executor
        code_executor = SharedCodeExecutor.get_executor()
        
        # Generate and execute code
        print(f"🎯 Executing visualization request: {message[:100]}...")
        result = code_executor.execute_with_agent(self.agent, message)
        
        return result
    
    def _read_snapshots_file(self, output_dir: str) -> List[float]:
        """
        Read Snapshots.txt file to get the scale factors that should be plotted.
        
        Args:
            output_dir: Directory containing Snapshots.txt
            
        Returns:
            List of scale factors from second column of Snapshots.txt
        """
        snapshots_file = os.path.join(output_dir, "Snapshots.txt")
        scale_factors = []
        
        if not os.path.exists(snapshots_file):
            print(f"Warning: Snapshots.txt not found in {output_dir}")
            return scale_factors
        
        try:
            with open(snapshots_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                # Load the number in the second column
                                scale_factor = float(parts[1])
                                scale_factors.append(scale_factor)
                            except ValueError:
                                print(f"Warning: Could not parse scale factor from line: {line}")
        except Exception as e:
            print(f"Warning: Could not read Snapshots.txt: {e}")
        
        return scale_factors

    def plot_power_spectrum(
        self,
        output_dir: str,
        output_filename: str = "power_spectrum.png",
        specific_redshifts: Optional[List[float]] = None,
        use_snapshots_file: bool = True
    ) -> str:
        """
        Plot power spectrum from simulation output files.
        
        Args:
            output_dir: Directory containing powerspectrum-{scale_factor}.txt files
            output_filename: Output plot filename
            specific_redshifts: List of specific redshifts to plot (if None, uses Snapshots.txt)
            use_snapshots_file: Whether to use Snapshots.txt to filter scale factors
            
        Returns:
            Path to saved plot
        """
        # Get scale factors from Snapshots.txt if requested
        target_scale_factors = None
        if use_snapshots_file and specific_redshifts is None:
            target_scale_factors = self._read_snapshots_file(output_dir)
            if target_scale_factors:
                print(f"Found {len(target_scale_factors)} scale factors in Snapshots.txt: {target_scale_factors}")
        
        # Find all power spectrum files
        pattern = os.path.join(output_dir, "powerspectrum-*.txt")
        files = glob.glob(pattern)
        
        if not files:
            raise FileNotFoundError(f"No power spectrum files found in {output_dir}")
        
        # Extract scale factors and calculate redshifts
        data_list = []
        for file in files:
            filename = os.path.basename(file)
            # Extract scale factor from filename: powerspectrum-0.333333.txt -> 0.333333
            scale_factor_str = filename.replace("powerspectrum-", "").replace(".txt", "")
            try:
                scale_factor = float(scale_factor_str)
                redshift = 1.0 / scale_factor - 1.0
                
                # Filter by Snapshots.txt scale factors if available
                if target_scale_factors is not None:
                    # Find closest scale factor in Snapshots.txt (within 1% tolerance)
                    if not any(abs(scale_factor - target_sf) / target_sf < 0.01 for target_sf in target_scale_factors):
                        continue
                
                # Filter by specific redshifts if provided
                if specific_redshifts is not None:
                    if not any(abs(redshift - z) < 0.1 for z in specific_redshifts):
                        continue
                
                # Load power spectrum data
                data = np.loadtxt(file)
                k = data[:, 0]  # wavenumber
                P_k = data[:, 1]  # power spectrum
                
                data_list.append({
                    'k': k,
                    'P_k': P_k,
                    'redshift': redshift,
                    'scale_factor': scale_factor,
                    'file': file
                })
            except (ValueError, IndexError) as e:
                print(f"Warning: Could not process file {file}: {e}")
                continue
        
        if not data_list:
            if target_scale_factors:
                raise ValueError(f"No power spectrum files found matching scale factors from Snapshots.txt: {target_scale_factors}")
            else:
                raise ValueError("No valid power spectrum data found")
        
        # Sort by redshift (highest to lowest)
        data_list.sort(key=lambda x: x['redshift'], reverse=True)
        
        # Create the plot
        plt.figure(figsize=(10, 8))
        
        for data in data_list:
            label = f"z = {data['redshift']:.2f}"
            plt.loglog(data['k'], data['P_k'], label=label, linewidth=2)
        
        plt.xlabel(r'k [h/Mpc]', fontsize=14)
        plt.ylabel(r'P(k) [(Mpc/h)³]', fontsize=14)
        plt.title('Matter Power Spectrum', fontsize=16)
        plt.legend(fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Save the plot
        if os.path.isabs(output_filename):
            output_path = output_filename
        else:
            output_path = os.path.join(output_dir, output_filename)
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def create_power_spectrum_message(
        self,
        output_dir: str,
        redshift: Optional[float] = None,
        output_filename: str = "power_spectrum.png"
    ) -> str:
        """
        Create a message for power spectrum plotting.
        
        Args:
            output_dir: Directory containing simulation output
            redshift: Specific redshift to plot (if None, plots all available)
            output_filename: Output file name
            
        Returns:
            Message string
        """
        if redshift is not None:
            return f"""Plot the power spectrum at redshift z={redshift} from the simulation output directory: {output_dir}

Load the powerspectrum-{{scale_factor}}.txt files where scale_factor = 1/(1+z).
Use matplotlib to create a loglog plot with:
- X-axis: k [h/Mpc] 
- Y-axis: P(k) [(Mpc/h)³]
- Label the redshift on the plot
- Save as {output_filename}

Find the file with scale factor closest to {1.0/(1.0+redshift):.6f} for redshift {redshift}."""
        else:
            return f"""Plot all available power spectra from the simulation output directory: {output_dir}

Load all powerspectrum-{{scale_factor}}.txt files and plot them together.
For each file:
1. Extract scale_factor from filename
2. Calculate redshift = 1/scale_factor - 1
3. Load the k and P(k) data
4. Plot using matplotlib loglog scale

Create a plot with:
- X-axis: k [h/Mpc]
- Y-axis: P(k) [(Mpc/h)³]  
- Legend showing redshift for each curve
- Save as {output_filename}

Use different colors/styles for each redshift."""
    
    def generate_and_execute_plot(self, output_dir: str, output_filename: str = "power_spectrum.png", redshift: Optional[float] = None) -> Any:
        """
        Generate Python code for power spectrum plotting and execute it automatically.
        
        Args:
            output_dir: Directory containing simulation output
            output_filename: Output file name
            redshift: Specific redshift to plot (if None, plots all available)
            
        Returns:
            Execution result
        """
        message = self.create_power_spectrum_message(output_dir, redshift, output_filename)
        return self.execute_with_code(message)