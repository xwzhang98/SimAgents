#!/usr/bin/env python3
"""
Test script for the CodeExecutor integration with VisualizationAgent and DensityFieldAgent.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from agents.visualization_agent import VisualizationAgent
from agents.density_field_agent import DensityFieldAgent
from agents.code_executor import SharedCodeExecutor


def test_visualization_agent_with_executor():
    """Test VisualizationAgent with automatic code execution."""
    print("🎨 Testing VisualizationAgent with CodeExecutor")
    print("-" * 60)
    
    # Paths
    project_root = Path(__file__).parent.parent
    simulation_output_dir = project_root / "example" / "simulation_output" / "output"
    visualization_output_dir = project_root / "example" / "visualization_output"
    
    # Create visualization output directory
    visualization_output_dir.mkdir(exist_ok=True)
    
    # Check if simulation output exists
    if not simulation_output_dir.exists():
        print(f"❌ Error: Simulation output not found: {simulation_output_dir}")
        return False
    
    try:
        # Create visualization agent
        viz_agent = VisualizationAgent()
        
        # Test automatic code generation and execution
        print("🚀 Testing automatic power spectrum plotting...")
        output_file = str(visualization_output_dir / "auto_power_spectrum.png")
        
        result = viz_agent.generate_and_execute_plot(
            output_dir=str(simulation_output_dir),
            output_filename=output_file
        )
        
        print(f"✅ VisualizationAgent test completed")
        print(f"📊 Result: {result}")
        
        return True
        
    except Exception as e:
        print(f"💥 Error during VisualizationAgent test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_density_field_agent_with_executor():
    """Test DensityFieldAgent with automatic code execution."""
    print("\n🎨 Testing DensityFieldAgent with CodeExecutor")
    print("-" * 60)
    
    # Paths
    project_root = Path(__file__).parent.parent
    simulation_output_dir = project_root / "example" / "simulation_output" / "output"
    visualization_output_dir = project_root / "example" / "visualization_output"
    demo_file = project_root / "data" / "gaepsi2_demo.py"
    
    # Create visualization output directory
    visualization_output_dir.mkdir(exist_ok=True)
    
    # Check if demo file exists
    if not demo_file.exists():
        print(f"❌ Error: Demo file not found: {demo_file}")
        return False
    
    # Check simulation output
    if not simulation_output_dir.exists():
        print(f"❌ Error: Simulation output not found: {simulation_output_dir}")
        return False
    
    # List available PART directories
    part_dirs = list(simulation_output_dir.glob("PART_*"))
    if not part_dirs:
        print(f"❌ Error: No PART_* directories found in {simulation_output_dir}")
        return False
    
    try:
        # Create density field agent with RAG
        print(f"🤖 Creating DensityFieldAgent with RAG...")
        density_agent = DensityFieldAgent(
            gaepsi2_demo_path=str(demo_file)
        )
        
        # Test automatic code generation and execution
        snapshot_name = part_dirs[0].name
        print(f"🎯 Testing automatic density field generation for: {snapshot_name}")
        
        result = density_agent.generate_and_execute_density_field(
            simulation_output_dir=str(simulation_output_dir),
            output_dir=str(visualization_output_dir),
            snapshot_name=snapshot_name,
            particle_type=1  # Dark matter particles
        )
        
        print(f"✅ DensityFieldAgent test completed")
        print(f"📊 Result: {result}")
        
        # Clean up
        density_agent.cleanup()
        
        return True
        
    except Exception as e:
        print(f"💥 Error during DensityFieldAgent test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_shared_executor():
    """Test the SharedCodeExecutor singleton pattern."""
    print("\n🔧 Testing SharedCodeExecutor singleton")
    print("-" * 60)
    
    try:
        # Get two instances
        executor1 = SharedCodeExecutor.get_executor()
        executor2 = SharedCodeExecutor.get_executor()
        
        # They should be the same instance
        assert executor1 is executor2, "SharedCodeExecutor should be a singleton"
        print("✅ Singleton pattern working correctly")
        
        # Test simple code execution
        simple_code = "print('Hello from CodeExecutor!')"
        result = executor1.execute_code(simple_code)
        
        print(f"✅ Simple code execution test:")
        print(f"   Code: {simple_code}")
        print(f"   Result: {result.get('success', False)}")
        
        return True
        
    except Exception as e:
        print(f"💥 Error during SharedCodeExecutor test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests."""
    print("🚀 Testing CodeExecutor Integration with Agents")
    print("=" * 60)
    
    # Test SharedCodeExecutor
    shared_test = test_shared_executor()
    
    # Test VisualizationAgent
    viz_test = test_visualization_agent_with_executor()
    
    # Test DensityFieldAgent
    density_test = test_density_field_agent_with_executor()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print(f"   SharedCodeExecutor: {'✅ PASS' if shared_test else '❌ FAIL'}")
    print(f"   VisualizationAgent: {'✅ PASS' if viz_test else '❌ FAIL'}")
    print(f"   DensityFieldAgent:  {'✅ PASS' if density_test else '❌ FAIL'}")
    
    if all([shared_test, viz_test, density_test]):
        print("\n🎉 All tests passed! CodeExecutor integration is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the error messages above.")
    
    # Clean up shared executor
    try:
        SharedCodeExecutor.reset()
        print("\n🧹 Cleaned up shared resources")
    except Exception as e:
        print(f"\n⚠️ Warning: Failed to clean up: {e}")


if __name__ == "__main__":
    main()