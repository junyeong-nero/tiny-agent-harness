from tiny_agent_harness.agents.planner.agent import PlannerAgent, planner_agent


OrchestratorAgent = PlannerAgent

__all__ = ["OrchestratorAgent", "planner_agent", "orchestrator_agent"]


def orchestrator_agent(*args, **kwargs):
    return planner_agent(*args, **kwargs)
