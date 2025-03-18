# Agent Design Principles

## 1. An agent has no value if its trusted by humans, or it will have no value

AI agents will not, and should not, be trusted by default. They have to earn trust.
These guidelines are a starting point for building trustworthy agents. The
key elements of trust include:
    - the agent will only perform expected operations
    - the behavior of the agent is explainable
    - the agent will rely only on knowledge we expect it to use, and it will
        explain its knowledge sources when it makes a decision
    - the agent stays aligned with its operator's values, and the values of
        human safety

## 2. Agents must only run under the authority of a named human user

Agents always inherit their authority to access information or resources
from their human creators and operators.  Agents must never run _autonomously_ 
without any human being named as responsible for their operation. 
Allowing anonymous (or "AI identity") operation is a dangerous anti-pattern. 

*Human in the loop* is a key feature that agents should rely on until they can
prove that they can operate autonomously.

## 3. Agent generated content should identify as machine produced

The initial human consumer of any Agent generated content should know that the content
was machine generated. A human may "process" such content and re-publish it without
the disclosure. For example, an agent must NOT post "pretend human" messages to a
social network.

This rule is already violated by, for example, various AI SDR systems. But the alternative
is a world with no rules to distinguish human generated vs machine generated content.

## 4. Agent behavior must be _explainable_

We cannot necessarily predict agent behavior, but agentic systems must explain
what they are doing and why as much as possible. Unexplainable behavior is
a system bug to be fixed, and should not be tolerated. Part of explainability is
transparency about the operations executed and resources used by the agent.

Agent User Interface should always promote and provide explainability - they
should never hide the actions of the agent.

## 5. Agents should publish their test suites

Like the reproducibility of scientific experiments, even closed-source agents
should publish their test suites, so that users can evaluate how throughly
the agent has been tested.