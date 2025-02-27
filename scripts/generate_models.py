#!/usr/bin/env python3
"""
Generate Python data models from OpenAPI specification.
"""

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple


# ANSI color codes for terminal output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_header(text: str) -> None:
    """Print a section header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD} {text} {Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")


def print_step(step: str) -> None:
    """Print a step in the process."""
    print(f"{Colors.BLUE}➤ {step}{Colors.ENDC}")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.ENDC}", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.ENDC}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"{Colors.CYAN}ℹ {message}{Colors.ENDC}")


def fix_mutable_defaults(content: str) -> Tuple[str, int]:
    """
    Fix mutable default values in dataclasses by replacing them with default_factory.
    
    Args:
        content: The content of the generated file
        
    Returns:
        Tuple of (modified_content, number_of_fixes)
    """
    fixes_applied = 0
    
    # Fix 1: Replace mutable default values with default_factory
    # Pattern for empty list defaults: field_name: Optional[List[...]] = []
    list_pattern = r'(\s+)(\w+): Optional\[List\[(.*?)\]\] = \[\]'
    list_replacement = r'\1\2: Optional[List[\3]] = field(default_factory=list)'
    
    # Count matches before replacement
    list_matches = len(re.findall(list_pattern, content))
    # Apply replacement
    content = re.sub(list_pattern, list_replacement, content)
    fixes_applied += list_matches
    
    # Pattern for empty dict defaults: field_name: Optional[Dict[...]] = {}
    dict_pattern = r'(\s+)(\w+): Optional\[Dict\[(.*?)\]\] = \{\}'
    dict_replacement = r'\1\2: Optional[Dict[\3]] = field(default_factory=dict)'
    
    # Count matches before replacement
    dict_matches = len(re.findall(dict_pattern, content))
    # Apply replacement
    content = re.sub(dict_pattern, dict_replacement, content)
    fixes_applied += dict_matches
    
    # Also handle non-Optional List and Dict defaults
    simple_list_pattern = r'(\s+)(\w+): List\[(.*?)\] = \[\]'
    simple_list_replacement = r'\1\2: List[\3] = field(default_factory=list)'
    
    simple_list_matches = len(re.findall(simple_list_pattern, content))
    content = re.sub(simple_list_pattern, simple_list_replacement, content)
    fixes_applied += simple_list_matches
    
    simple_dict_pattern = r'(\s+)(\w+): Dict\[(.*?)\] = \{\}'
    simple_dict_replacement = r'\1\2: Dict[\3] = field(default_factory=dict)'
    
    simple_dict_matches = len(re.findall(simple_dict_pattern, content))
    content = re.sub(simple_dict_pattern, simple_dict_replacement, content)
    fixes_applied += simple_dict_matches
    
    return content, fixes_applied


def fix_inheritance_issues(content: str) -> Tuple[str, int]:
    """
    Fix inheritance issues in dataclasses by flattening the class hierarchy.
    
    Args:
        content: The content of the generated file
        
    Returns:
        Tuple of (modified_content, number_of_fixes)
    """
    # First, extract all dataclass definitions
    dataclass_pattern = r'@dataclass\s+class\s+(\w+)(?:\((\w+)\))?\s*:\s*([^@]*?)(?=@|\Z)'
    dataclasses = re.findall(dataclass_pattern, content, re.DOTALL)
    
    # Build a map of class name to its fields
    class_fields: Dict[str, List[Tuple[str, str, str]]] = {}
    for class_name, parent_class, class_body in dataclasses:
        # Extract fields from the class body with their default values if any
        field_pattern = r'^\s+(\w+):\s+(.*?)(?:(?:\s*=\s*(.*?))?$)'
        fields = re.findall(field_pattern, class_body, re.MULTILINE)
        class_fields[class_name] = [(name, type_, default.strip() if default else None) for name, type_, default in fields]
    
    # Build inheritance hierarchy
    inheritance: Dict[str, str] = {}
    for class_name, parent_class, _ in dataclasses:
        if parent_class:
            inheritance[class_name] = parent_class
    
    # Identify classes that need flattening (those with inheritance)
    classes_to_flatten = set(inheritance.keys())
    
    # No classes to flatten
    if not classes_to_flatten:
        return content, 0
    
    # For each class that needs flattening, collect all fields from parent classes
    flattened_fields: Dict[str, List[Tuple[str, str, str]]] = {}
    for class_name in classes_to_flatten:
        fields = []
        current = class_name
        
        # Traverse up the inheritance chain
        visited = set()
        while current in inheritance and current not in visited:
            visited.add(current)
            parent = inheritance[current]
            if parent in class_fields:
                # Add parent fields first
                fields = class_fields[parent] + fields
            current = parent
        
        # Add the class's own fields
        if class_name in class_fields:
            fields += class_fields[class_name]
        
        # Remove duplicates (keep the last occurrence of each field name)
        seen = set()
        unique_fields = []
        for field in reversed(fields):
            name, type_, default = field
            if name not in seen:
                seen.add(name)
                unique_fields.append(field)
        
        # Sort fields: required fields first, then optional fields
        required_fields = []
        optional_fields = []
        
        for field in reversed(unique_fields):
            name, type_, default = field
            if default is None:
                required_fields.append(field)
            else:
                optional_fields.append(field)
        
        flattened_fields[class_name] = required_fields + optional_fields
    
    # Now replace each class definition with a flattened version
    for class_name in classes_to_flatten:
        # Find the original class definition
        class_pattern = rf'@dataclass\s+class\s+{class_name}\({inheritance[class_name]}\)\s*:\s*([^@]*?)(?=@|\Z)'
        class_match = re.search(class_pattern, content, re.DOTALL)
        
        if class_match:
            # Create a new class body with all fields
            new_body = ""
            
            # Add all fields from the flattened hierarchy
            for field_name, field_type, default in flattened_fields[class_name]:
                if default:
                    new_body += f"    {field_name}: {field_type} = {default}\n"
                else:
                    new_body += f"    {field_name}: {field_type}\n"
            
            # Replace the class definition
            new_class_def = f"@dataclass\nclass {class_name}:\n{new_body}"
            content = content.replace(class_match.group(0), new_class_def)
    
    return content, len(classes_to_flatten)


def manually_fix_models(content: str) -> Tuple[str, int]:
    """
    Manually fix specific models based on the OpenAPI specification.
    
    Args:
        content: The content of the generated file
        
    Returns:
        Tuple of (modified_content, number_of_fixes)
    """
    fixes_applied = 0
    
    # Fix ChatRequest - handle both with and without inheritance
    chat_request_pattern = r'@dataclass\s+class\s+ChatRequest(?:\(Request\))?\s*:\s*([^@]*?)(?=@|\Z)'
    chat_request_match = re.search(chat_request_pattern, content, re.DOTALL)
    if chat_request_match:
        new_chat_request = """@dataclass
class ChatRequest:
    request_id: str
    input: str
    logging_level: Optional[str] = None
    request_metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
"""
        content = content.replace(chat_request_match.group(0), new_chat_request)
        fixes_applied += 1
    
    # Fix ConfigureRequest
    configure_request_pattern = r'@dataclass\s+class\s+ConfigureRequest(?:\(Request\))?\s*:\s*([^@]*?)(?=@|\Z)'
    configure_request_match = re.search(configure_request_pattern, content, re.DOTALL)
    if configure_request_match:
        new_configure_request = """@dataclass
class ConfigureRequest:
    request_id: str
    args: Dict[str, Any]
    logging_level: Optional[str] = None
    request_metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
"""
        content = content.replace(configure_request_match.group(0), new_configure_request)
        fixes_applied += 1
    
    # Fix CancelRequest
    cancel_request_pattern = r'@dataclass\s+class\s+CancelRequest(?:\(Request\))?\s*:\s*([^@]*?)(?=@|\Z)'
    cancel_request_match = re.search(cancel_request_pattern, content, re.DOTALL)
    if cancel_request_match:
        new_cancel_request = """@dataclass
class CancelRequest:
    request_id: str
    logging_level: Optional[str] = None
    request_metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
"""
        content = content.replace(cancel_request_match.group(0), new_cancel_request)
        fixes_applied += 1
    
    # Fix ResumeWithInput
    resume_with_input_pattern = r'@dataclass\s+class\s+ResumeWithInput(?:\(Request\))?\s*:\s*([^@]*?)(?=@|\Z)'
    resume_with_input_match = re.search(resume_with_input_pattern, content, re.DOTALL)
    if resume_with_input_match:
        new_resume_with_input = """@dataclass
class ResumeWithInput:
    request_id: str
    request_keys: Dict[str, Any]
    logging_level: Optional[str] = None
    request_metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
"""
        content = content.replace(resume_with_input_match.group(0), new_resume_with_input)
        fixes_applied += 1
    
    # Fix RequestStarted
    request_started_pattern = r'@dataclass\s+class\s+RequestStarted(?:\(Event\))?\s*:\s*([^@]*?)(?=@|\Z)'
    request_started_match = re.search(request_started_pattern, content, re.DOTALL)
    if request_started_match:
        new_request_started = """@dataclass
class RequestStarted:
    id: int
    run_id: str
    agent: str
    type: str
    request_id: str
    depth: Optional[int] = 0
    timestamp: Optional[str] = None
"""
        content = content.replace(request_started_match.group(0), new_request_started)
        fixes_applied += 1
    
    # Fix WaitForInput
    wait_for_input_pattern = r'@dataclass\s+class\s+WaitForInput(?:\(Event\))?\s*:\s*([^@]*?)(?=@|\Z)'
    wait_for_input_match = re.search(wait_for_input_pattern, content, re.DOTALL)
    if wait_for_input_match:
        new_wait_for_input = """@dataclass
class WaitForInput:
    id: int
    run_id: str
    agent: str
    type: str
    request_keys: Dict[str, str]
    depth: Optional[int] = 0
    timestamp: Optional[str] = None
"""
        content = content.replace(wait_for_input_match.group(0), new_wait_for_input)
        fixes_applied += 1
    
    # Fix TextOutput
    text_output_pattern = r'@dataclass\s+class\s+TextOutput(?:\(Event\))?\s*:\s*([^@]*?)(?=@|\Z)'
    text_output_match = re.search(text_output_pattern, content, re.DOTALL)
    if text_output_match:
        new_text_output = """@dataclass
class TextOutput:
    id: int
    run_id: str
    agent: str
    type: str
    content: str
    depth: Optional[int] = 0
    timestamp: Optional[str] = None
"""
        content = content.replace(text_output_match.group(0), new_text_output)
        fixes_applied += 1
    
    # Fix ToolCall
    tool_call_pattern = r'@dataclass\s+class\s+ToolCall(?:\(Event\))?\s*:\s*([^@]*?)(?=@|\Z)'
    tool_call_match = re.search(tool_call_pattern, content, re.DOTALL)
    if tool_call_match:
        new_tool_call = """@dataclass
class ToolCall:
    id: int
    run_id: str
    agent: str
    type: str
    function_name: str
    args: Dict[str, Any]
    depth: Optional[int] = 0
    timestamp: Optional[str] = None
"""
        content = content.replace(tool_call_match.group(0), new_tool_call)
        fixes_applied += 1
    
    # Fix ToolResult
    tool_result_pattern = r'@dataclass\s+class\s+ToolResult(?:\(Event\))?\s*:\s*([^@]*?)(?=@|\Z)'
    tool_result_match = re.search(tool_result_pattern, content, re.DOTALL)
    if tool_result_match:
        new_tool_result = """@dataclass
class ToolResult:
    id: int
    run_id: str
    agent: str
    type: str
    function_name: str
    text_result: str
    depth: Optional[int] = 0
    timestamp: Optional[str] = None
"""
        content = content.replace(tool_result_match.group(0), new_tool_result)
        fixes_applied += 1
    
    # Fix ArtifactGenerated
    artifact_generated_pattern = r'@dataclass\s+class\s+ArtifactGenerated(?:\(Event\))?\s*:\s*([^@]*?)(?=@|\Z)'
    artifact_generated_match = re.search(artifact_generated_pattern, content, re.DOTALL)
    if artifact_generated_match:
        new_artifact_generated = """@dataclass
class ArtifactGenerated:
    id: int
    run_id: str
    agent: str
    type: str
    name: str
    artifact_id: str
    url: str
    mime_type: str
    depth: Optional[int] = 0
    timestamp: Optional[str] = None
"""
        content = content.replace(artifact_generated_match.group(0), new_artifact_generated)
        fixes_applied += 1
    
    # Fix OperationComplete
    operation_complete_pattern = r'@dataclass\s+class\s+OperationComplete(?:\(Event\))?\s*:\s*([^@]*?)(?=@|\Z)'
    operation_complete_match = re.search(operation_complete_pattern, content, re.DOTALL)
    if operation_complete_match:
        new_operation_complete = """@dataclass
class OperationComplete:
    id: int
    run_id: str
    agent: str
    type: str
    finish_reason: FinishReason
    depth: Optional[int] = 0
    timestamp: Optional[str] = None
"""
        content = content.replace(operation_complete_match.group(0), new_operation_complete)
        fixes_applied += 1
    
    return content, fixes_applied


def post_process_generated_file(file_path: Path) -> int:
    """
    Post-process the generated file to fix common issues:
    1. Replace mutable default values with default_factory
    2. Fix inheritance issues with non-default arguments by manually fixing models
    
    Returns the number of fixes applied.
    """
    print_step("Post-processing generated file to fix common issues...")
    
    with open(file_path, "r") as f:
        content = f.read()
    
    total_fixes = 0
    
    # Fix mutable default values
    content, mutable_fixes = fix_mutable_defaults(content)
    if mutable_fixes > 0:
        print_success(f"Applied {mutable_fixes} fixes for mutable default values")
        total_fixes += mutable_fixes
    else:
        print_info("No mutable default values found that needed fixing")
    
    # Manually fix models based on the OpenAPI specification
    content, manual_fixes = manually_fix_models(content)
    if manual_fixes > 0:
        print_success(f"Manually fixed {manual_fixes} models based on the OpenAPI specification")
        total_fixes += manual_fixes
    else:
        print_info("No models needed manual fixing")
    
    # Write the modified content back to the file
    with open(file_path, "w") as f:
        f.write(content)
    
    return total_fixes


def main():
    """Generate Python models from OpenAPI spec."""
    print_header("Agent Protocol Model Generator")
    
    # Ensure we're running from the project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Paths
    openapi_spec = project_root / "specs" / "openapi.yaml"
    output_dir = project_root / "src" / "agent_protocol" / "models"
    output_file = output_dir / "generated.py"
    
    # Check if OpenAPI spec exists
    if not openapi_spec.exists():
        print_error(f"OpenAPI specification not found at {openapi_spec}")
        print_info("Please create the OpenAPI specification file first.")
        return 1
    
    # Ensure the output directory exists
    print_step("Ensuring output directory exists...")
    output_dir.mkdir(exist_ok=True)
    
    # Generate the models
    print_step("Generating models from OpenAPI specification...")
    cmd = [
        "datamodel-codegen",
        "--input", str(openapi_spec),
        "--input-file-type", "openapi",
        "--output", str(output_file),
        "--output-model-type", "dataclasses.dataclass",
        "--target-python-version", "3.11",
        "--disable-timestamp",
        "--use-schema-description",
        "--field-constraints",
    ]
    
    print_info(f"Running command: {' '.join(cmd)}")
    
    try:
        start_time = time.time()
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Check if the generated file exists and has content
        if output_file.exists() and output_file.stat().st_size > 0:
            # Post-process the generated file to fix common issues
            print_step("Automatically fixing common issues in generated models...")
            fixes_applied = post_process_generated_file(output_file)
            
            # Create an __init__.py file to expose the generated models
            print_step("Creating __init__.py file...")
            with open(output_dir / "__init__.py", "w") as f:
                f.write("from .generated import *  # noqa\n")
            
            # Count the number of models generated
            with open(output_file, "r") as f:
                content = f.read()
                dataclass_count = content.count("@dataclass")
                enum_count = content.count("class") - dataclass_count
            
            end_time = time.time()
            print_success(f"Successfully generated {dataclass_count} dataclasses and {enum_count} enums")
            if fixes_applied > 0:
                print_success(f"Applied {fixes_applied} automatic fixes to ensure compatibility")
            print_success(f"Generation completed in {end_time - start_time:.2f} seconds")
            
            print_info(f"Generated models are available at: {output_file}")
            print_info("You can test the models with: poetry run python scripts/test_models.py")
            
            return 0
        else:
            print_error("Generated file is empty or does not exist")
            return 1
            
    except subprocess.CalledProcessError as e:
        print_error(f"Error generating models: {e}")
        if e.stdout:
            print_info("Command output:")
            print(e.stdout)
        if e.stderr:
            print_error("Command error output:")
            print(e.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 