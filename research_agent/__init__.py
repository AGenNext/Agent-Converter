"""Research deep agent.

A LangChain `deepagents` implementation of the Research Agent build
specification (v1.0): an orchestrator that plans research, delegates to
source-pack sub-agents, and synthesises honest, well-sourced, confidence-
tagged answers.
"""

from research_agent.agent import build_agent

__all__ = ["build_agent"]
