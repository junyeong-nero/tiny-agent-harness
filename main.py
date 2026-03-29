import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tiny_agent_harness.llm import create_llm_client
from tiny_agent_harness.schemas.config import load_config
from tiny_agent_harness.schemas.runtime import RunRequest
from tiny_agent_harness.runtime import run_harness
from tiny_agent_harness.tools import create_default_tool_caller


def _resolve_provider_api_key(provider_name: str) -> str | None:
    normalized = provider_name.strip().lower()
    if normalized == "openrouter":
        return os.getenv("OPENROUTER_API_KEY")
    if normalized == "openai":
        return os.getenv("OPENAI_API_KEY")
    return None


def main():
    config = load_config()
    goal = " ".join(sys.argv[1:]).strip() or "Run the tiny-agent-harness demo loop."
    request = RunRequest(goal=goal)
    api_key = _resolve_provider_api_key(config.provider)
    llm_client = create_llm_client(config, api_key=api_key) if api_key else None
    tool_caller = create_default_tool_caller(
        str(PROJECT_ROOT),
        actor_permissions=config.tools.as_actor_permissions(),
    )
    state, result = run_harness(request, config, llm_client=llm_client, tool_caller=tool_caller)

    print(f"provider: {config.provider}")
    print(f"mode: {'live_llm' if llm_client else 'mock'}")
    print(f"orchestrator model: {config.models.orchestrator}")
    print(f"executor model: {config.models.executor}")
    print(f"reviewer model: {config.models.reviewer}")
    print(f"goal: {request.goal}")
    print(f"task: {state.current_task.id if state.current_task else 'none'}")
    print(f"executor status: {state.last_executor_result.status if state.last_executor_result else 'none'}")
    print(f"review decision: {state.last_review_result.decision if state.last_review_result else 'none'}")
    print(f"result: {result.summary}")


if __name__ == "__main__":
    main()
