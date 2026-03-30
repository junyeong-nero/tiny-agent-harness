from tiny_agent_harness.agents.planner.agent import planner_agent
from tiny_agent_harness.agents.supervisor.agent import SupervisorAgent, supervisor_agent

OrchestratorAgent = SupervisorAgent

__all__ = [
    "OrchestratorAgent",
    "planner_agent",
    "supervisor_agent",
    "orchestrator_agent",
]


def orchestrator_agent(*args, **kwargs):
    return supervisor_agent(*args, **kwargs)
