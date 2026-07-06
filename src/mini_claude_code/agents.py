"""Agent definitions — specialized agents and the orchestrator.

Architecture:
                    ┌──────────────────┐
                    │   Orchestrator    │  (Planner + Router)
                    └───────┬──────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  File Agent  │ │  Bash Agent  │ │   Git Agent  │
    │  (read/edit) │ │  (execute)   │ │  (status/    │
    │              │ │              │ │   commit)    │
    └──────────────┘ └──────────────┘ └──────────────┘
            │               │               │
            └───────────────┼───────────────┘
                            ▼
                    ┌──────────────────┐
                    │   MCP Agent      │  (dynamic tools)
                    └──────────────────┘
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from .tools import ALL_TOOLS, FILE_TOOLS, BASH_TOOLS, GIT_TOOLS, MCP_TOOLS
from .memory import ConversationMemory, RAGMemory


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Planner
# ═══════════════════════════════════════════════════════════════════════════════

PLANNER_PROMPT = """You are a Planner. Given a user request, break it down into
a sequence of steps. Each step should be one of:
- read_file(path)
- write_file(path, content)
- edit_file(path, old_string, new_string)
- run_bash(command)
- git_status / git_diff / git_commit
- mcp_register_tool / mcp_call_tool
- rag_search(query)
- ask_user(question)

Output a JSON array of steps:
[
  {{"step": 1, "action": "read_file", "params": {{"path": "..."}}}},
  {{"step": 2, "action": "run_bash", "params": {{"command": "..."}}}}
]"""


def plan_task(llm: ChatOpenAI, user_request: str) -> List[dict]:
    """Decompose a user request into a step-by-step plan."""
    response = llm.invoke([
        SystemMessage(content=PLANNER_PROMPT),
        HumanMessage(content=f"Plan this request:\n{user_request}"),
    ])
    content = response.content.strip()
    # Extract JSON array from the response
    if "[" in content:
        json_str = content[content.index("["):content.rindex("]") + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    return [{"step": 1, "action": "ask_user", "params": {"question": "Could you clarify your request?"}}]


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Multi-Agent — Specialized Agent Definitions
# ═══════════════════════════════════════════════════════════════════════════════

def _build_agent(llm: ChatOpenAI, tools: List[BaseTool], system_prompt: str):
    """Create a bound LLM with tools and system prompt."""
    llm_with_tools = llm.bind_tools(tools)
    return {"llm": llm_with_tools, "tools": {t.name: t for t in tools}, "prompt": system_prompt}


def create_file_agent(llm: ChatOpenAI) -> dict:
    """Agent specialized in file operations."""
    return _build_agent(
        llm, FILE_TOOLS,
        "You are a File Agent. Read, write, and edit files. "
        "Use read_file to inspect, write_file to create, edit_file to modify."
    )


def create_bash_agent(llm: ChatOpenAI) -> dict:
    """Agent specialized in bash execution."""
    return _build_agent(
        llm, BASH_TOOLS,
        "You are a Bash Agent. Execute shell commands to accomplish tasks. "
        "Be careful with destructive commands."
    )


def create_git_agent(llm: ChatOpenAI) -> dict:
    """Agent specialized in git operations."""
    return _build_agent(
        llm, GIT_TOOLS,
        "You are a Git Agent. Check status, show diffs, and commit changes."
    )


def create_mcp_agent(llm: ChatOpenAI) -> dict:
    """Agent specialized in MCP tool management."""
    return _build_agent(
        llm, MCP_TOOLS,
        "You are an MCP Agent. Register, list, and call MCP tools dynamically."
    )


def create_orchestrator_agent(llm: ChatOpenAI) -> dict:
    """Orchestrator agent that routes tasks to specialized agents."""
    return _build_agent(
        llm, ALL_TOOLS,
        "You are the Orchestrator. Analyze the user's request and decide which "
        "specialized agent should handle it, or handle it yourself using available tools. "
        "For file tasks → use file tools. For bash → use bash tools. "
        "For git → use git tools. For MCP → use MCP tools."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Execution
# ═══════════════════════════════════════════════════════════════════════════════

def run_agent(agent: dict, user_input: str, context: str = "") -> str:
    """Run an agent with tools, returning the final response."""
    llm = agent["llm"]
    tools = agent["tools"]
    system_prompt = agent["prompt"]

    messages = [SystemMessage(content=system_prompt)]
    if context:
        messages.append(SystemMessage(content=f"Context:\n{context}"))
    messages.append(HumanMessage(content=user_input))

    response = llm.invoke(messages)
    messages.append(response)

    # Tool calling loop (max 10 iterations)
    for _ in range(10):
        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc.get("args", {})
            if tool_name in tools:
                try:
                    result = tools[tool_name].invoke(tool_args)
                except Exception as e:
                    result = f"Error calling {tool_name}: {e}"
            else:
                result = f"Unknown tool: {tool_name}"

            messages.append(AIMessage(content=str(result)[:2000]))

        response = llm.invoke(messages)
        messages.append(response)

    return response.content if hasattr(response, "content") else str(response)


# ═══════════════════════════════════════════════════════════════════════════════
# Orchestrator — Routes to specialized agents
# ═══════════════════════════════════════════════════════════════════════════════

def route_to_agent(user_input: str) -> str:
    """Determine which agent should handle the request based on keywords."""
    lower = user_input.lower()
    if any(w in lower for w in ["git ", "commit", "push", "branch", "status"]):
        return "git"
    if any(w in lower for w in ["bash", "shell", "run ", "execute", "command", "terminal"]):
        return "bash"
    if any(w in lower for w in ["mcp", "register", "tool"]):
        return "mcp"
    if any(w in lower for w in ["read ", "write ", "edit ", "file ", "create "]):
        return "file"
    return "orchestrator"
