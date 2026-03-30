"""
Pre-mock modules that are broken at import time due to in-progress refactoring.
These mocks must be registered before any tiny_agent_harness package is imported.
"""
import sys
from unittest.mock import MagicMock

# harness.py references old schema fields and is not yet updated
if "tiny_agent_harness.harness" not in sys.modules:
    sys.modules["tiny_agent_harness.harness"] = MagicMock()
