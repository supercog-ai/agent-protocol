# Agent Protocol (draft - 2025 edition)

We are rapidly entering a world with lots and lots of AI agents, built on lots and lots of different frameworks.
There have been [previous efforts](https://agentprotocol.ai/) at defining a common protocol for interacting
with agents, but now that we HAVE lots of good agents, the need is more urgent.

The goals of this proposal are to enable interoperability between _agents_ built using different
frameworks like LangGraph, Smol Agents, Atomic Agents, etc... Notably, our emphasis is on allowing
two (or more) agents to collaborate together, rather than providing a common User->Agent interface
(although that is a partial side-effect of this proposal).

You can read some background on our [motivations](./MOTIVATION.md) for this project.

## Goal by example

Our goal is to let multiple AI agents, built on different software stacks, to collaborate on a task. To make
a concrete example,  assume I have built my "Personal Assistant" agent which helps me in my daily tasks (it
has access to my email, calendar, etc...). I want my agent to be able to use the 
[Browser Use](https://github.com/browser-use/browser-use) agent for browser automation tasks, AND
the [GPT Researcher](https://github.com/assafelovic/gpt-researcher) agent to perfom long research tasks.
I can code my Personal Agent by hand to accomplish this. The intention of this proposal is to define
a protocol where such integration would be easy and extensible to other agents.

## Why tool calling is the wrong paradigm

The current standard for "teams of agents" is to support _agents as tools_ - re-using the function calling
protocol to allow Agent A to invoke Agent B. This approach assumes that agents look like _synchronous
functions_. You invoke the agent with a set of parameters, and then wait for it to return a unitary
result.

This is the wrong model for agents. Agent operations may run for a long time, take different paths, and
generate lots of intermediate results while they run. They may need to stop and ask a human for input.
None of these characteristics fit well into a synchronous function call model (this is the same reason
we build large concurrent systems using event driven architectures rather than RPC).

The correct model for AI Agents is actually the [actor model](https://en.wikipedia.org/wiki/Actor_model),
created back in 1973! Actors are independently operating entities, which only access their own private
state, and communicate asynchronously by passing messages between them. This model naturally allows
us to fit our long running, asynchronous, interupttable agents into a unified framework.

## Tools as Agents

We propose that the correct model is not to "define down" agents as tools, but rather to generalize "everything
is an agent", including tools. All coordination happens via asynchronous message passing. If we adopt this
model then agent cooperation is very natural, and tools and agents are interchangable. Today I can use the
hand-coded "web browser tool", but tomorrow I can swap it out for a true agent (like BrowserUse) which performs
the job better.

(One caveat is that the LLM tool calling protocol only has a single LLM completion pass to 'observe' the
results of a tool call. So if our 'tool' is an agent generating an output stream, what is the input to
the 'observe' phase? This is still an open design question. 'Cache the events' and provide them all as the
result is the easiest model. One could imagine progessively feeding the sub-agent results to the caller, like
"Here are prelim results from that tool call:... Keep waiting for more output.")

## Agent definition

An _agent_ is defined as a named software entity which advertises a set of supported _operations_. A client
can _request_ the agent to perform an _operation_ by sending it an operation request message. Subsequently
the agent will publish a stream of events relevant to the operation until eventually it publishes
an _request completed_ event. 

All events between _request started_ and _requsted completed_ are considered a single _turn_. The
client can send another request to the same agent, and this is considered the _next turn_. Clients
can assume that agents have memory and so a set of turns will consistute a _run_ (analogous to a 
web _session_) where memory was preserved during the session. Clients can elect to start a new 
run with any operation request.

## Exclusions

Note that this spec is aimed at interoperability amongst agents in a _trusted_ environment. We do
specify any user authentication nor specify any authz/authn between agents.

## Base elements of the protocol

Agents must implement the following logical operations:

_describe_ Requests the agent to return its description (name and operations)

_process_ - Send the agent a request to process. A request could start a new _Run_ or
continue one already in progress. Callers can send a special `ConfigureRequest` to configure
agent.

_get events_ - returns available events, or subscribes to the stream of events from the agent

### Agent operations

Agent can advertise one or more supported operations via the _describe_ protocol. For
convenience our protocol assumes that every agent supports a generic "ChatRequest" request type
which contains a single text request (like a ChatGPT user prompt). Agents should implement this 
request by publishing intermediate _TextOutput_ events (string messages) and publishing a final
_RequestCompleted_ event which contains a single string result. This "lowest-common denominator"
operation allows us to integrate almost any agent that supports a basic conversational interface.

### Pseudo-code example

```
process(requestObject, run_id, run_context)
    Requests an agent to start an operation. 
    The requestObject specifies the details of the request and references an _operation_ defined by the agent.
    If 'run_id' is null, then a new Run is started (agent short-term memory is initialized).
    "run_context" can pass additional metadata into the operation. A notable example is the "user_context".
    which could identify the requesting user.
    If run_id is not null, then this operation continues a prior Run.

  <-- returns a RequestStarted object

get_events(request_id, stream=True)
    Streams output events from the agent until _RequestCompleted_ which should be the final event.
```

as you can see from this pseudo-code, much of our protocol lies in the definitions of the input and
output events to the agent.

## Schema definitions

Below are casual descriptions of the main types/events in the system. These will be formalized via JSON Schemas.

```
# == result of the "describe" API

type AgentDescriptor:
    name: string
    purpose: string
    endpoints: list[string] - list of supported API endpoints
    operations: list[AgentOperation]
    tools: list[string] - for information purposes

# agent operations 

type AgentOperation:
    name: string
    description: string
    input_schema: Optional formal schema
    output_schema: Optional formal schema

type DefaultChatOperation(AgentOperation):
    name: chat
    description: send a chat request
    input_schema: [input: string]
    output_schema: [output: string]

# == Event base type

type Event:
    id: int             # incrementing event index, only unique within a Run
    run_id: int         # the Run that this event is part of
    agent: string       # Identifier for the agent, defaults to the name
    type: string        # event type identifier
    role: string        # generally one of: system, assistant, user, tool
    depth: int          # indicates the caller-chain depth where this event originated

# == Request types

type ConfigureRequest:         # pass configuration to the agent
    args: dict

type Request:
    request_id: string
    logging_level:  string # request additional logging detail from the agent
    request_metadata: dict   # opaque additional data to the request. Useful for things like:
                             # user_id, current_time, ...

type ChatRequest(Request):
    input: string

type CancelRequest(Request): # cancel a request in progress

type ResumeWithInput(Request): # tell an agent to resume from WaitForInput
    request_keys: dict  # key, value pairs

# Implementations can implement new Request types. An example might be 'ChatWithFileUpload' which
# would include a file attachment with the user input. 

# == Response events

type RequestStarted: # the agent has started processing a request
    request_id: string

type WaitForInput:   # the agent is waiting on caller input
    request_keys: dict      # Requested key value, description pairs

type TextOutput(Event): # the agent generated some text output
    content: string 

type ToolCall(Event):   # agent is calling a tool
    function_name: string
    args: dict

type ToolResult(Event): # a tool call returned a result
    function_name: string
    text_result: string     # text representation of the tool result

type ArtifactGenerated(Event): # the agent generated some artifact
    name: string
    id: string
    url: string
    mime_type: string

type ToolTextOutput(Event): # tool call generated some text output
    content: string

type ToolError(Event):
    content: string         # a tool encountered an error

type CompletionCall(Event): # agent is requesting a completion from the LLM

type CompletionResult(Event): # the result of an LLM completion call

type RequestCompleted(Event): # the agent turn is completed
    finish_reason: string   [success, error, canceled]
    
```

### The minimum Event set

An agent **must** support these events at minimum:

> ChatRequest, RequestStarted, RequestCompleted

To make the operation of an agent visible, it **should** support these events:

> TextOutput, ToolCall, ToolResult, ToolError, CompletionCall, CompletionResult

All other events are optional.

## Relation to OpenAI APIs

The most analagous API is the OpenAI [Assistants API](https://platform.openai.com/docs/api-reference/assistants).
The Agent Protocol is similar, some terminology is different:

- OpenAI uses `Thread` where we use `Run`. Both represent a "chat session", with "conversation thread" being
the inspiration for the OpenAI terminology. Because Agents are meant to generalize beyond just chat, we 
think of "running" an agent in a session.

- OpenAI uses `run` to refer to what we term a `turn` - the single turn execution of their Assistant.
We find that 'run' and 'run step' are too low level to be useful other than logging. The same concept
is represented in agent protocol by the `RequestStarted` and `RequestCompleted` events.

Many apps and libraries have been built around the streaming `completion` API defined by OpenAI. To
suppor broader compatibility, we provide a `stream_request` endpoint which takes a Request input
object and streams result events via SSE immediately back to the client. This endpoint operates conceptually
in a similar manner as the standard `completion` endpoint.

## Protocol as REST Endpoints

The protocol can be implemented on multiple transport types. For reference purposes we define a
REST API that all agents should support. Other transports are optional (websocket, etc...).

```
Basic discovery endpoint

    # List agents available at this endpoint
    /   -> list[name, path] pairs


All other endpoints are relative to the agent's path:

    # Get the agent's descriptor
    /describe -> AgentDescriptor

    # Send the agent a request to process
    /process (Request) -> Event|None
        params: 
            wait: bool  # wait for the agent response. Agent will return an Event response, otherwise
                        # the agent returns only the HTTP status code.

    # Get events from a request. If stream=False then the agent will return any events queued since
    # the last `getevents` call (basic polling mechanism). If stream=True then the endpoint will
    # publish events via SSE
    /getevents (request_id)
        params:
            stream: bool
            since: event_id     # pass the last event_id and any later events will be returned

    # Convenience route that starts a new Request and streams back the results in one call
    /stream_request (Request)
        <-- events via SSE

**Optional endpoints**

    GET /request/{request_id}    -> Returns the status of a request
    GET /runs                    -> Returns a list of persisted Runs
    GET /getevents/{run_id}      -> Returns all events for a Run in time sequence
```

Example event flows:

```
# retrieve agent operations
GET /describe

# configure an agent
POST /process (ConfigureRequest(args), wait=True)
    -> RequestCompleted

# Start a run, passing a chat prompt to the agent
POST /process (ChatRequest(input), wait=True)
    -> RequestStarted (contains 'request_id' and 'run_id')

# Stream output events from the agent
GET /getevents/{request_id}?stream=True

# Continue a Run
POST /process (ChatRequest(run_id=?))

```

**Human in the Loop**

```
POST /process (ChatRequest(input), wait=True)
    -> RequestStarted (contains 'request_id' and 'run_id')

# Stream output events from the agent
GET /getevents/{request_id}?stream=True

<- WaitForInput event received
..caller prompts for input...

POST /process (ResumeWithInput(...))
GET /getevents/{request_id}?stream=True
```

**Canceling a Request**

You can interrupt an agent turn:

```
POST /process (ChatRequest(input), wait=True)

GET /getevents/{request_id}?stream=True

POST /process (CancelRequest(request_id=?))

GET /getevents/{request_id}?stream=True
<-- RequestCompleted (finish_reason=canceled)
```

**Artifact example**

An agent uses a _PDFWriter_ tool to create a PDF file that the caller
can download:

```
POST /process (ChatRequest(input), wait=True)

GET /getevents/{request_id}?stream=True
<-- ArtifactGenerated
(caller displays the artifact to the user)
```

**Persisted Runs**

Caller lists available Runs, then requests the event history from a Run:

```
GET /runs
GET /events/{run_id=?}
```

## Development

### OpenAPI Specification

The Agent Protocol is defined using OpenAPI 3.1.0 specification in the `specs/openapi.yaml` file. This specification includes JSON Schema definitions for all protocol types, events, and API endpoints.

Python data models are automatically generated from this specification using the `datamodel-code-generator` tool:

```bash
python scripts/generate_models.py
```

This will update the models in `src/agent_protocol/models/`.

This approach ensures that:
1. The specification serves as the single source of truth
2. All models are consistent with the specification
3. Documentation and code are always in sync
4. Models can be regenerated for different programming languages

### Python Models

The `src/agent_protocol/models/` directory contains auto-generated Python data models for the Agent Protocol. These models are automatically generated from the OpenAPI specification.

#### Usage

You can import and use the models directly:

```python
from agent_protocol.models import (
    ChatRequest,
    TextOutput,
    FinishReason,
    # etc.
)

# Create a chat request
request = ChatRequest(
    request_id="req-123",
    input="Hello, agent!",
)

# Create a text output event
output = TextOutput(
    id=1,
    run_id="run-789",
    agent="MyAgent",
    type="text_output",
    content="Hello, human!",
)
```

#### Manual Adjustments

The auto-generated models may sometimes require manual adjustments for:

1. **Mutable default values**: Python dataclasses don't allow mutable defaults like empty lists or dictionaries. Use `field(default_factory=list)` instead.

2. **Inheritance issues**: When a class inherits from another class, all required fields must come before optional fields.

3. **Field name conflicts**: If a field name conflicts with a Python keyword or another field, it needs to be renamed.

These adjustments are typically handled automatically by the generation script, but you may need to make additional changes for complex cases.

#### Testing Models

You can test the models using the provided test script:

```bash
poetry run python scripts/test_models.py
```

### Development Setup

// ... existing code ...


