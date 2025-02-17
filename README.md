# Agent Protocol (2025 edition)

We are rapidly entering a world with lots and lots of AI agents, built on lots and lots of different frameworks.
There have been [previous efforts](https://agentprotocol.ai/) at defining a common protocol for interacting
with agents, but now that we HAVE lots of good agents, the need is more urgent.

The goals of this proposal are to enable interoperability between _agents_ built using different
frameworks like LangGraph, Smol Agents, Atomic Agents, etc... Notably, our emphasis is on allowing
two (or more) agents to collaborate together, rather than providing a common User->Agent interface
(although that is a partial side-effect of this proposal).

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

## Agent definition

An _agent_ is defined as a named software entity which advertises a set of supported _operations_. A client
can request the agent to perform an operation by sending it an operation request message. Subsequently
the agent will publish a stream of events relevant to the operation until eventually it publishes
an _operation complete_ event. 

All events between _operation request_ and _operation complete_ are considered a single _turn_. The
client can send another request to the same agent, and this is considered the _next turn_. Clients
can assume that agents have memory and so a set of turns will consistute a _run_ (analogous to a 
web _session_) where memory was preserved during the session. Clients can elect to start a new 
run with any operation request.

## Base elements of the protocol

Agents must implement the following logical operations:

_self-description_ Requests the agent to return its description (name and operations)

_process request_ - Send the agent a request to process. A request could start a n

_get events_ - returns available events, or subscribes to the stream of events from the agent