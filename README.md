# SimAgents

A powerful AI-driven framework for automating cosmological simulation workflows. SimAgents combines multiple specialized AI agents to extract simulation parameters from scientific papers, generate visualizations, and create 3D density field plots from MP-Gadget simulation data.

## 🚀 Features

### Core Capabilities

- **📄 Parameter Extraction**: Automatically extract MP-Gadget simulation parameters from scientific papers using AI-powered document analysis
- **📊 Power Spectrum Visualization**: Generate publication-quality power spectrum plots from simulation outputs
- **🎨 3D Density Field Visualization**: Create stunning 3D density field visualizations using gaepsi2 integration
- **🤖 AI Code Generation**: Automatic Python code generation and execution with error handling
- **🔧 Workflow Automation**: End-to-end automation of complex simulation analysis tasks

### Agent Architecture

- **VisualizationAgent**: Specialized in creating scientific plots and power spectrum visualizations
- **DensityFieldAgent**: Expert in 3D density field visualization with RAG-enhanced code generation
- **ParameterRetriever**: Extracts simulation parameters from scientific literature
- **CodeExecutor**: Safe execution environment for AI-generated code with automatic error handling

## 📦 Installation

### Prerequisites

- Python 3.8+
- OpenAI API key

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd SimAgents
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API key**
   
   Create a `.env` file in the root directory:
   ```env
   OPENAI_API_KEY="your-openai-api-key-here"
   ```

### Optional Dependencies

For 3D density field visualization, uncomment and install the optional packages in `requirements.txt`:

```bash
# For gaepsi2 support (may require manual compilation)
pip install Cython>=3.0.0
pip install gaepsi2
pip install bigfile
```

**Note**: gaepsi2 may have compilation issues on some systems. See installation tips in `requirements.txt`.

## 🎯 Quick Start

### Parameter Extraction

Extract simulation parameters from scientific papers:

```python
#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
from workflows.parameter_extraction import ParameterExtractionWorkflow

# Load environment variables
load_dotenv()

def main():
    # Path to your PDF paper
    paper_path = "path/to/your/paper.pdf"
    
    # Output directory for extracted parameters
    output_dir = "parameter_output"
    
    # Create workflow with custom extraction prompt
    workflow = ParameterExtractionWorkflow(
        paper_path=paper_path,
        output_dir=output_dir,
        max_iterations=2,
        custom_prompt="Extract parameters for the simulation run with name XXXXX"
    )
    
    # Run extraction
    file_paths = workflow.run()
    
    print("✅ Extraction completed!")
    for file_type, file_path in file_paths.items():
        print(f"📄 {file_type.capitalize()}: {file_path}")

if __name__ == "__main__":
    main()
```

### Complete Visualization Workflow

Run both power spectrum and density field visualization:

```python
#!/usr/bin/env python3
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Run complete visualization workflow."""
    
    # Setup paths
    simulation_output_dir = Path("path/to/simulation/output")
    visualization_output_dir = Path("visualization_output")
    demo_file = Path("data/gaepsi2_demo.py")
    
    # Create output directory
    visualization_output_dir.mkdir(exist_ok=True)
    
    # Import agents
    from agents.visualization_agent import VisualizationAgent
    from agents.density_field_agent import DensityFieldAgent
    
    # Step 1: Power Spectrum Visualization
    print("🎨 Creating power spectrum plots...")
    viz_agent = VisualizationAgent()
    
    result = viz_agent.generate_and_execute_plot(
        output_dir=str(simulation_output_dir),
        output_filename=str(visualization_output_dir / "power_spectrum.png")
    )
    
    # Step 2: Density Field Visualization (optional - requires gaepsi2)
    print("🎨 Creating density field visualization...")
    try:
        density_agent = DensityFieldAgent(gaepsi2_demo_path=str(demo_file))
        
        result = density_agent.generate_and_execute_density_field(
            simulation_output_dir=str(simulation_output_dir),
            output_dir=str(visualization_output_dir),
            snapshot_name="PART_000",
            particle_type=1
        )
        
        density_agent.cleanup()
        print("✅ Complete workflow finished!")
        
    except Exception as e:
        print(f"⚠️ Density field visualization skipped: {e}")
        print("💡 Install gaepsi2 dependencies for full functionality")

if __name__ == "__main__":
    main()
```

## 🔧 Configuration

### Environment Variables

Configure SimAgents through environment variables in `.env`:

```env
# Required
OPENAI_API_KEY="your-openai-api-key"
```

### LLM Settings

Default settings provide reproducible results:

- **Model**: gpt-4o
- **Temperature**: 0.01 (for reproducibility)
- **Top-p**: 0.1 

## 📊 Supported Data Formats

### Input Formats

- **PDF Papers**: Scientific papers for parameter extraction
- **MP-Gadget Output**: BigFile format simulation data
- **Power Spectrum Files**: `powerspectrum-{scale_factor}.txt`
- **Snapshot Files**: `Snapshots.txt` with scale factor listings

### Output Formats

- **Parameter Files**: JSON format with genic/gadget configurations
- **Visualizations**: High-resolution PNG plots
- **Generated Code**: Self-contained Python scripts

## 🎨 Example Outputs

### Parameter Extraction
```json
"genic": {
      "OutputDir": "./ICs/",
      "FileBase": "LR_100Mpc_64",
      "BoxSize": 100000.0,
      "Ngrid": 64,
      "WhichSpectrum": 2,
      "FileWithInputSpectrum": "./WMAP9_CAMB_matterpower.dat",
      "Omega0": 0.2814,
      "OmegaBaryon": 0.0464,
      "OmegaLambda": 0.7186,
      "HubbleParam": 0.697,
      "ProduceGas": 0,
      "Redshift": 99,
      "Seed": 12345
    }

"gadget": {
      "InitCondFile": "./ICs/LR_100Mpc_64",
      "OutputDir": "./output/",
      "OutputList": "0.333,1.0",
      "TimeLimitCPU": 86400,
      "MetalReturnOn": 0,
      "CoolingOn": 0,
      "SnapshotWithFOF": 0,
      "BlackHoleOn": 0,
      "StarformationOn": 0,
      "WindOn": 0,
      "MassiveNuLinRespOn": 0,
      "DensityIndependentSphOn": 0,
      "Omega0": 0.2814
    }
}
```

### Generated Visualizations

- **Power Spectrum Plots**: Log-log scale P(k) vs k with redshift labels
- **Density Field Visualizations**: 3D rendered density fields from particle data

## 🔍 Golden Standard Database

SimAgents includes a comprehensive database of validated simulation parameters from major cosmological surveys:

- **IllustrisTNG**: TNG100, TNG300 series
- **Millennium**: Large-scale structure simulations  
- **MTNG**: MillenniumTNG simulations
- **Magneticum**: Galaxy formation simulations
- **SIMBA**: Hydrodynamical simulations

## 🛠️ Development

### Testing

Run the test workflows to verify functionality:

```bash
# Test parameter extraction
python workflows/run_example_extraction.py

# Test visualization
python workflows/visualization_workflow.py

# Test complete workflow
python workflows/complete_visualization_workflow.py
```


## 🙏 Acknowledgments

- **AutoGen**: Multi-agent conversation framework
- **OpenAI**: GPT models for AI capabilities
- **MP-Gadget**: Cosmological simulation code
- **gaepsi2**: 3D visualization library
- **BigFile**: Efficient data storage format

---

**Note**: This framework is designed for research purposes in computational cosmology. Ensure proper validation of extracted parameters before use in production simulations.