# tiny-agent-harness

`tiny-agent-harness` is a toy multi-agent harness for experimenting with a fixed 3-agent loop.
It is intentionally small in scope, easy to inspect, and not production-oriented.

## Overview

This repository is a minimal runtime for a small `orchestrator -> executor -> reviewer` workflow.
It aims to stay simple enough to understand end-to-end while still leaving room for configurable
models, pluggable I/O, and lightweight behavioral extensions.

## Architecture

The harness is built around a fixed 3-agent structure:

1. `orchestrator`
   Owns the goal, state, control flow, and external input/output.
2. `executor`
   Performs the assigned task and produces structured execution results.
3. `reviewer`
   Checks executor output and returns a structured review decision.

Runtime loop:

```text
goal -> orchestrator -> executor -> reviewer -> state update -> next step / stop
```

Only `orchestrator` should interact with external input and output channels.
`executor` and `reviewer` should operate only on internal runtime messages and return structured
results back to `orchestrator`.

## Runtime Model

- `OpenRouter` as the default LLM provider
- `config.yaml` for provider, model, retry, and runtime step settings
- pluggable `channels` for external input and output
- pluggable `listeners` for internal runtime events
- Markdown-based `skills` for lightweight behavior customization
- schema-driven tool calling through a shared `ToolCaller`

Minimal configuration:

```yaml
provider: openrouter

models:
  default: nvidia/nemotron-3-super-120b-a12b:free
  orchestrator: nvidia/nemotron-3-super-120b-a12b:free
  executor: nvidia/nemotron-3-super-120b-a12b:free
  reviewer: nvidia/nemotron-3-super-120b-a12b:free

llm:
  max_retries: 2

runtime:
  orchestrator_max_tool_steps: 2
  executor_max_tool_steps: 3
  reviewer_max_tool_steps: 3

tools:
  orchestrator:
    - list_files
    - search
  executor:
    - bash
    - read_file
    - search
    - list_files
    - apply_patch
  reviewer:
    - read_file
    - search
    - list_files
    - git_diff
```

Suggested skill layout:

```text
skills/
  base/
    executor/
      SKILL.md
    reviewer/
      SKILL.md
  custom/
    some-skill/
      SKILL.md
```

Skills are read from Markdown and injected into agent context before execution.

Tool access is assigned per role:

- `orchestrator`: `list_files`, `search`
- `executor`: `bash`, `read_file`, `search`, `list_files`, `apply_patch`
- `reviewer`: `read_file`, `search`, `list_files`, `git_diff`

All tool calls are schema-driven. Each tool exposes a description and argument schema, and the
shared caller layer enforces role-based access before execution.

## Current Status

The project is still in an early scaffold stage. The next step is to build the smallest possible
version of the agreed design:

- load provider and model settings from `config.yaml`
- run the fixed 3-agent loop
- expose basic input/output channels
- support Markdown-based skills
- provide a small core tool set for execution and review

## Tech Stack

- Python 3.13+
- OpenRouter as the default provider
- uv for dependency management

## Getting Started

Install dependencies:

```bash
uv sync
```

Run the project:

```bash
uv run python main.py
```
