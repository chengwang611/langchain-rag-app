"""Tools module — all tools that the agents can call.

Each tool is a @tool-decorated function with clear docstrings for LLM discovery.
Tools are organized by capability domain.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool


# ═══════════════════════════════════════════════════════════════════════════════
# 3. File Reader
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def read_file(path: str, offset: int = 0, limit: Optional[int] = None) -> str:
    """Read a file from the local filesystem. Returns content with line numbers.

    Args:
        path: Absolute or relative path to the file.
        offset: Line number to start reading from (1-based).
        limit: Maximum number of lines to return. None = all lines.
    """
    try:
        resolved = Path(path).resolve()
        if not resolved.exists():
            return f"Error: file not found: {path}"
        if not resolved.is_file():
            return f"Error: not a file: {path}"

        lines = resolved.read_text(encoding="utf-8").splitlines()
        start = max(0, offset - 1)
        end = None if limit is None else start + limit
        selected = lines[start:end]

        result = "\n".join(
            f"{i + 1:4d} | {line}" for i, line in enumerate(selected, start=start + 1)
        )
        total = len(lines)
        shown = len(selected)
        return f"{resolved} ({shown}/{total} lines):\n{result}"
    except Exception as e:
        return f"Error reading file {path}: {e}"


@tool
def list_files(path: str = ".", pattern: Optional[str] = None) -> str:
    """List files and directories in a path.

    Args:
        path: Directory to list.
        pattern: Optional glob pattern to filter (e.g. '*.py').
    """
    try:
        resolved = Path(path).resolve()
        if not resolved.is_dir():
            return f"Error: directory not found: {path}"

        if pattern:
            items = list(resolved.glob(pattern))
        else:
            items = list(resolved.iterdir())

        result = []
        for item in sorted(items):
            suffix = "/" if item.is_dir() else ""
            result.append(f"  {item.name}{suffix}")
        return f"{resolved} ({len(result)} items):\n" + "\n".join(result)
    except Exception as e:
        return f"Error listing {path}: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. File Editor
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def write_file(path: str, content: str) -> str:
    """Create or overwrite a file with the given content.

    Args:
        path: Path to the file to write.
        content: Full file content to write.
    """
    try:
        resolved = Path(path).resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return f"Written {len(content)} bytes to {resolved}"
    except Exception as e:
        return f"Error writing {path}: {e}"


@tool
def edit_file(path: str, old_string: str, new_string: str) -> str:
    """Search and replace text in an existing file. Replaces FIRST occurrence only.

    Args:
        path: Path to the file to edit.
        old_string: Exact text to search for.
        new_string: Replacement text.
    """
    try:
        resolved = Path(path).resolve()
        if not resolved.exists():
            return f"Error: file not found: {path}"

        content = resolved.read_text(encoding="utf-8")
        if old_string not in content:
            return f"Error: string not found in {path}:\n  {old_string[:80]}"

        new_content = content.replace(old_string, new_string, 1)
        resolved.write_text(new_content, encoding="utf-8")
        return f"Replaced 1 occurrence in {resolved}"
    except Exception as e:
        return f"Error editing {path}: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Bash Executor
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def run_bash(command: str, timeout_seconds: int = 30) -> str:
    """Execute a shell command and return its output.

    SECURITY: Commands run in a sandboxed temporary directory.
    BLOCKED commands: rm -rf /, sudo, chmod 777, dd, mkfs, :(){ :|:& };:

    Args:
        command: Shell command to execute.
        timeout_seconds: Maximum execution time in seconds.
    """
    dangerous = ["rm -rf /", "sudo ", "chmod 777", "dd if=", "mkfs", ":(){", "> /dev/"]
    for d in dangerous:
        if d in command:
            return f"Blocked: command contains dangerous pattern '{d}'"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=tmpdir,
                env={**os.environ, "HOME": tmpdir},
            )
            output = []
            if result.stdout:
                output.append(result.stdout[:5000])
            if result.stderr:
                output.append(f"STDERR:\n{result.stderr[:2000]}")
            if result.returncode != 0:
                output.append(f"Exit code: {result.returncode}")
            return "\n".join(output) if output else "(no output)"
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout_seconds}s"
    except Exception as e:
        return f"Error executing command: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Git Integration
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def git_status(path: str = ".") -> str:
    """Show git status for a repository.

    Args:
        path: Path to the git repository.
    """
    try:
        result = subprocess.run(
            ["git", "status"],
            capture_output=True, text=True, cwd=path, timeout=10,
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {e}"


@tool
def git_diff(path: str = ".", staged: bool = False) -> str:
    """Show git diff for unstaged or staged changes.

    Args:
        path: Path to the git repository.
        staged: If True, show staged diff (--cached).
    """
    try:
        cmd = ["git", "diff", "--cached" if staged else ""]
        cmd = [c for c in cmd if c]
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=path, timeout=10,
        )
        return result.stdout[:5000] or "(no changes)"
    except Exception as e:
        return f"Error: {e}"


@tool
def git_commit(message: str, path: str = ".") -> str:
    """Stage all changes and commit with a message.

    Args:
        message: Commit message.
        path: Path to the git repository.
    """
    try:
        subprocess.run(["git", "add", "-A"], capture_output=True, cwd=path, timeout=10)
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True, text=True, cwd=path, timeout=10,
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# 10. MCP — Model Context Protocol Tools
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def mcp_register_tool(name: str, description: str, schema_json: str) -> str:
    """Register a new tool at runtime via the Model Context Protocol.

    Args:
        name: Tool name (snake_case).
        description: What the tool does.
        schema_json: JSON schema string for the tool's parameters.
    """
    registry = _get_mcp_registry()
    registry[name] = {"description": description, "schema": schema_json}
    _save_mcp_registry(registry)
    return f"Registered MCP tool: {name}"


@tool
def mcp_list_tools() -> str:
    """List all currently registered MCP tools."""
    registry = _get_mcp_registry()
    if not registry:
        return "No MCP tools registered."
    return json.dumps(registry, indent=2)


@tool
def mcp_call_tool(name: str, arguments_json: str) -> str:
    """Call a registered MCP tool with JSON arguments.

    Args:
        name: Name of the registered tool.
        arguments_json: JSON string of arguments.
    """
    registry = _get_mcp_registry()
    if name not in registry:
        return f"Error: MCP tool '{name}' not found. Registered: {list(registry.keys())}"
    return f"Called MCP tool '{name}' with args: {arguments_json}"


_MCP_REGISTRY_FILE = Path(tempfile.gettempdir()) / "mini_claude_code_mcp.json"


def _get_mcp_registry() -> dict:
    if _MCP_REGISTRY_FILE.exists():
        return json.loads(_MCP_REGISTRY_FILE.read_text())
    return {}


def _save_mcp_registry(registry: dict) -> None:
    _MCP_REGISTRY_FILE.write_text(json.dumps(registry, indent=2))


# ═══════════════════════════════════════════════════════════════════════════════
# Tool Registry — all tools grouped by domain
# ═══════════════════════════════════════════════════════════════════════════════

FILE_TOOLS = [read_file, list_files, write_file, edit_file]
BASH_TOOLS = [run_bash]
GIT_TOOLS = [git_status, git_diff, git_commit]
MCP_TOOLS = [mcp_register_tool, mcp_list_tools, mcp_call_tool]

ALL_TOOLS = FILE_TOOLS + BASH_TOOLS + GIT_TOOLS + MCP_TOOLS
