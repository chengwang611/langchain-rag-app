"""LangGraph workflow — the core execution graph.

Graph structure:
    START → plan → route → execute → reflect → END
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         file_agent   bash_agent   git_agent
              │            │            │
              └────────────┼────────────┘
                           ▼
                      mcp_agent
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from .agents import (
    create_bash_agent,
    create_file_agent,
    create_git_agent,
    create_mcp_agent,
    create_orchestrator_agent,
    plan_task,
    run_agent,
)
from .memory import ConversationMemory, RAGMemory
from .tools import ALL_TOOLS


# ═══════════════════════════════════════════════════════════════════════════════
# State Definition
# ═══════════════════════════════════════════════════════════════════════════════

class AgentState(TypedDict):
    """Shared state for the mini-claude-code workflow."""
    session_id: str
    user_request: str
    plan: List[dict]
    current_step: int
    step_results: List[str]
    final_response: str
    messages: List
    agent_type: str  # which agent to route to


# ═══════════════════════════════════════════════════════════════════════════════
# Node Functions
# ═══════════════════════════════════════════════════════════════════════════════

def _get_llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


def plan_node(state: AgentState) -> dict:
    """1. Planner — decompose request into steps."""
    llm = _get_llm()
    steps = plan_task(llm, state["user_request"])
    return {
        "plan": steps,
        "current_step": 0,
        "step_results": [],
        "messages": [HumanMessage(content=f"Plan: {json.dumps(steps, indent=2)}")],
    }


def route_node(state: AgentState) -> dict:
    """Determine which agent should handle the current step."""
    user_input = state["user_request"]
    lower = user_input.lower()

    if any(w in lower for w in ["git ", "commit", "push", "branch", "status", "diff"]):
        agent_type = "git"
    elif any(w in lower for w in ["bash", "shell", "run ", "execute", "command", "terminal"]):
        agent_type = "bash"
    elif any(w in lower for w in ["mcp", "register tool"]):
        agent_type = "mcp"
    elif any(w in lower for w in ["read ", "write ", "edit ", "file ", "create "]):
        agent_type = "file"
    else:
        agent_type = "orchestrator"

    return {"agent_type": agent_type}


def execute_node(state: AgentState) -> dict:
    """Execute the current step using the appropriate agent."""
    llm = _get_llm()
    agent_type = state.get("agent_type", "orchestrator")
    user_input = state["user_request"]

    # Build context from memory and RAG
    memory = ConversationMemory()
    rag = RAGMemory()
    context_parts = []

    history = memory.format_for_llm(state["session_id"])
    if history:
        context_parts.append(history)

    rag_context = rag.format_context(user_input)
    if rag_context:
        context_parts.append(rag_context)

    context = "\n".join(context_parts)

    # Select and run the appropriate agent
    agents = {
        "file": create_file_agent,
        "bash": create_bash_agent,
        "git": create_git_agent,
        "mcp": create_mcp_agent,
        "orchestrator": create_orchestrator_agent,
    }

    agent_fn = agents.get(agent_type, create_orchestrator_agent)
    agent = agent_fn(llm)
    response = run_agent(agent, user_input, context)

    # Store in memory
    memory.add_message(state["session_id"], "user", user_input)
    memory.add_message(state["session_id"], "assistant", response[:500])

    step_results = state.get("step_results", []) + [response]

    return {
        "step_results": step_results,
        "current_step": state.get("current_step", 0) + 1,
        "final_response": response,
        "messages": [AIMessage(content=response[:2000])],
    }


def reflect_node(state: AgentState) -> dict:
    """Check if the plan is complete or needs revision."""
    current = state.get("current_step", 0)
    plan = state.get("plan", [])

    if current >= len(plan):
        return {"final_response": state.get("final_response", "")}

    # Check if we need to continue with next step
    return {"current_step": current}


# ═══════════════════════════════════════════════════════════════════════════════
# Conditional Routing
# ═══════════════════════════════════════════════════════════════════════════════

def should_continue(state: AgentState) -> Literal["execute", "reflect", "__end__"]:
    """Decide whether to continue execution or end."""
    current = state.get("current_step", 0)
    plan = state.get("plan", [])

    if not plan:
        return "reflect"  # No plan yet, go to reflect
    if current < len(plan):
        return "execute"  # More steps to execute
    return "__end__"  # All done


# ═══════════════════════════════════════════════════════════════════════════════
# Graph Construction
# ═══════════════════════════════════════════════════════════════════════════════

def build_graph():
    """Build the mini-claude-code LangGraph workflow."""
    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("plan", plan_node)
    builder.add_node("route", route_node)
    builder.add_node("execute", execute_node)
    builder.add_node("reflect", reflect_node)

    # Add edges
    builder.add_edge(START, "plan")
    builder.add_edge("plan", "route")
    builder.add_edge("route", "execute")
    builder.add_edge("execute", "reflect")

    # Conditional: continue or end
    builder.add_conditional_edges(
        "reflect",
        should_continue,
        {
            "execute": "execute",
            "reflect": "reflect",
            "__end__": END,
        },
    )

    return builder.compile()


def run_workflow(session_id: str, user_request: str) -> str:
    """Run the full workflow and return the final response."""
    graph = build_graph()
    initial_state: AgentState = {
        "session_id": session_id,
        "user_request": user_request,
        "plan": [],
        "current_step": 0,
        "step_results": [],
        "final_response": "",
        "messages": [],
        "agent_type": "orchestrator",
    }

    result = graph.invoke(initial_state)
    return result.get("final_response", "(no response generated)")
