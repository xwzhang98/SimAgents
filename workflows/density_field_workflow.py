#!/usr/bin/env python3
"""
Density field workflow using DensityFieldAgent with CodeExecutor integration.
Creates 3D density field visualizations from MP-Gadget simulation data.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from agents.density_field_agent import DensityFieldAgent


def main():
    """Run density field workflow to create 3D visualizations."""
    
    # Setup paths
    project_root = Path(__file__).parent.parent
    simulation_output_dir = project_root / "example" / "simulation_output" / "output"
    visualization_output_dir = project_root / "example" / "visualization_output"
    demo_file = project_root / "data" / "gaepsi2_demo.py"
    
    print("🎨 Starting Density Field Workflow")
    print("=" * 50)
    print(f"📁 Simulation output: {simulation_output_dir}")
    print(f"📁 Visualization output: {visualization_output_dir}")
    print(f"📄 Demo file: {demo_file}")
    
    # Create output directory
    visualization_output_dir.mkdir(exist_ok=True)
    
    # Check if demo file exists
    if not demo_file.exists():
        print(f"❌ Error: Demo file not found: {demo_file}")
        print("💡 Tip: Make sure gaepsi2_demo.py is in the data/ directory")
        return
    
    # Check if simulation output exists
    if not simulation_output_dir.exists():
        print(f"❌ Error: Simulation output directory not found: {simulation_output_dir}")
        return
    
    # List available PART directories
    part_dirs = list(simulation_output_dir.glob("PART_*"))
    if not part_dirs:
        print(f"❌ Error: No PART_* directories found in {simulation_output_dir}")
        return
    
    print(f"\n✅ Found {len(part_dirs)} PART directories:")
    for part_dir in sorted(part_dirs):
        print(f"  📄 {part_dir.name}")
    
    try:
        # Create density field agent with RAG
        print(f"\n🤖 Creating DensityFieldAgent with RAG...")
        density_agent = DensityFieldAgent(
            gaepsi2_demo_path=str(demo_file)
        )
        
        # Test with first available PART directory
        snapshot_name = part_dirs[0].name
        print(f"\n🎯 Processing snapshot: {snapshot_name}")
        
        # Generate and execute density field visualization
        print("🚀 Generating and executing density field code...")
        result = density_agent.generate_and_execute_density_field(
            simulation_output_dir=str(simulation_output_dir),
            output_dir=str(visualization_output_dir),
            snapshot_name=snapshot_name,
            particle_type=1  # Dark matter particles
        )
        
        print(f"\n✅ Density field workflow completed!")
        
        # Check if the output was created
        expected_output = visualization_output_dir / f"density_field_{snapshot_name}_type1.png"
        if expected_output.exists():
            print(f"📊 Density field visualization saved to: {expected_output}")
            print(f"🎯 Execution result: Success - Visualization file created")
        else:
            print(f"⚠️ Expected output file not found: {expected_output}")
            print(f"🎯 Execution result: Warning - Check execution logs")
        
        print(f"📝 Execution details: {result}")
        
        # Clean up
        density_agent.cleanup()
        print("🧹 Cleaned up agent resources")
        
    except Exception as e:
        print(f"\n💥 Error during density field workflow: {e}")
        
        # Check for common issues
        if "OPENAI_API_KEY" in str(e):
            print("💡 Tip: Make sure OPENAI_API_KEY is set in your .env file")
        elif "gaepsi2" in str(e).lower():
            print("💡 Tip: Install gaepsi2 dependencies (see requirements.txt)")
            print("   Uncomment the optional packages section and run: pip install -r requirements.txt")
        elif "bigfile" in str(e).lower():
            print("💡 Tip: Install BigFile package for particle data loading")
            print("   Run: pip install bigfile")
        
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()