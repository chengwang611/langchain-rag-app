# mini-claude-code

A minimal Claude Code-like agent built with **LangChain** and **LangGraph**.
Demonstrates 10 core capabilities in ~1,000 lines of Python.

## Architecture

```
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
```

## 10 Capabilities

| # | Capability | File | Key Function |
|---|---|---|---|
| 1 | **Planner** | [`agents.py`](agents.py:14) | `plan_task()` — decomposes requests into step-by-step plans |
| 2 | **Tool Calling** | [`agents.py`](agents.py:120) | `run_agent()` — LLM-driven tool selection and invocation loop |
| 3 | **File Reader** | [`tools.py`](tools.py:27) | `read_file()` — read files with line numbers |
| 4 | **File Editor** | [`tools.py`](tools.py:82) | `write_file()` / `edit_file()` — create and modify files |
| 5 | **Bash Executor** | [`tools.py`](tools.py:107) | `run_bash()` — sandboxed shell command execution |
| 6 | **Git Integration** | [`tools.py`](tools.py:143) | `git_status()` / `git_diff()` / `git_commit()` |
| 7 | **Multi-Agent** | [`agents.py`](agents.py:70) | 5 specialized agents + orchestrator routing |
| 8 | **Memory** | [`memory.py`](memory.py:33) | `ConversationMemory` — SQLite-backed chat history |
| 9 | **RAG** | [`memory.py`](memory.py:103) | `RAGMemory` — vector store with semantic retrieval |
| 10 | **MCP** | [`tools.py`](tools.py:175) | `mcp_register_tool()` / `mcp_call_tool()` — dynamic tool registration |

## LangGraph Workflow

```
START → plan → route → execute → reflect → END
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         file_agent   bash_agent   git_agent
              │            │            │
              └────────────┼────────────┘
                           ▼
                      mcp_agent
```

Defined in [`graph.py`](graph.py:100) — `build_graph()` assembles the `StateGraph`.

## Usage

```bash
# Interactive mode
python -m mini_claude_code.main --interactive

# Single request
python -m mini_claude_code.main "Read the file src/mini_claude_code/__init__.py"
python -m mini_claude_code.main "Run git status"
python -m mini_claude_code.main "Create a new Python file hello.py"
```

### Interactive Commands

| Command | Action |
|---|---|
| `exit` / `quit` | Exit the REPL |
| `tools` | List all available tools |
| `clear` | Clear conversation history |
| `help` | Show help |

## File Structure

```
src/mini_claude_code/
├── __init__.py    # Package docstring with capability overview
├── tools.py       # All @tool-decorated functions (file, bash, git, MCP)
├── memory.py      # ConversationMemory (SQLite) + RAGMemory (vector store)
├── agents.py      # Planner + 5 specialized agents + orchestrator
├── graph.py       # LangGraph StateGraph workflow definition
├── main.py        # CLI entrypoint (interactive + single-shot modes)
└── README.md      # This file
```

## Dependencies

- `langchain>=0.3.0`
- `langchain-core>=0.3.0`
- `langchain-openai>=0.2.0`
- `langgraph>=0.2.0`
- `openai>=1.40.0`

## Design Decisions

1. **No external vector DB** — RAG uses `InMemoryVectorStore` with a simple n-gram embedding. Swap to `OpenAIEmbeddings` + `PGVector` for production.
2. **SQLite for memory** — Zero-dependency persistence. Swap to PostgreSQL for multi-user.
3. **Sandboxed bash** — Commands run in a temp directory with dangerous patterns blocked.
4. **MCP registry** — JSON file in `/tmp` for runtime tool registration. In production, use a proper MCP server.
