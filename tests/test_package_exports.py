import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import tiny_agent_harness


class PackageExportsTestCase(unittest.TestCase):
    def test_public_exports_do_not_include_removed_symbols(self) -> None:
        self.assertNotIn("CollectingOutputHandler", tiny_agent_harness.__all__)
        self.assertNotIn("ConsoleOutputHandler", tiny_agent_harness.__all__)
        self.assertNotIn("OutputEventDispatcher", tiny_agent_harness.__all__)
        self.assertNotIn("RequestProcessor", tiny_agent_harness.__all__)
        self.assertNotIn("CollectingListenerHandler", tiny_agent_harness.__all__)
        self.assertNotIn("ConsoleListenerHandler", tiny_agent_harness.__all__)
        self.assertIn("InputChannel", tiny_agent_harness.__all__)
        self.assertIn("ListenerChannel", tiny_agent_harness.__all__)
        self.assertIn("run_harness", tiny_agent_harness.__all__)


if __name__ == "__main__":
    unittest.main()
