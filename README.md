# tiny-agent-harness

`tiny-agent-harness` is a toy multi-agent harness for experimenting with a fixed 3-agent loop.
It is intentionally small in scope, easy to inspect, and not production-oriented.

## Overview

This repository is a minimal runtime for a small `main_loop -> executor -> reviewer` workflow.
It aims to stay simple enough to understand end-to-end while still leaving room for configurable
models, pluggable I/O, and lightweight behavioral extensions.

## Architecture

The harness is built around a fixed 3-agent structure:

1. `main_loop`
   Owns the goal, state, control flow, and external input/output.
2. `executor`
   Performs the assigned task and produces structured execution results.
3. `reviewer`
   Checks executor output and returns a structured review decision.

Runtime loop:

```text
goal -> main_loop -> executor -> reviewer -> state update -> next step / stop
```

Only `main_loop` should interact with external input and output channels.
`executor` and `reviewer` should operate only on internal runtime messages and return structured
results back to `main_loop`.

## Runtime Model

- `OpenRouter` as the default LLM provider
- `config.yaml` for provider and model selection
- pluggable `channels` for external input and output
- pluggable `listeners` for internal runtime events
- Markdown-based `skills` for lightweight behavior customization

Minimal configuration:

```yaml
provider: openrouter

models:
  default: nvidia/nemotron-3-super-120b-a12b:free
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

- `main_loop`: `list_files`, `search`
- `executor`: `bash`, `read_file`, `search`, `list_files`, `apply_patch`
- `reviewer`: `read_file`, `search`, `list_files`, `git_diff`

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
