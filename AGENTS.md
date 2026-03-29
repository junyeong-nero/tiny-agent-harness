# Repository Guidelines

## Project Structure & Module Organization

Application code lives under `src/tiny_agent_harness/`.

- `agents/`: role-specific agent logic and prompts (`orchestrator`, `executor`, `reviewer`)
- `llm/`: LLM client and provider factory
- `providers/`: vendor adapters such as OpenRouter and OpenAI
- `schemas/`: Pydantic models for config and runtime messages
- `tools/`: workspace tools such as `bash`, `read_file`, `search`, and `git_diff`
- `runtime.py`: top-level loop orchestration

Repository-level files:

- `main.py`: local entry point
- `config.yaml`: provider and model selection
- `tests/`: `unittest`-based coverage for runtime, LLM, providers, and tools

## Build, Test, and Development Commands

- `uv sync`: install project dependencies from `pyproject.toml` and `uv.lock`
- `python3 main.py "demo goal"`: run the harness locally
- `python3 -m unittest tests.test_runtime`: run a focused runtime test
- `python3 -m unittest tests.test_runtime tests.test_providers tests.test_llm_factory tests.test_llm_client tests.test_tools`: run the full test suite

Use `OPENROUTER_API_KEY` to enable live OpenRouter execution. Without an API key, the runtime should stay on its mock path.

## Coding Style & Naming Conventions

Use 4-space indentation and keep code Python 3.13-compatible. Prefer small, typed modules with explicit imports. Runtime payloads should use Pydantic models from `schemas/`. New agent-specific prompts belong next to the agent, for example `agents/executor/prompt.py`. Keep orchestration in `runtime.py` and vendor-specific HTTP code in `providers/`.

## Testing Guidelines

Use the standard library `unittest` framework. Name test files `tests/test_<area>.py` and keep test methods descriptive, for example `test_chat_structured_retries_after_validation_failure`. Add tests for new schema validation, provider behavior, and tool execution paths. Prefer isolated temporary directories for file and git tool tests.

## Commit & Pull Request Guidelines

Commit messages should start with bracketed tags, as seen in history: `[feat]`, `[refactor]`, `[chore]`. Keep commits small and grouped by intent. Example: `[feat] Add core workspace tools and tests`.

For pull requests, include:

- a short summary of behavior changes
- affected modules or directories
- test evidence (`python3 -m unittest ...`)
- any required environment variables or provider assumptions
