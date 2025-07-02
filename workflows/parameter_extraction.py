#!/usr/bin/env python3
"""
Parameter Extraction Workflow

This workflow extracts MP-Gadget simulation parameters from scientific papers
using the PhysicsPaperRetriever agent and saves them as separate JSON files.
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the parent directory to the path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from agents.parameter_retriever import PhysicsPaperRetriever


class ParameterExtractionWorkflow:
    """Workflow for extracting parameters from scientific papers."""
    
    def __init__(
        self,
        paper_path: str,
        output_dir: str = "output",
        api_key: Optional[str] = None,
        mp_gadget_docs_path: Optional[str] = None,
        max_iterations: int = 2,
        custom_prompt: Optional[str] = None
    ):
        """
        Initialize the parameter extraction workflow.
        
        Args:
            paper_path: Path to the PDF paper
            output_dir: Directory to save output files
            api_key: OpenAI API key (if None, uses environment variable)
            mp_gadget_docs_path: Path to MP-Gadget documentation
            max_iterations: Maximum iterations for parameter refinement
            custom_prompt: Custom instruction for parameter extraction
        """
        self.paper_path = paper_path
        self.output_dir = Path(output_dir)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.mp_gadget_docs_path = mp_gadget_docs_path
        self.max_iterations = max_iterations
        self.custom_prompt = custom_prompt
        
        # Validate inputs
        if not os.path.exists(paper_path):
            raise FileNotFoundError(f"Paper not found: {paper_path}")
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize the retriever
        self.retriever = PhysicsPaperRetriever(
            paper_path=paper_path,
            api_key=self.api_key,
            mp_gadget_docs_path=mp_gadget_docs_path,
            max_iterations=max_iterations
        )
    
    def extract_parameters(self, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract parameters from the paper.
        
        Args:
            custom_prompt: Optional custom instruction for parameter extraction
            
        Returns:
            Dictionary containing extracted parameters
        """
        print("🔬 Starting parameter extraction...")
        print(f"📄 Processing paper: {self.paper_path}")
        
        # Read paper content (for text-based extraction if needed)
        paper_content = f"PDF file: {self.paper_path}"
        
        # Use custom prompt from constructor or parameter
        prompt_to_use = custom_prompt or self.custom_prompt
        
        # Extract parameters
        parameters, reasoning = self.retriever.retrieve_parameters(
            paper_content=paper_content,
            custom_prompt=prompt_to_use
        )
        
        print("✅ Parameter extraction completed!")
        return {
            "parameters": parameters,
            "reasoning": reasoning
        }
    
    def save_parameters(self, extraction_result: Dict[str, Any], custom_prompt: Optional[str] = None) -> Dict[str, str]:
        """
        Save extracted parameters to separate JSON files.
        
        Args:
            extraction_result: Result from extract_parameters()
            custom_prompt: Custom prompt used (for logging)
            
        Returns:
            Dictionary with file paths
        """
        parameters = extraction_result["parameters"]
        reasoning = extraction_result["reasoning"]
        
        # Generate base filename from paper name
        paper_name = Path(self.paper_path).stem
        
        # Save genic parameters
        genic_file = self.output_dir / f"{paper_name}_genic.json"
        genic_data = {
            "source": self.paper_path,
            "parameters": parameters.get("genic", {})
        }
        
        with open(genic_file, 'w', encoding='utf-8') as f:
            json.dump(genic_data, f, indent=2, ensure_ascii=False)
        
        # Save gadget parameters
        gadget_file = self.output_dir / f"{paper_name}_gadget.json"
        gadget_data = {
            "source": self.paper_path,
            "parameters": parameters.get("gadget", {})
        }
        
        with open(gadget_file, 'w', encoding='utf-8') as f:
            json.dump(gadget_data, f, indent=2, ensure_ascii=False)
        
        file_paths = {
            "genic": str(genic_file),
            "gadget": str(gadget_file)
        }
        
        print(f"💾 Saved genic parameters: {genic_file}")
        print(f"💾 Saved gadget parameters: {gadget_file}")
        
        return file_paths
    
    def run(self, custom_prompt: Optional[str] = None) -> Dict[str, str]:
        """
        Run the complete parameter extraction workflow.
        
        Args:
            custom_prompt: Optional custom instruction for parameter extraction
            
        Returns:
            Dictionary with file paths of saved outputs
        """
        try:
            # Extract parameters
            extraction_result = self.extract_parameters(custom_prompt)
            
            # Save to files
            file_paths = self.save_parameters(extraction_result, custom_prompt)
            
            print("🎉 Parameter extraction workflow completed successfully!")
            return file_paths
            
        except Exception as e:
            print(f"❌ Error in parameter extraction workflow: {e}")
            raise
        finally:
            # Clean up resources
            self.retriever.cleanup()
    
    def cleanup(self):
        """Clean up workflow resources."""
        if hasattr(self, 'retriever'):
            self.retriever.cleanup()


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract MP-Gadget parameters from scientific papers")
    parser.add_argument("paper_path", help="Path to the PDF paper")
    parser.add_argument("--output-dir", default="output", help="Output directory (default: output)")
    parser.add_argument("--custom-prompt", help="Custom instruction for parameter extraction")
    parser.add_argument("--mp-gadget-docs", help="Path to MP-Gadget documentation")
    parser.add_argument("--max-iterations", type=int, default=2, help="Maximum iterations for refinement")
    
    args = parser.parse_args()
    
    # Create and run workflow
    workflow = ParameterExtractionWorkflow(
        paper_path=args.paper_path,
        output_dir=args.output_dir,
        mp_gadget_docs_path=args.mp_gadget_docs,
        max_iterations=args.max_iterations,
        custom_prompt=args.custom_prompt
    )
    
    try:
        file_paths = workflow.run()
        print("\n📁 Output files:")
        for file_type, file_path in file_paths.items():
            print(f"  {file_type}: {file_path}")
    except KeyboardInterrupt:
        print("\n⚠️  Workflow interrupted by user")
    except Exception as e:
        print(f"\n💥 Workflow failed: {e}")
        sys.exit(1)
    finally:
        workflow.cleanup()


if __name__ == "__main__":
    main()