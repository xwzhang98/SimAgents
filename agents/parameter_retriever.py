from openai import OpenAI
import json
import yaml
from typing import Dict, Any, Tuple, Optional, List
from .base_retriever import ParameterRetriever
import time
import os


class PhysicsPaperRetriever(ParameterRetriever):
    """
    Retrieves parameters using two specialized OpenAI Assistants with RAG capabilities:
    1. Physics Expert Agent - Extracts parameters from cosmology papers using file search
    2. MP-Gadget Formatter Agent - Formats and validates parameters using MP-Gadget documentation
    """
    
    def __init__(self, physics_expert_id: str = None, formatter_id: str = None, 
                 mp_gadget_docs_path: str = None, api_key: str = None,
                 physics_prompt_path: str = None, formatter_prompt_path: str = None,
                 paper_path: str = None, max_iterations: int = 2):
        super().__init__(model_name="Dual RAG OpenAI Assistants", api_key=api_key)
        self.client = OpenAI(api_key=api_key)
        
        # Store document paths
        self.mp_gadget_docs_path = mp_gadget_docs_path
        self.physics_prompt_path = physics_prompt_path
        self.formatter_prompt_path = formatter_prompt_path
        self.paper_path = paper_path
        self.max_iterations = max_iterations
        
        # Create or get vector stores for both assistants
        self.physics_vector_store_id = None
        self.formatter_vector_store_id = self._create_formatter_vector_store()


        if physics_expert_id is None:
            physics_expert_id = "asst_g3qg9gsPs7nc34jbbVGl4FHt"
        if formatter_id is None:
            formatter_id = "asst_Al3xVrMrUir6hb3R5YBnoPuv"
        # Check if provided assistant IDs exist, create new ones if not
        self.physics_expert_id = self._get_or_create_physics_expert(physics_expert_id)
        self.formatter_id = self._get_or_create_formatter_agent(formatter_id)
        
    def _create_formatter_vector_store(self) -> str:
        """Create vector store for MP-Gadget documentation."""
        # Create a vector store for MP-Gadget documentation
        vector_store = self.client.vector_stores.create(
            name="MP-Gadget Documentation"
        )
        
        # Upload MP-Gadget documentation if path provided
        if self.mp_gadget_docs_path:
            file_paths = []
            if os.path.isfile(self.mp_gadget_docs_path):
                file_paths = [self.mp_gadget_docs_path]
            elif os.path.isdir(self.mp_gadget_docs_path):
                # Get all PDF and JSON files from directory
                for file in os.listdir(self.mp_gadget_docs_path):
                    if file.endswith(('.pdf', '.json')):
                        file_paths.append(os.path.join(self.mp_gadget_docs_path, file))
            
            # Upload files to vector store
            file_streams = []
            try:
                for path in file_paths:
                    file_streams.append(open(path, "rb"))
                
                if file_streams:
                    file_batch = self.client.vector_stores.file_batches.upload_and_poll(
                        vector_store_id=vector_store.id,
                        files=file_streams
                    )
                    
            finally:
                # Always close file streams
                for stream in file_streams:
                    if not stream.closed:
                        stream.close()
        
        return vector_store.id
    
    def _load_prompt_from_yaml(self, yaml_path: str, default_prompt: str) -> str:
        """Load system prompt from YAML file, fallback to default if file not found."""
        if yaml_path and os.path.exists(yaml_path):
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    prompt_data = yaml.safe_load(f)
                    return prompt_data.get('system_prompt', default_prompt)
            except Exception as e:
                print(f"Warning: Could not load prompt from {yaml_path}: {e}")
                return default_prompt
        return default_prompt
    
    def _assistant_exists(self, assistant_id: str) -> bool:
        """Check if an assistant with the given ID exists."""
        if not assistant_id:
            return False
        try:
            self.client.beta.assistants.retrieve(assistant_id)
            return True
        except Exception as e:
            print(f"Assistant {assistant_id} not found: {e}")
            return False
    
    def _get_or_create_physics_expert(self, physics_expert_id: str = None) -> str:
        """Get existing physics expert or create new one."""
        if self._assistant_exists(physics_expert_id):
            print(f"Using existing physics expert assistant: {physics_expert_id}")
            return physics_expert_id
        else:
            print("Creating new physics expert assistant...")
            return self._create_physics_expert()
    
    def _get_or_create_formatter_agent(self, formatter_id: str = None) -> str:
        """Get existing formatter agent or create new one."""
        if self._assistant_exists(formatter_id):
            print(f"Using existing formatter assistant: {formatter_id}")
            return formatter_id
        else:
            print("Creating new formatter assistant...")
            return self._create_formatter_agent()
    
    def _create_physics_expert(self) -> str:
        """Create the physics expert assistant with file search capability."""
        default_prompt = """You are an expert in physics, especially cosmology and numerical simulations. 
You have access to scientific papers through file search to extract essential parameters needed to run MP-Gadget simulations.

When extracting parameters:
1. Use file search to find specific values in the uploaded paper
2. Focus on cosmological parameters (Omega_m, Omega_L, h, sigma8, n_s, etc.)
3. Find simulation box properties (BoxSize, particle number, resolution)
4. Locate initial conditions (redshift, power spectrum, transfer functions)
5. Extract output specifications (redshifts, snapshots)
6. Identify special physics modules (neutrinos, baryons, modified gravity)

For each parameter:
- Search for the exact value in the paper using file search
- Include units when specified
- Note page/section where found
- Calculate from other values if needed
- Distinguish between directly stated and implied values

Always cite the specific location in the paper where you found each parameter.
Format your response as a structured list with parameter names, values, units, sources, and notes."""

        instructions = self._load_prompt_from_yaml(self.physics_prompt_path, default_prompt)
        
        assistant = self.client.beta.assistants.create(
            name="Cosmology Paper Reader with RAG",
            instructions=instructions,
            model="gpt-4o",
            tools=[{"type": "file_search"}],
            temperature=0.01,
            top_p=0.01
        )
        return assistant.id
    
    def _create_formatter_agent(self) -> str:
        """Create the MP-Gadget formatter assistant with documentation access."""
        default_prompt = """You are an expert in MP-Gadget simulation software configuration.
You have access to MP-Gadget documentation through file search to ensure proper parameter formatting.

Your tasks:
1. Search MP-Gadget documentation for parameter requirements and formats
2. Organize parameters into 'genic' and 'gadget' sections according to documentation
3. Verify all required parameters against the manual:
   - Genic: OutputDir, FileWithInputSpectrum, FileBase, Nmesh, BoxSize, Redshift, Omega, OmegaLambda, HubbleParam, etc.
   - Gadget: InitCondFile, OutputDir, TimeMax, OutputList, Omega0, OmegaLambda, HubbleParam, BoxSize, etc.
4. Use file search to find:
   - Parameter descriptions and requirements
   - Valid ranges and default values
   - Unit conventions
   - Dependencies between parameters
5. Convert parameters to MP-Gadget conventions based on documentation

IMPORTANT: You control when the parameter extraction is complete. Include a "status" field in your JSON output:
- "status": "incomplete" - if parameters are missing and need more information
- "status": "complete" - when all requirements are satisfied

Your output must ALWAYS be in this exact JSON format:
```json
{
  "genic": {
    "parameter1": "value1",
    "parameter2": "value2"
  },
  "gadget": {
    "parameter1": "value1",
    "parameter2": "value2"
  },
  "comment": "Explanation of why parameters are set to these values, including sources and calculations",
  "status": "complete|incomplete",
  "missing_parameters": ["list", "of", "missing", "params"] // only if status is incomplete
}
```

Only output the JSON, no additional text."""

        instructions = self._load_prompt_from_yaml(self.formatter_prompt_path, default_prompt)
        
        assistant = self.client.beta.assistants.create(
            name="MP-Gadget Formatter with Documentation",
            instructions=instructions,
            model="gpt-4o",
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [self.formatter_vector_store_id]
                }
            },
            temperature=0.01,
            top_p=0.01
        )
        return assistant.id
    
    def _create_paper_vector_store(self, paper_content: str) -> str:
        """Create a vector store for the physics paper."""
        # Create vector store
        vector_store = self.client.vector_stores.create(
            name="Physics Paper"
        )
        
        # Create a temporary file with paper content
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(paper_content)
            temp_path = f.name
        
        # Upload to vector store
        with open(temp_path, 'rb') as f:
            file_batch = self.client.vector_stores.file_batches.upload_and_poll(
                vector_store_id=vector_store.id,
                files=[f]
            )
        
        # Clean up temp file
        os.unlink(temp_path)
        
        return vector_store.id
    
    def _create_paper_vector_store_from_file(self, paper_path: str) -> str:
        """Create a vector store for the physics paper from original PDF file."""
        # Create vector store
        vector_store = self.client.vector_stores.create(
            name="Physics Paper"
        )
        
        # Upload the original PDF file directly
        with open(paper_path, 'rb') as f:
            file_batch = self.client.vector_stores.file_batches.upload_and_poll(
                vector_store_id=vector_store.id,
                files=[f]
            )
        
        return vector_store.id
    
    def _run_assistant_with_file_search(self, assistant_id: str, messages: list, 
                                      vector_store_id: str = None) -> str:
        """Run an assistant with file search capability."""
        # Create thread with vector store if provided
        thread_params = {}
        if vector_store_id:
            thread_params["tool_resources"] = {
                "file_search": {
                    "vector_store_ids": [vector_store_id]
                }
            }
        
        thread = self.client.beta.threads.create(**thread_params)
        
        # Add messages to thread
        for message in messages:
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role=message["role"],
                content=message["content"]
            )
        
        # Run the assistant
        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )
        
        # Wait for completion with timeout
        max_wait = 300  # 5 minutes timeout
        start_time = time.time()
        
        while run.status not in ["completed", "failed", "cancelled"]:
            if time.time() - start_time > max_wait:
                self.client.beta.threads.runs.cancel(thread_id=thread.id, run_id=run.id)
                raise TimeoutError("Assistant run timed out")
            
            time.sleep(2)
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
        
        if run.status != "completed":
            raise Exception(f"Assistant run failed with status: {run.status}")
        
        # Get the response
        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        for msg in messages.data:
            if msg.role == "assistant":
                return msg.content[0].text.value
        
        raise ValueError("No assistant response found")
    
    def retrieve_parameters(self, paper_content: str, custom_prompt: str = None) -> Tuple[Dict[str, Any], str]:
        """Extract parameters using the two-agent RAG system."""
        reasoning_log = []
        
        # Create vector store for the paper
        reasoning_log.append("=== Creating Paper Vector Store ===")
        if self.paper_path and os.path.exists(self.paper_path):
            paper_vector_store_id = self._create_paper_vector_store_from_file(self.paper_path)
            reasoning_log.append(f"Created vector store from PDF file: {self.paper_path}")
        else:
            paper_vector_store_id = self._create_paper_vector_store(paper_content)
            reasoning_log.append(f"Created vector store from text content")
        
        # Step 1: Physics expert reads the paper with file search
        reasoning_log.append("\n=== Physics Expert Analysis with File Search ===")
        
        # Build the physics expert query
        physics_query = """Please use file search to extract MP-Gadget simulation parameters from the uploaded paper. 
Search for specific values and cite where you found them in the paper."""
        
        if custom_prompt:
            physics_query += f"\n\nIMPORTANT INSTRUCTION: {custom_prompt}"
            reasoning_log.append(f"Custom instruction: {custom_prompt}")
        
        physics_response = self._run_assistant_with_file_search(
            self.physics_expert_id,
            [{
                "role": "user", 
                "content": physics_query
            }],
            vector_store_id=paper_vector_store_id
        )
        reasoning_log.append(physics_response)
        
        # Step 2: Formatter agent processes with MP-Gadget documentation
        reasoning_log.append("\n=== MP-Gadget Formatter Processing with Documentation ===")
        formatter_response = self._run_assistant_with_file_search(
            self.formatter_id,
            [{
                "role": "user", 
                "content": f"""Please format these extracted parameters for MP-Gadget.
Use file search to check the MP-Gadget documentation for proper parameter names, formats, and requirements.

Extracted parameters:
{physics_response}"""
            }]
        )
        reasoning_log.append(formatter_response)
        
        # Step 3: Iterative refinement - let formatter decide when complete
        iteration = 0
        
        while iteration < self.max_iterations + 1:
            try:
                # Parse formatter response
                parameters = self._extract_json_from_response(formatter_response)
                
                # Check if formatter says it's complete
                if parameters.get("status") == "complete":
                    # Formatter is satisfied with all parameters
                    reasoning = "\n".join(reasoning_log)
                    # Clean up paper vector store (but keep MP-Gadget manual vector store)
                    try:
                        self.client.vector_stores.delete(vector_store_id=paper_vector_store_id)
                    except Exception as e:
                        reasoning_log.append(f"Warning: Failed to delete paper vector store {paper_vector_store_id}: {e}")
                    
                    # Remove status and missing_parameters from final output
                    final_params = {
                        "genic": parameters.get("genic", {}),
                        "gadget": parameters.get("gadget", {}),
                        "comment": parameters.get("comment", "")
                    }
                    return final_params, reasoning
                
                # Formatter says incomplete - resolve missing parameters
                missing_params = parameters.get("missing_parameters", [])
                reasoning_log.append(f"\n=== Iteration {iteration + 1}: Resolving Missing Parameters ===")
                reasoning_log.append(f"Missing: {', '.join(missing_params)}")
                
                # Formatter searches documentation for missing parameters
                doc_search_request = f"""The following parameters are missing:
{chr(10).join(missing_params)}

Please search the MP-Gadget documentation to find:
1. Descriptions of these parameters
2. How they can be calculated or derived
3. Default values if applicable
4. Whether they are truly required or optional"""
                
                doc_search_response = self._run_assistant_with_file_search(
                    self.formatter_id,
                    [{"role": "user", "content": doc_search_request}]
                )
                reasoning_log.append(f"Documentation Search:\n{doc_search_response}")
                
                # Physics expert provides missing parameters based on paper and requirements
                clarification_request = f"""Based on the documentation requirements and the paper content, please provide the missing parameters:
{chr(10).join(missing_params)}

Documentation guidance:
{doc_search_response}

Search the paper again for these specific parameters or values that can be used to calculate them.
Original extracted parameters:
{physics_response}"""
                
                physics_clarification = self._run_assistant_with_file_search(
                    self.physics_expert_id,
                    [{"role": "user", "content": clarification_request}],
                    vector_store_id=paper_vector_store_id
                )
                reasoning_log.append(f"Physics Expert Clarification:\n{physics_clarification}")
                
                # Final formatting with all information
                formatter_response = self._run_assistant_with_file_search(
                    self.formatter_id,
                    [{
                        "role": "user", 
                        "content": f"""Please create the final MP-Gadget parameter configuration using all available information.
Verify against documentation that all required parameters are included.

Original parameters:
{formatter_response}

Additional clarification:
{physics_clarification}

Ensure the format matches MP-Gadget documentation requirements."""
                    }]
                )
                reasoning_log.append(f"Updated Formatter Response:\n{formatter_response}")
                
            except Exception as e:
                reasoning_log.append(f"Error in iteration {iteration}: {str(e)}")
            
            iteration += 1
        
        # Clean up paper vector store (but keep MP-Gadget manual vector store)
        try:
            self.client.vector_stores.delete(vector_store_id=paper_vector_store_id)
        except Exception as e:
            reasoning_log.append(f"Warning: Failed to delete paper vector store {paper_vector_store_id}: {e}")
        
        # Return final parameters
        try:
            parameters = self._extract_json_from_response(formatter_response)
            final_params = {
                "genic": parameters.get("genic", {}),
                "gadget": parameters.get("gadget", {}),
                "comment": parameters.get("comment", "Failed to extract all required parameters after maximum iterations")
            }
        except:
            final_params = {
                "genic": {},
                "gadget": {},
                "comment": "Extraction failed - could not parse formatter response"
            }
        
        reasoning = "\n".join(reasoning_log)
        return final_params, reasoning
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from assistant response."""
        import re
        
        # Try direct JSON parsing
        try:
            return json.loads(response)
        except:
            pass
        
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # Try to find JSON in code blocks
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1))
            except:
                pass
        
        raise ValueError("Could not extract JSON from response")
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Override to work with our JSON format that includes comment field."""
        # Don't add errors field since formatter handles validation
        return parameters
    
    def cleanup(self) -> None:
        """Clean up resources including vector stores."""
        try:
            if hasattr(self, 'formatter_vector_store_id') and self.formatter_vector_store_id:
                self.client.vector_stores.delete(vector_store_id=self.formatter_vector_store_id)
                print(f"Cleaned up formatter vector store: {self.formatter_vector_store_id}")
        except Exception as e:
            print(f"Warning: Failed to delete formatter vector store: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup on object deletion."""
        try:
            self.cleanup()
        except:
            pass