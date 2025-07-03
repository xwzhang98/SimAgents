#!/usr/bin/env python3
"""
Test script for the updated VisualizationAgent that plots power spectra.
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
    """Test the visualization agent with power spectrum plotting."""
    
    # Path to simulation output and visualization output
    simulation_output_dir = Path(__file__).parent.parent / "example" / "simulation_output" / "output"
    visualization_output_dir = Path(__file__).parent.parent / "example" / "visualization_output"
    
    # Create visualization output directory
    visualization_output_dir.mkdir(exist_ok=True)
    
    print("🎨 Testing VisualizationAgent Power Spectrum Plotting")
    print(f"📁 Looking for power spectrum files in: {simulation_output_dir}")
    print("-" * 60)
    
    # Check if directory exists
    if not simulation_output_dir.exists():
        print(f"❌ Error: Directory not found: {simulation_output_dir}")
        return
    
    # List power spectrum files
    import glob
    pattern = str(simulation_output_dir / "powerspectrum-*.txt")
    files = glob.glob(pattern)
    
    if not files:
        print(f"❌ No power spectrum files found matching pattern: powerspectrum-*.txt")
        return
    
    print(f"✅ Found {len(files)} power spectrum files:")
    for file in sorted(files):
        filename = Path(file).name
        # Extract scale factor
        scale_factor_str = filename.replace("powerspectrum-", "").replace(".txt", "")
        try:
            scale_factor = float(scale_factor_str)
            redshift = 1.0 / scale_factor - 1.0
            print(f"  📄 {filename} -> z = {redshift:.3f}")
        except ValueError:
            print(f"  ⚠️  {filename} -> Invalid scale factor")
    
    # Create visualization agent
    viz_agent = VisualizationAgent()
    
    try:
        # Test direct plotting method
        print(f"\n🚀 Plotting power spectra...")
        output_path = str(visualization_output_dir / "power_spectrum.png")
        viz_agent.plot_power_spectrum(
            output_dir=str(simulation_output_dir),
            output_filename=output_path
        )
        print(f"✅ Plot saved to: {output_path}")
        
        # Test message creation for specific redshift
        print(f"\n📝 Creating message for z=0 plotting:")
        message = viz_agent.create_power_spectrum_message(
            output_dir=str(simulation_output_dir),
            redshift=0.0,
            output_filename="z0_power_spectrum.png"
        )
        print("Generated message:")
        print("-" * 40)
        print(message)
        print("-" * 40)
        
        # Test message creation for all redshifts
        print(f"\n📝 Creating message for all redshifts:")
        message_all = viz_agent.create_power_spectrum_message(
            output_dir=str(simulation_output_dir),
            output_filename="all_power_spectra.png"
        )
        print("Generated message:")
        print("-" * 40)
        print(message_all)
        print("-" * 40)
        
        print(f"\n🎉 VisualizationAgent test completed successfully!")
        print(f"📊 Check the plot: {output_path}")
        
    except Exception as e:
        print(f"\n💥 Error during visualization: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()