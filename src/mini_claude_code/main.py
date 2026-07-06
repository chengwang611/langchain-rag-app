"""CLI entrypoint for mini-claude-code.

Usage:
    python -m mini_claude_code.main "Read the file src/mini_claude_code/__init__.py"
    python -m mini_claude_code.main "Run git status"
    python -m mini_claude_code.main "Create a new Python file hello.py"
    python -m mini_claude_code.main --interactive
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

from .graph import run_workflow
from .memory import ConversationMemory, RAGMemory
from .tools import ALL_TOOLS


def print_banner():
    """Print a welcome banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║              mini-claude-code v1.0.0                        ║
║  A minimal Claude Code-like agent with 10 capabilities      ║
║                                                             ║
║  Planner  │  Tool Calling  │  File Reader  │  File Editor   ║
║  Bash     │  Git           │  Multi-Agent  │  Memory        ║
║  RAG      │  MCP           │                               ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_tools():
    """Print available tools."""
    print("\nAvailable tools:")
    for tool in ALL_TOOLS:
        print(f"  • {tool.name}: {tool.description.split(chr(10))[0]}")
    print()


def interactive_mode():
    """Run in interactive REPL mode."""
    session_id = f"session-{uuid.uuid4().hex[:8]}"
    memory = ConversationMemory()
    rag = RAGMemory()

    print_banner()
    print_tools()
    print("Type 'exit' to quit, 'tools' to list tools, 'clear' to clear history.\n")

    while True:
        try:
            user_input = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break
        if user_input.lower() == "tools":
            print_tools()
            continue
        if user_input.lower() == "clear":
            memory.clear_session(session_id)
            print("Session history cleared.")
            continue
        if user_input.lower() == "help":
            print("Commands: exit, tools, clear, help")
            print("Or ask me to do anything — read files, run bash, git operations, etc.")
            continue

        # Add to RAG for future context
        rag.add_document(user_input, {"source": "user_query", "session": session_id})

        # Run the workflow
        print()
        response = run_workflow(session_id, user_input)
        print(f"\n{response}\n")


def single_mode(request: str):
    """Run a single request and print the response."""
    session_id = f"session-{uuid.uuid4().hex[:8]}"
    response = run_workflow(session_id, request)
    print(response)


def main():
    parser = argparse.ArgumentParser(
        description="mini-claude-code — A minimal Claude Code-like agent"
    )
    parser.add_argument(
        "request",
        nargs="?",
        help="Single request to process. Omit for interactive mode.",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Force interactive mode",
    )
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version",
    )

    args = parser.parse_args()

    if args.version:
        print("mini-claude-code v1.0.0")
        return

    if args.interactive or not args.request:
        interactive_mode()
    else:
        single_mode(args.request)


if __name__ == "__main__":
    main()
