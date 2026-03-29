import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tiny_agent_harness.llm import create_llm_client
from tiny_agent_harness.channels import (
    EgressQueue,
    IngressQueue,
    OutputEventDispatcher,
    RequestProcessor,
)
from tiny_agent_harness.output_handlers import ConsoleOutputHandler
from tiny_agent_harness.schemas.config import load_config
from tiny_agent_harness.schemas import InputRequest
from tiny_agent_harness.schemas.runtime import RunRequest
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
    ingress_queue = IngressQueue()
    egress_queue = EgressQueue()
    processor = RequestProcessor(
        ingress_queue=ingress_queue,
        egress_queue=egress_queue,
        config=config,
        llm_client=llm_client,
        tool_caller=tool_caller,
    )
    dispatcher = OutputEventDispatcher(
        egress_queue=egress_queue,
        handlers=[ConsoleOutputHandler()],
    )
    ingress_queue.push(InputRequest(message_id="cli-1", payload=request))
    output = processor.process_next()
    if output is None:
        raise RuntimeError("request processor did not produce an output")

    print(f"provider: {config.provider}")
    print(f"mode: {'live_llm' if llm_client else 'mock'}")
    print(f"orchestrator model: {config.models.orchestrator}")
    print(f"executor model: {config.models.executor}")
    print(f"reviewer model: {config.models.reviewer}")

    dispatched = dispatcher.dispatch_next()
    if dispatched is None:
        raise RuntimeError("egress dispatcher did not dispatch an output")


if __name__ == "__main__":
    main()
