import unittest

import tiny_agent_harness.agents as agents
import tiny_agent_harness.agents.planner.agent as planner_module
import tiny_agent_harness.agents.verifier.agent as verifier_module
import tiny_agent_harness.agents.supervisor.agent as supervisor_module
import tiny_agent_harness.agents.worker.agent as worker_module
from tiny_agent_harness.agents import (
    PlannerAgent,
    VerifierAgent,
    SupervisorAgent,
    WorkerAgent,
)


class TestAgentExports(unittest.TestCase):
    def test_agents_package_exports_agent_classes(self):
        self.assertEqual(
            set(agents.__all__),
            {"PlannerAgent", "VerifierAgent", "SupervisorAgent", "WorkerAgent"},
        )
        self.assertIs(agents.PlannerAgent, PlannerAgent)
        self.assertIs(agents.VerifierAgent, VerifierAgent)
        self.assertIs(agents.SupervisorAgent, SupervisorAgent)
        self.assertIs(agents.WorkerAgent, WorkerAgent)

    def test_wrapper_functions_removed_from_agent_modules(self):
        self.assertFalse(hasattr(planner_module, "planner_agent"))
        self.assertFalse(hasattr(worker_module, "worker_agent"))
        self.assertFalse(hasattr(verifier_module, "verifier_agent"))
        self.assertFalse(hasattr(supervisor_module, "supervisor_agent"))
