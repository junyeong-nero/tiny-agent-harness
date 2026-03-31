import unittest

from tiny_agent_harness.schemas import ToolResult, ToolSpec


class TestAgentsProtocols(unittest.TestCase):
    def test_protocols_module_exports_shared_agent_helpers(self):
        from tiny_agent_harness.agents.protocols import (
            SupportsStructuredLLM,
            format_tool_catalog,
            format_tool_result,
        )

        self.assertEqual(SupportsStructuredLLM.__name__, "SupportsStructuredLLM")

        catalog = format_tool_catalog(
            [
                ToolSpec(
                    name="search",
                    description="Search the workspace",
                    arguments_schema={"type": "object"},
                )
            ]
        )
        self.assertIn("- search: Search the workspace", catalog)

        result = format_tool_result(
            ToolResult(tool="search", ok=True, content="match", error=None)
        )
        self.assertIn("tool=search", result)
        self.assertIn("ok=True", result)

