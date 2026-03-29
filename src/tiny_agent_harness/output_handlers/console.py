from tiny_agent_harness.output_handlers.base import OutputHandler
from tiny_agent_harness.schemas import OutputEvent


class ConsoleOutputHandler(OutputHandler):
    def handle(self, event: OutputEvent) -> None:
        payload = event.payload
        state = payload.state
        result = payload.result

        print(f"goal: {payload.request.goal}")
        print(f"task: {state.current_task.id if state.current_task else 'none'}")
        print(
            "executor status: "
            f"{state.last_executor_result.status if state.last_executor_result else 'none'}"
        )
        print(
            "review decision: "
            f"{state.last_review_result.decision if state.last_review_result else 'none'}"
        )
        print(f"result: {result.summary}")
