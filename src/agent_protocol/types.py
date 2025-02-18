from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, UTC

class FinishReason(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    CANCELED = "canceled"

@dataclass
class AgentOperation:
    """Defines an operation that an agent can perform."""
    name: str
    description: str
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None

@dataclass
class AgentDescriptor:
    """Describes an agent's capabilities."""
    name: str
    purpose: str
    endpoints: List[str]
    operations: List[AgentOperation]
    tools: List[str] = field(default_factory=list)

@dataclass
class Event:
    """Base event type for all agent events."""
    id: int
    run_id: str
    agent: str
    type: str
    depth: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

@dataclass
class Request:
    """Base request type for all agent requests."""
    request_id: str
    logging_level: Optional[str] = None
    request_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ChatRequest(Request):
    """Simple chat request with text input."""
    input: str

@dataclass
class ConfigureRequest(Request):
    """Request to configure an agent."""
    args: Dict[str, Any]

@dataclass
class CancelRequest(Request):
    """Request to cancel an operation in progress."""
    pass

@dataclass
class ResumeWithInput(Request):
    """Request to resume an operation with user input."""
    request_keys: Dict[str, Any]

# Response Events
@dataclass
class RequestStarted(Event):
    """Event indicating a request has started processing."""
    request_id: str

@dataclass
class WaitForInput(Event):
    """Event indicating the agent is waiting for user input."""
    request_keys: Dict[str, str]

@dataclass
class TextOutput(Event):
    """Event containing text output from the agent."""
    content: str

@dataclass
class ToolCall(Event):
    """Event indicating a tool is being called."""
    function_name: str
    args: Dict[str, Any]

@dataclass
class ToolResult(Event):
    """Event containing the result of a tool call."""
    function_name: str
    text_result: str

@dataclass
class ArtifactGenerated(Event):
    """Event indicating an artifact was generated."""
    name: str
    id: str
    url: str
    mime_type: str

@dataclass
class OperationComplete(Event):
    """Event indicating an operation has completed."""
    finish_reason: FinishReason 