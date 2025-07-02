from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
import json
from datetime import datetime


class ParameterRetriever(ABC):
    """Base class for parameter retrieval methods from scientific papers."""
    
    def __init__(self, model_name: str = "gpt-4o", api_key: str = None):
        self.model_name = model_name
        self.api_key = api_key
        self.method_name = self.__class__.__name__
        
    @abstractmethod
    def retrieve_parameters(self, paper_content: str, custom_prompt: str = None) -> Tuple[Dict[str, Any], str]:
        """
        Extract MP-Gadget parameters from paper content.
        
        Args:
            paper_content: The text content of the scientific paper
            custom_prompt: Optional custom prompt to specify which simulation to extract
                          (e.g., "Focus on the simulation run named 'L100N512'")
            
        Returns:
            Tuple of (parameters_dict, reasoning_text)
            parameters_dict should contain 'genic' and 'gadget' sections
        """
        pass
    
    def format_output(self, parameters: Dict[str, Any], reasoning: str) -> str:
        """Format the output in the standard format for saving."""
        output = {
            "method": self.method_name,
            "timestamp": datetime.now().isoformat(),
            "parameters": parameters,
            "reasoning": reasoning
        }
        
        # Match the existing format from save_message_to_files
        formatted_content = f"{json.dumps(parameters, indent=2)}\n---\n"
        formatted_content += f"**Parameter Extraction Reasoning ({self.method_name}):**\n"
        formatted_content += reasoning
        
        return formatted_content
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that parameters contain required fields."""
        required_genic = ["OutputDir", "FileWithInputSpectrum", "FileBase", "Nmesh", "BoxSize"]
        required_gadget = ["InitCondFile", "OutputDir", "TimeMax", "OutputList"]
        
        errors = []
        
        if "genic" not in parameters:
            errors.append("Missing 'genic' section")
        else:
            for field in required_genic:
                if field not in parameters["genic"]:
                    errors.append(f"Missing genic field: {field}")
        
        if "gadget" not in parameters:
            errors.append("Missing 'gadget' section")
        else:
            for field in required_gadget:
                if field not in parameters["gadget"]:
                    errors.append(f"Missing gadget field: {field}")
        
        parameters["errors"] = errors
        return parameters