#!/usr/bin/env python3
"""
Test script to verify that the generated models can be imported and used.
"""

import json
from datetime import datetime
from typing import Any, Dict

from agent_protocol.models import (
    AgentDescriptor,
    AgentOperation,
    ArtifactGenerated,
    CancelRequest,
    ChatRequest,
    ConfigureRequest,
    Event,
    FinishReason,
    OperationComplete,
    Request,
    RequestStarted,
    ResumeWithInput,
    TextOutput,
    ToolCall,
    ToolResult,
    WaitForInput,
)


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


def format_model(obj: Any) -> str:
    """Format a model instance for display."""
    # Convert to dict and format nicely
    if hasattr(obj, "__dict__"):
        # Handle Enum values
        if isinstance(obj, FinishReason):
            return f"{Colors.CYAN}{obj.name}{Colors.ENDC}"
        
        # For regular dataclasses
        result = {}
        for key, value in obj.__dict__.items():
            if isinstance(value, FinishReason):
                result[key] = f"{Colors.CYAN}{value.name}{Colors.ENDC}"
            elif value is None:
                result[key] = f"{Colors.YELLOW}None{Colors.ENDC}"
            elif isinstance(value, (dict, list)) and not value:
                result[key] = f"{Colors.YELLOW}empty {type(value).__name__}{Colors.ENDC}"
            else:
                result[key] = value
        
        # Format as JSON-like string with indentation
        formatted = json.dumps(result, indent=2, default=str)
        # Add colors
        formatted = formatted.replace('"', '')
        formatted = formatted.replace('{', f'{Colors.BOLD}{{')
        formatted = formatted.replace('}', f'}}{Colors.ENDC}')
        formatted = formatted.replace(':', f':{Colors.ENDC}')
        
        # Highlight field names
        for key in result.keys():
            formatted = formatted.replace(f"{key}:", f"{Colors.GREEN}{key}{Colors.ENDC}:")
        
        return formatted
    return str(obj)


def print_header(text: str) -> None:
    """Print a section header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 50}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD} {text} {Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 50}{Colors.ENDC}\n")


def main():
    """Test the generated models with nice output formatting."""
    print_header("Agent Protocol Models Demo")
    
    # Create a timestamp for events
    now = datetime.now().isoformat()
    
    # 1. Agent Description
    print_header("Agent Description")
    operations = [
        AgentOperation(
            name="chat",
            description="Send a chat message to the agent",
        ),
        AgentOperation(
            name="search",
            description="Search for information",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        ),
    ]
    
    agent = AgentDescriptor(
        name="DemoAgent",
        purpose="Demonstrate the Agent Protocol models",
        endpoints=["/chat", "/search", "/cancel"],
        operations=operations,
        tools=["web_search", "calculator"],
    )
    
    print(f"{Colors.BOLD}Agent Descriptor:{Colors.ENDC}")
    print(format_model(agent))
    
    # 2. Requests
    print_header("Request Types")
    
    chat_request = ChatRequest(
        request_id="req-123",
        input="Hello, agent! Can you help me with a task?",
    )
    
    configure_request = ConfigureRequest(
        request_id="req-124",
        args={"temperature": 0.7, "max_tokens": 1000},
    )
    
    cancel_request = CancelRequest(
        request_id="req-125",
    )
    
    resume_request = ResumeWithInput(
        request_id="req-126",
        request_keys={"user_input": "Yes, please continue"},
    )
    
    print(f"{Colors.BOLD}Chat Request:{Colors.ENDC}")
    print(format_model(chat_request))
    
    print(f"\n{Colors.BOLD}Configure Request:{Colors.ENDC}")
    print(format_model(configure_request))
    
    print(f"\n{Colors.BOLD}Cancel Request:{Colors.ENDC}")
    print(format_model(cancel_request))
    
    print(f"\n{Colors.BOLD}Resume With Input Request:{Colors.ENDC}")
    print(format_model(resume_request))
    
    # 3. Events
    print_header("Event Types")
    
    request_started = RequestStarted(
        id=1,
        run_id="run-789",
        agent="DemoAgent",
        type="request_started",
        request_id="req-123",
        timestamp=now,
    )
    
    text_output = TextOutput(
        id=2,
        run_id="run-789",
        agent="DemoAgent",
        type="text_output",
        content="I'm here to help! What would you like to know?",
        timestamp=now,
    )
    
    wait_for_input = WaitForInput(
        id=3,
        run_id="run-789",
        agent="DemoAgent",
        type="wait_for_input",
        request_keys={"confirmation": "Do you want to proceed?"},
        timestamp=now,
    )
    
    tool_call = ToolCall(
        id=4,
        run_id="run-789",
        agent="DemoAgent",
        type="tool_call",
        function_name="web_search",
        args={"query": "latest AI developments"},
        timestamp=now,
    )
    
    tool_result = ToolResult(
        id=5,
        run_id="run-789",
        agent="DemoAgent",
        type="tool_result",
        function_name="web_search",
        text_result="Found several articles about recent AI advancements...",
        timestamp=now,
    )
    
    artifact = ArtifactGenerated(
        id=6,
        run_id="run-789",
        agent="DemoAgent",
        type="artifact_generated",
        name="search_results.pdf",
        artifact_id="art-456",
        url="https://example.com/artifacts/art-456",
        mime_type="application/pdf",
        timestamp=now,
    )
    
    operation_complete = OperationComplete(
        id=7,
        run_id="run-789",
        agent="DemoAgent",
        type="operation_complete",
        finish_reason=FinishReason.success,
        timestamp=now,
    )
    
    print(f"{Colors.BOLD}Request Started Event:{Colors.ENDC}")
    print(format_model(request_started))
    
    print(f"\n{Colors.BOLD}Text Output Event:{Colors.ENDC}")
    print(format_model(text_output))
    
    print(f"\n{Colors.BOLD}Wait For Input Event:{Colors.ENDC}")
    print(format_model(wait_for_input))
    
    print(f"\n{Colors.BOLD}Tool Call Event:{Colors.ENDC}")
    print(format_model(tool_call))
    
    print(f"\n{Colors.BOLD}Tool Result Event:{Colors.ENDC}")
    print(format_model(tool_result))
    
    print(f"\n{Colors.BOLD}Artifact Generated Event:{Colors.ENDC}")
    print(format_model(artifact))
    
    print(f"\n{Colors.BOLD}Operation Complete Event:{Colors.ENDC}")
    print(format_model(operation_complete))
    
    # Summary
    print_header("Summary")
    print(f"{Colors.GREEN}{Colors.BOLD}✓ Successfully imported and demonstrated all Agent Protocol models!{Colors.ENDC}")
    print(f"\n{Colors.CYAN}These models were auto-generated from the OpenAPI specification.{Colors.ENDC}")
    print(f"{Colors.CYAN}To update the models, modify specs/openapi.yaml and run scripts/generate_models.py{Colors.ENDC}")


if __name__ == "__main__":
    main() 