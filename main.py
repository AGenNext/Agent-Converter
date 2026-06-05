"""CLI entrypoint for the Research deep agent.

Run a one-off research question:
    python main.py "Research Parkwalk Advisors for Sumandra's GBP 3.2M seed"

Or start an interactive session:
    python main.py

For a one-shot run (e.g. a Kubernetes Job), set the QUESTION env var:
    QUESTION="Research ..." python main.py
"""

from __future__ import annotations

import os
import sys

from research_agent import build_agent


def _run(agent, question: str) -> None:
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    content = result["messages"][-1].content
    # Content may be a string or a list of content blocks (e.g. Anthropic).
    if isinstance(content, list):
        content = "".join(
            b if isinstance(b, str) else b.get("text", "")
            for b in content
            if isinstance(b, str) or isinstance(b, dict)
        )
    print(content)


def main() -> None:
    agent = build_agent()

    if len(sys.argv) > 1:
        _run(agent, " ".join(sys.argv[1:]))
        return

    question_env = os.environ.get("QUESTION")
    if question_env:
        _run(agent, question_env)
        return

    print("Research deep agent. Type a question, or 'exit' to quit.\n")
    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"exit", "quit"}:
            break
        if question:
            _run(agent, question)
            print()


if __name__ == "__main__":
    main()
