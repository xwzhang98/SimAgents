#!/usr/bin/env python3
"""
Test script for the updated DensityFieldAgent with RAG capabilities.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from agents.density_field_agent import DensityFieldAgent


def main():
    """Test the density field agent with RAG functionality."""
    
    # Paths
    project_root = Path(__file__).parent.parent
    simulation_output_dir = project_root / "example" / "simulation_output" / "output"
    visualization_output_dir = project_root / "example" / "visualization_output"
    demo_file = project_root / "data" / "gaepsi2_demo.py"
    
    # Create visualization output directory
    visualization_output_dir.mkdir(exist_ok=True)
    
    print("🎨 Testing DensityFieldAgent with RAG")
    print(f"📄 Demo file: {demo_file}")
    print(f"📁 Simulation output: {simulation_output_dir}")
    print(f"📁 Visualization output: {visualization_output_dir}")
    print("-" * 60)
    
    # Check if demo file exists
    if not demo_file.exists():
        print(f"❌ Error: Demo file not found: {demo_file}")
        return
    
    # Check simulation output
    if not simulation_output_dir.exists():
        print(f"❌ Error: Simulation output not found: {simulation_output_dir}")
        return
    
    # List available PART directories
    part_dirs = list(simulation_output_dir.glob("PART_*"))
    if not part_dirs:
        print(f"❌ Error: No PART_* directories found in {simulation_output_dir}")
        return
    
    print(f"✅ Found {len(part_dirs)} PART directories:")
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
        print(f"\n🎯 Testing with snapshot: {snapshot_name}")
        
        # Generate density field visualization script
        script_path = density_agent.create_density_field_visualization(
            simulation_output_dir=str(simulation_output_dir),
            output_dir=str(visualization_output_dir),
            snapshot_name=snapshot_name,
            particle_type=1  # Dark matter particles
        )
        
        print(f"\n🎉 Density field agent test completed successfully!")
        print(f"📝 Generated script: {script_path}")
        print(f"📊 Check the generated Python script for gaepsi2 visualization code")
        
        # Clean up
        density_agent.cleanup()
        
    except Exception as e:
        print(f"\n💥 Error during density field generation: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()