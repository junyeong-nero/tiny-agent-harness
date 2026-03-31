import unittest


class TestToolCallingAgent(unittest.TestCase):
    def test_tool_calling_agent_is_importable_from_new_module(self):
        from tiny_agent_harness.agents.tool_calling_agent import ToolCallingAgent

        self.assertEqual(ToolCallingAgent.__name__, "ToolCallingAgent")

