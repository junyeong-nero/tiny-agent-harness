import unittest

from tiny_agent_harness import schemas


class TestSchemasExports(unittest.TestCase):
    def test___all___matches_reexported_names(self):
        public_names = {
            name: value
            for name, value in vars(schemas).items()
            if not name.startswith("_") and name not in {"agents", "channels", "config", "harness", "skills", "tools"}
        }

        self.assertEqual(set(schemas.__all__), set(public_names))

    def test_no_missing_or_dead_public_exports(self):
        for name in schemas.__all__:
            self.assertTrue(hasattr(schemas, name), msg=f"missing re-export: {name}")
