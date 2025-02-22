# Motivation

It's always a good idea to understand "Why does this exist? What problems are we trying to solve?" when you are looking at a new project.

This project came out of these experiences:

- Lots of people are building cool agents now, like GPT Researcher and others. But the state of the art is to build your agent and then expose some custom interface to it. In the case of GPT Researcher it has its own UI. Other agents expose some arbitrary command line or internal API.

- There isn't an easy way for agents to cooperate as _teams_. I have to write custom code to integrate one agent with another.

But imagine if we have a standard "agent protocol" for interacting with agents? Then we could solve both of these problems. People could build re-usable UI interfaces that could "operate" multiple agents, and we could build "agent teams" out of cooperating agents that were built with different tech stacks (even different languages).

Anthropic introduced [Model Context Protocol](https://github.com/modelcontextprotocol) a while back, but it is targeted at integrating LLM apps with external data sources:

> The Model Context Protocol (MCP) is an open protocol that enables seamless integration between LLM applications and external data sources and tools. 

Now we could try to "squeeze" agents into that protocol, and treat them as "tools" which some "LLM app" is going to call. But that isn't really "fit for purpose". If we take seriously the idea of agents, and teams of agents, then we believe you want a different, high level protocol:

> An agent is a "automonous LLM powered software app" which advertises a set of capabilities. When it runs it maintains its own thread of control and internal state.

Today, the most "standard" protocol is the original OpenAI `completions` API, for basic chat. Lots of people support that API, which is basically: "given this list of 'role' messages, please generate the next messsage". It is very low level, stateless, and synchronous.

The Open AI [Assistants API](https://platform.openai.com/docs/api-reference/assistants) gets a lot closer. It defines a callable, stateful object (the 'assistant') and a protocol of API endpoints and return messages from using the assistant. That API is good prior art, but it also proprietary to OpenAI, and fitted around their specific "agent" implementation.

Achieving the goals of this proposal would mean:

- You could take the same UI application and from it access agents built in LangGraph, Pydantic AI, SmolAgents, or any other framework.
- Agents from different frameworks could be drafted together into collaborting "teams".

We think the starting point to achieve this is:

A good set of **nouns and verbs**. What are the standard pieces of the "agent model" (in physics terms) and how we talk about them? 

Pydantic AI uses these nouns:
- conversation (a multi-turn chat session)
  - run (a single turn)
    - messages (messages exchanged during the run or conversation)

whereas OpenAI Assistants uses these:
- thread (the multi-turn conversation)
  - run (a single turn)
     - steps (the steps taken by the agent during a turn)

and we have proposed this structure:
- run (the multi-turn chat session)
   - turn (a single request to agent, plus its response events)
      - request (the request to the agent)
      - events (events sent by the agent when operating)
      - result (the 'final result' from the turn)

Agreeing on the right nouns and verbs will be key to interoperability.

What is the **agent definition**? There is some consensus on:

- `name` the name of the agent
- `system_prompt` or `instructions` - the LLM system prompt that defines the agent's behavior
- `tools` the set of "tools" the agent is configured to use

Beyond that there isn't much agreement. Most people assume a "process chat" default operation
which looks like the original LLM completion call:

    user prompt -> agent operation -> result

And people have various techniques for describing what is happening inside "agent operation".

We have proposed the following:

Agents offer `operations` which can be named and can define their inputs and outputs. We assume
that every agent supports the fallback "chat operation" by default. For using _agents as tools_ we are
gonna want more strictly defined operations (but maybe not TOO strictly defined).

Operations run asynchronously (it is up to the caller if they want to wait for the 'end event' or not). 
When running an operation, the agent generates an `event stream` of typed events. So rather than
assuming a single "result value" like a function call, the agent can emit lots of events describing
what it is doing. The purpose and "depth of detail" of each event is described so that the 
caller can make a choice about what it uses or reflects back to its user/caller.

A big part of this spec is the definition of the **Events** that an agent can emit. We expect that
lots of folks may create and use custom events, but we think having the "_standard library_" of Event defintions
is key to actually re-using agents. Otherwise you are stuck with function calling, `f(x) -> y`, and
text input/output, which is very limiting.

Agents are **asynchronous**

We assume, **in the protocol**, that agents run asynchronously to their caller and any other agents. This makes it much easier
to support long-running agents, or agents doing things in the background, or agents stopping to wait for human input. If you don't build around asynchronous operation all the way down, then eventually something will want to block and that causes a lot of problems.

What about **agent memory**?

Different frameworks make different assumptions about how much memory your agent will have. But by default most
people assume your agent will remember a "chat conversation" - the history of messages and actions taking across
multiple turns in a single "session". Some folks define their protocol as stateless (like the underlying LLM
protocol), and leave it to the caller to remember the message history on every turn. We think that makes it 
much harder to build clients, so we have assumed that agents are **stateful** and remember what happens within
a session. 

