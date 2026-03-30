SUPERVISOR_PIPELINE_LABEL = "planner -> worker -> reviewer"

SUPERVISOR_ROLE_DESCRIPTION = (
    "Supervisor coordinates the serial multi-agent pipeline. "
    "It executes planner decisions, optionally runs the worker, and always asks the reviewer "
    "for approval before the cycle completes."
)

__all__ = ["SUPERVISOR_PIPELINE_LABEL", "SUPERVISOR_ROLE_DESCRIPTION"]
