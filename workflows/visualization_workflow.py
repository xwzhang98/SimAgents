#!/usr/bin/env python3
"""
Visualization workflow using VisualizationAgent with CodeExecutor integration.
Plots power spectrum and saves output to example/visualization_output.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from agents.visualization_agent import VisualizationAgent


def main():
    """Run visualization workflow to plot power spectrum."""
    
    # Setup paths
    project_root = Path(__file__).parent.parent
    simulation_output_dir = project_root / "example" / "simulation_output" / "output"
    visualization_output_dir = project_root / "example" / "visualization_output"
    
    print("🎨 Starting Visualization Workflow")
    print("=" * 50)
    print(f"📁 Simulation output: {simulation_output_dir}")
    print(f"📁 Visualization output: {visualization_output_dir}")
    
    # Create output directory
    visualization_output_dir.mkdir(exist_ok=True)
    
    # Check if simulation output exists
    if not simulation_output_dir.exists():
        print(f"❌ Error: Simulation output directory not found: {simulation_output_dir}")
        return
    
    try:
        # Create visualization agent
        print("\n🤖 Creating VisualizationAgent...")
        viz_agent = VisualizationAgent()
        
        # Generate and execute power spectrum plot
        print("\n🚀 Generating power spectrum plot...")
        output_file = str(visualization_output_dir / "power_spectrum.png")
        
        result = viz_agent.generate_and_execute_plot(
            output_dir=str(simulation_output_dir),
            output_filename=output_file
        )
        
        print(f"\n✅ Visualization workflow completed!")
        print(f"📊 Power spectrum plot saved to: {output_file}")
        
        # Check if the output file was created
        if Path(output_file).exists():
            print(f"🎯 Execution result: Success - Plot file created")
        else:
            print(f"🎯 Execution result: Warning - Plot file not found")
        
        print(f"📝 Chat completed with {len(result.chat_history)} messages")
        
    except Exception as e:
        print(f"\n💥 Error during visualization workflow: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()