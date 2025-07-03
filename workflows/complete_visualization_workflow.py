#!/usr/bin/env python3
"""
Complete visualization workflow that runs both visualization and density field agents.
First creates power spectrum plots, then generates 3D density field visualizations.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from agents.visualization_agent import VisualizationAgent
from agents.density_field_agent import DensityFieldAgent


def run_visualization_workflow(simulation_output_dir: Path, visualization_output_dir: Path) -> bool:
    """
    Run the visualization workflow to create power spectrum plots.
    
    Args:
        simulation_output_dir: Directory containing simulation output
        visualization_output_dir: Directory to save visualization output
        
    Returns:
        True if successful, False otherwise
    """
    print("🎨 Starting Visualization Agent Workflow")
    print("=" * 50)
    
    try:
        # Create visualization agent
        print("🤖 Creating VisualizationAgent...")
        viz_agent = VisualizationAgent()
        
        # Generate and execute power spectrum plot
        print("🚀 Generating power spectrum plot...")
        output_file = str(visualization_output_dir / "power_spectrum.png")
        
        result = viz_agent.generate_and_execute_plot(
            output_dir=str(simulation_output_dir),
            output_filename=output_file
        )
        
        # Check if the output was created
        if Path(output_file).exists():
            print(f"✅ Power spectrum plot created: {output_file}")
            print(f"📝 Chat completed with {len(result.chat_history)} messages")
            return True
        else:
            print(f"❌ Power spectrum plot not found: {output_file}")
            return False
            
    except Exception as e:
        print(f"💥 Error in visualization workflow: {e}")
        if "OPENAI_API_KEY" in str(e):
            print("💡 Tip: Make sure OPENAI_API_KEY is set in your .env file")
        return False


def run_density_field_workflow(simulation_output_dir: Path, visualization_output_dir: Path, demo_file: Path) -> bool:
    """
    Run the density field workflow to create 3D visualizations.
    
    Args:
        simulation_output_dir: Directory containing simulation output
        visualization_output_dir: Directory to save visualization output
        demo_file: Path to gaepsi2 demo file
        
    Returns:
        True if successful, False otherwise
    """
    print("\n🎨 Starting Density Field Agent Workflow")
    print("=" * 50)
    
    # Check if demo file exists
    if not demo_file.exists():
        print(f"❌ Error: Demo file not found: {demo_file}")
        print("💡 Tip: Make sure gaepsi2_demo.py is in the data/ directory")
        return False
    
    # List available PART directories
    part_dirs = list(simulation_output_dir.glob("PART_*"))
    if not part_dirs:
        print(f"❌ Error: No PART_* directories found in {simulation_output_dir}")
        return False
    
    print(f"✅ Found {len(part_dirs)} PART directories")
    
    try:
        # Create density field agent with RAG
        print("🤖 Creating DensityFieldAgent with RAG...")
        density_agent = DensityFieldAgent(
            gaepsi2_demo_path=str(demo_file)
        )
        
        # Test with first available PART directory
        snapshot_name = part_dirs[0].name
        print(f"🎯 Processing snapshot: {snapshot_name}")
        
        # Generate and execute density field visualization
        print("🚀 Generating and executing density field code...")
        result = density_agent.generate_and_execute_density_field(
            simulation_output_dir=str(simulation_output_dir),
            output_dir=str(visualization_output_dir),
            snapshot_name=snapshot_name,
            particle_type=1  # Dark matter particles
        )
        
        # Check if the output was created
        expected_output = visualization_output_dir / f"density_field_{snapshot_name}_type1.png"
        if expected_output.exists():
            print(f"✅ Density field visualization created: {expected_output}")
            # Clean up
            density_agent.cleanup()
            return True
        else:
            # Check execution result for errors
            if result and isinstance(result, dict):
                output = result.get('output', '')
                if 'gaepsi2' in output:
                    print("⚠️ gaepsi2 package not installed - density field visualization skipped")
                    print("💡 Tip: Install gaepsi2 dependencies (see requirements.txt)")
                elif 'bigfile' in output:
                    print("⚠️ bigfile package not installed - density field visualization skipped")
                    print("💡 Tip: Install bigfile package: pip install bigfile")
                else:
                    print(f"⚠️ Density field execution completed but output file not found")
                    print(f"📝 Execution details: {result}")
            
            # Clean up
            density_agent.cleanup()
            return False
            
    except Exception as e:
        print(f"💥 Error in density field workflow: {e}")
        
        # Check for common issues
        if "OPENAI_API_KEY" in str(e):
            print("💡 Tip: Make sure OPENAI_API_KEY is set in your .env file")
        elif "gaepsi2" in str(e).lower():
            print("💡 Tip: Install gaepsi2 dependencies (see requirements.txt)")
        elif "bigfile" in str(e).lower():
            print("💡 Tip: Install BigFile package for particle data loading")
        
        return False


def main():
    """Run complete visualization workflow."""
    
    # Setup paths
    project_root = Path(__file__).parent.parent
    simulation_output_dir = project_root / "example" / "simulation_output" / "output"
    visualization_output_dir = project_root / "example" / "visualization_output"
    demo_file = project_root / "data" / "gaepsi2_demo.py"
    
    print("🚀 Starting Complete Visualization Workflow")
    print("=" * 60)
    print(f"📁 Simulation output: {simulation_output_dir}")
    print(f"📁 Visualization output: {visualization_output_dir}")
    print(f"📄 Demo file: {demo_file}")
    print()
    
    # Create output directory
    visualization_output_dir.mkdir(exist_ok=True)
    
    # Check if simulation output exists
    if not simulation_output_dir.exists():
        print(f"❌ Error: Simulation output directory not found: {simulation_output_dir}")
        return
    
    # Track results
    results = {
        'visualization': False,
        'density_field': False
    }
    
    # Step 1: Run visualization workflow
    print("STEP 1: Power Spectrum Visualization")
    print("-" * 40)
    results['visualization'] = run_visualization_workflow(simulation_output_dir, visualization_output_dir)
    
    # Step 2: Run density field workflow
    print("\nSTEP 2: Density Field Visualization")
    print("-" * 40)
    results['density_field'] = run_density_field_workflow(simulation_output_dir, visualization_output_dir, demo_file)
    
    # Final summary
    print("\n" + "=" * 60)
    print("📋 Complete Workflow Summary:")
    print(f"   Power Spectrum:   {'✅ SUCCESS' if results['visualization'] else '❌ FAILED'}")
    print(f"   Density Field:    {'✅ SUCCESS' if results['density_field'] else '⚠️  SKIPPED/FAILED'}")
    print()
    
    if results['visualization']:
        print("📊 Generated Files:")
        power_spectrum_file = visualization_output_dir / "power_spectrum.png"
        if power_spectrum_file.exists():
            print(f"   📈 {power_spectrum_file}")
        
        density_field_files = list(visualization_output_dir.glob("density_field_*.png"))
        for df_file in density_field_files:
            print(f"   🎨 {df_file}")
    
    if results['visualization'] and results['density_field']:
        print("\n🎉 Complete workflow succeeded! All visualizations generated.")
    elif results['visualization']:
        print("\n✅ Visualization workflow succeeded. Density field skipped due to missing dependencies.")
        print("💡 Install gaepsi2 and bigfile packages to enable density field visualization.")
    else:
        print("\n❌ Workflow failed. Check error messages above.")
    
    print("\n🏁 Workflow completed.")


if __name__ == "__main__":
    main()