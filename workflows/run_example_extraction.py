#!/usr/bin/env python3
"""
Example script for running parameter extraction on the example paper.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from workflows.parameter_extraction import ParameterExtractionWorkflow


def main():
    """Run parameter extraction on the example paper."""
    
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    
    # Path to the example paper
    paper_path = project_root / "example" / "2105.01016v2.pdf"
    
    # Output directory inside example folder
    output_dir = project_root / "example" / "parameter_extraction_output"
    
    print("🚀 Running Parameter Extraction Workflow")
    print(f"📄 Paper: {paper_path}")
    print(f"📁 Output directory: {output_dir}")
    print("-" * 50)
    
    # Check if paper exists
    if not paper_path.exists():
        print(f"❌ Error: Paper not found at {paper_path}")
        return
    
    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        return
    
    try:
        # Get custom prompt from user input
        print("\n🤖 Custom Prompt (optional):")
        print("Enter a custom instruction for parameter extraction, or press Enter for default:")
        custom_prompt = input("Prompt: ").strip()
        
        # Use None if user didn't provide a prompt
        if not custom_prompt:
            custom_prompt ="Extract parameters for the low-resolution run mentioned in the paper"
        
        # Create workflow with custom prompt
        workflow = ParameterExtractionWorkflow(
            paper_path=str(paper_path),
            output_dir=str(output_dir),
            max_iterations=2,
            custom_prompt=custom_prompt
        )
        
        # Run extraction (custom prompt is already set in constructor)
        file_paths = workflow.run()
        
        print("\n🎉 Extraction completed successfully!")
        print("\n📁 Generated files:")
        for file_type, file_path in file_paths.items():
            print(f"  📄 {file_type.capitalize()}: {file_path}")
            
        print(f"\n✨ You can find the extracted parameters in: {output_dir}")
        
    except Exception as e:
        print(f"\n💥 Error during extraction: {e}")
        print("Please check your API key and try again.")


if __name__ == "__main__":
    main()