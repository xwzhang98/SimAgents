import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .base_retriever import ParameterRetriever


class ParameterRetrievalComparison:
    """Framework for comparing different parameter retrieval methods."""
    
    def __init__(self, output_dir: str = "./comparison_results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results = []
        
    def add_retriever(self, retriever: ParameterRetriever, name: str = None):
        """Add a retriever to the comparison."""
        if not hasattr(self, 'retrievers'):
            self.retrievers = []
        
        retriever_name = name or retriever.__class__.__name__
        self.retrievers.append((retriever_name, retriever))
    
    def run_comparison(self, paper_content: str, paper_name: str = "paper", 
                      parallel: bool = True, custom_prompt: str = None) -> Dict[str, Any]:
        """Run all retrievers on the same paper content."""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        paper_dir = os.path.join(self.output_dir, f"{paper_name}_{timestamp}")
        os.makedirs(paper_dir, exist_ok=True)
        
        # Save the original paper content
        with open(os.path.join(paper_dir, "paper_content.txt"), "w") as f:
            f.write(paper_content)
        
        # Save custom prompt if provided
        if custom_prompt:
            with open(os.path.join(paper_dir, "custom_prompt.txt"), "w") as f:
                f.write(custom_prompt)
        
        results = {
            "paper_name": paper_name,
            "timestamp": timestamp,
            "custom_prompt": custom_prompt,
            "methods": {}
        }
        
        if parallel:
            # Run retrievers in parallel
            with ThreadPoolExecutor(max_workers=len(self.retrievers)) as executor:
                future_to_retriever = {}
                
                for name, retriever in self.retrievers:
                    future = executor.submit(self._run_single_retriever, 
                                           retriever, paper_content, name, custom_prompt)
                    future_to_retriever[future] = name
                
                for future in as_completed(future_to_retriever):
                    name = future_to_retriever[future]
                    try:
                        result = future.result()
                        results["methods"][name] = result
                        
                        # Save individual results
                        self._save_retriever_output(paper_dir, name, result)
                        
                    except Exception as e:
                        results["methods"][name] = {
                            "error": str(e),
                            "status": "failed"
                        }
        else:
            # Run retrievers sequentially
            for name, retriever in self.retrievers:
                try:
                    result = self._run_single_retriever(retriever, paper_content, name, custom_prompt)
                    results["methods"][name] = result
                    
                    # Save individual results
                    self._save_retriever_output(paper_dir, name, result)
                    
                except Exception as e:
                    results["methods"][name] = {
                        "error": str(e),
                        "status": "failed"
                    }

        
        self.results.append(results)
        return results
    
    def _run_single_retriever(self, retriever: ParameterRetriever, 
                            paper_content: str, name: str, custom_prompt: str = None) -> Dict[str, Any]:
        """Run a single retriever and measure performance."""
        
        start_time = time.time()
        
        try:
            parameters, reasoning = retriever.retrieve_parameters(paper_content, custom_prompt)
            end_time = time.time()
            
            return {
                "status": "success",
                "parameters": parameters,
                "reasoning": reasoning,
                "execution_time": end_time - start_time,
                "formatted_output": retriever.format_output(parameters, reasoning)
            }
        except Exception as e:
            end_time = time.time()
            return {
                "status": "failed",
                "error": str(e),
                "execution_time": end_time - start_time
            }
    
    def _save_retriever_output(self, paper_dir: str, method_name: str, result: Dict[str, Any]):
        """Save individual retriever output."""
        
        method_dir = os.path.join(paper_dir, method_name)
        os.makedirs(method_dir, exist_ok=True)
        
        if result["status"] == "success":
            # Save formatted output (similar to original save_message_to_files)
            with open(os.path.join(method_dir, "output.txt"), "w") as f:
                f.write(result["formatted_output"])
            
            # Save parameters as JSON
            with open(os.path.join(method_dir, "parameters.json"), "w") as f:
                json.dump(result["parameters"], f, indent=2)
            
            # Save reasoning
            with open(os.path.join(method_dir, "reasoning.txt"), "w") as f:
                f.write(result["reasoning"])
            
            # Create .genic and .gadget files if no errors
            if "errors" not in result["parameters"] or len(result["parameters"]["errors"]) == 0:
                self._create_config_files(method_dir, result["parameters"])
        
        # Save full result
        with open(os.path.join(method_dir, "full_result.json"), "w") as f:
            # Remove formatted_output from saved JSON to avoid duplication
            result_copy = result.copy()
            if "formatted_output" in result_copy:
                del result_copy["formatted_output"]
            json.dump(result_copy, f, indent=2)
    
    def _create_config_files(self, output_dir: str, parameters: Dict[str, Any]):
        """Create .genic and .gadget configuration files."""
        
        # Create .genic file
        if "genic" in parameters:
            genic_content = ""
            for key, value in parameters["genic"].items():
                genic_content += f"{key} = {value}\n"
            
            with open(os.path.join(output_dir, "sim.genic"), "w") as f:
                f.write(genic_content)
        
        # Create .gadget file
        if "gadget" in parameters:
            gadget_content = ""
            for key, value in parameters["gadget"].items():
                gadget_content += f"{key} = {value}\n"
            
            with open(os.path.join(output_dir, "sim.gadget"), "w") as f:
                f.write(gadget_content)