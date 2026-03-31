# Repository Guidelines

## Project Structure & Module Organization

Application code lives under `src/tiny_agent_harness/`.

- `agents/`: class-based agent implementations and prompts for `SupervisorAgent`, `PlannerAgent`, `WorkerAgent`, and `ReviewerAgent`
- `agents/tool_calling_agent.py`: shared tool-calling base class used by planner/worker/reviewer
- `agents/protocols.py`: shared protocols and prompt-formatting helpers
- `channels/`: input/listener/output channel abstractions and the internal `IngressQueue`
- `llm/`: `LLMClient`, provider factory, and provider implementations under `llm/providers/`
- `schemas/`: Pydantic models for config, agent I/O, channels, skills, tools, and harness output
- `skills/`: built-in skill registry and skill implementations
- `tools/`: workspace tools such as `bash`, `read_file`, `search`, `list_files`, `git_diff`, and `apply_patch`
- `harness.py`: top-level orchestration loop
- `cli.py`: interactive CLI entry point exposed as the `tiny-agent` script

Repository-level files:

- `config.yaml`: local provider/model configuration
- `refactor_plan.md`: in-repo refactor checklist
- `tests/`: pytest-based coverage for agents, channels, CLI rendering, schema exports, and provider wiring

## Build, Test, and Development Commands

Use `uv` for local development. Prefer `uv run ...` over calling `python3` directly.

- `uv sync`: install project dependencies from `pyproject.toml` and `uv.lock`
- `uv run tiny-agent --config config.yaml`: run the interactive harness
- `uv run python -m tiny_agent_harness.cli --config config.yaml`: alternate CLI entry point
- `PYTHONPATH=src uv run pytest`: run the full test suite
- `PYTHONPATH=src uv run pytest tests/test_supervisor_agent.py`: run a focused test file

Use `OPENROUTER_API_KEY` or `OPENAI_API_KEY` when exercising live providers. Without an API key, provider creation paths that resolve environment credentials will fail.

## Coding Style & Naming Conventions

Use 4-space indentation and keep code compatible with Python 3.11+. Prefer small, typed modules with explicit imports. Runtime payloads should use Pydantic models from `schemas/`. Keep agent prompts adjacent to their agent modules, for example `agents/worker/prompt.py`. Keep orchestration in `harness.py`, LLM provider code in `llm/providers/`, and channel-specific behavior in `channels/`.

When extending agents, preserve the current class-based pattern:

- `SupervisorAgent` coordinates sub-agent execution directly
- `PlannerAgent`, `WorkerAgent`, and `ReviewerAgent` inherit from `ToolCallingAgent`
- shared typing and prompt helpers belong in `agents/protocols.py`

## Testing Guidelines

Use `pytest` and keep tests in `tests/test_<area>.py`. Prefer focused unit tests around agent behavior, schema validation, CLI rendering, provider selection, and channel behavior. When imports rely on the `src/` layout, run tests as `PYTHONPATH=src uv run pytest`.

Add or update tests for:

- schema or export-surface changes
- agent dispatch and tool-calling behavior
- provider factory or provider import-path changes
- CLI event rendering changes

Prefer isolated mocks or temporary directories for tool and filesystem behavior.

## Commit & Pull Request Guidelines

Commit messages should start with bracketed tags such as `[feat]`, `[refactor]`, or `[chore]`. Keep commits small and grouped by intent. Example: `[refactor] Remove agent wrapper functions`.

For pull requests, include:

- a short summary of behavior changes
- affected modules or directories
- test evidence, for example `PYTHONPATH=src uv run pytest`
- any required environment variables or provider assumptions
