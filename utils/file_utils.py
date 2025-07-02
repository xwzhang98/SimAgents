import json
import os
from typing import Dict, Any


def save_message_to_files(
    message: str,
    base_path: str = "/hildafs/home/xzhangn/xzhangn/LLM/5-multiagent/output/"
) -> Dict[str, str]:
    """
    Save simulation configuration message to .genic and .gadget files.
    
    Args:
        message: JSON message containing simulation parameters
        base_path: Base directory path for output
        
    Returns:
        Dictionary with paths to created files
    """
    if not base_path.endswith("/"):
        base_path += "/"
    
    # Extract the JSON part (everything before the "---")
    json_str = message.split("---")[0]
    data = json.loads(json_str)
    
    output_dir = base_path + "sim_output/"
    
    # Default paths
    file_with_transfer_function = "/hildafs/projects/phy200018p/xzhangn/source/MP-Gadget/examples/class_tk_99.dat"
    file_base = "ICs"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Save .genic file
    genic_path = f"{base_path}output.genic"
    with open(genic_path, 'w') as f:
        for key, value in data['genic'].items():
            if key == "OutputDir":
                f.write(f"{key} = {output_dir}\n")
            elif key == "FileWithInputSpectrum":
                file_with_input_spectrum = base_path + value
                f.write(f"{key} = {file_with_input_spectrum}\n")
            elif key == "FileBase":
                f.write(f"{key} = {file_base}\n")
            elif key == "FileWithTransferFunction":
                f.write(f"{key} = {file_with_transfer_function}\n")
            else:
                f.write(f"{key} = {value}\n")
        f.write("FileWithTransferFunction = " + file_with_transfer_function + "\n")
    
    # Save .gadget file
    gadget_path = f"{base_path}output.gadget"
    with open(gadget_path, 'w') as f:
        for key, value in data['gadget'].items():
            if key == "InitCondFile":
                f.write(f"{key} = {output_dir}{file_base}\n")
            elif key == "OutputDir":
                f.write(f"{key} = {output_dir}\n")
            else:
                f.write(f"{key} = {value}\n")
    
    # Save error messages
    error_path = f"{base_path}error_messages.txt"
    with open(error_path, 'w') as f:
        f.write("Error Messages:\n")
        f.write("==============\n\n")
        for error in data.get('errors', []):
            f.write(f"- {error}\n")
        
        # Add the reasoning part if present
        if "**Parameter Extraction Reasoning:**" in message:
            f.write("\nParameter Extraction Reasoning:\n")
            f.write("============================\n\n")
            reasoning = message.split("**Parameter Extraction Reasoning:**")[1].strip()
            for line in reasoning.split('\n'):
                if line.strip():
                    f.write(f"{line.strip()}\n")
    
    return {
        "genic_path": genic_path,
        "gadget_path": gadget_path,
        "error_path": error_path,
        "output_dir": output_dir
    }