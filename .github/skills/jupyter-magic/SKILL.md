# Skill: Jupyter Context Management (Context-First)

## Description

This skill enables agents to manage a modular, multi-notebook architecture designed for high-performance context retrieval and "Agentic Governance." It prioritizes separating tool testing, architectural decisions, and operational runbooks into distinct "Context-Bounds."

## Philosophies

- **Token Efficiency**: Only provide the notebook relevant to the current sub-task (e.g., discovery.ipynb for tool probing).
- **Red/Green Notebooks**: Notebooks are for TDD and Evals, not just code.
- **Git Hygiene**: Never commit notebook outputs. The code and markdown are the "source of truth"; outputs are ephemeral.
- **Beads Memory**: Use Markdown headers (##, ###) to create a "State Map" that the agent can navigate via the Outline View.

## Directory Structure

- `notebooks/discovery.ipynb`: Tool probing and MCP server debugging.
- `notebooks/arch.ipynb`: Architectural "Beads" and design decisions.
- `notebooks/ops.ipynb`: Runbooks, failover scripts, and infrastructure tasks.
- `notebooks/scratchpad.ipynb`: Temporary execution and disposable snippets.

## Protocol for Agents

### Context Loading

Before starting a task, identify which notebook contains the relevant state.

### Execution

Run code in small, atomic cells. Document the intent of the cell in a preceding Markdown block.

### State Capture

If a tool output is significant (e.g., a new MCP tool schema), transcribe the core result into arch.ipynb.

### Sanitation

Prior to finishing a task, invoke the git-sanitize recipe to clear execution counts and outputs.

## Commands (Integrate with justfile)

```bash
just sanitize: Runs python jupyter-magic/scripts/git_sanitize.py to clean all notebooks.
```
