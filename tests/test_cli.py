import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tiny_agent_harness import cli
from tiny_agent_harness.schemas import AppConfig, LLMConfig, ModelsConfig, RuntimeConfig, ToolPermissionsConfig


class CLITestCase(unittest.TestCase):
    def test_main_uses_packaged_config_and_cwd_by_default(self) -> None:
        config = AppConfig(
            provider="openai",
            models=ModelsConfig(default="demo-model"),
            llm=LLMConfig(),
            runtime=RuntimeConfig(),
            tools=ToolPermissionsConfig(),
        )
        harness = self._make_harness_double()

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.object(cli.Path, "cwd", return_value=Path(tmpdir)),
            patch("tiny_agent_harness.cli.load_config", return_value=config) as load_config,
            patch("tiny_agent_harness.cli.TinyHarness", return_value=harness) as tiny_harness,
            patch("builtins.input", side_effect=["quit"]),
        ):
            exit_code = cli.main([])

        self.assertEqual(exit_code, 0)
        load_config.assert_called_once_with(None)
        tiny_harness.assert_called_once_with(
            config=config,
            workspace_root=str(Path(tmpdir).resolve()),
        )
        harness.ch_input.queue.assert_not_called()
        harness.run.assert_not_called()

    def test_main_accepts_explicit_config_workspace_and_prompt(self) -> None:
        config = AppConfig(
            provider="openai",
            models=ModelsConfig(default="demo-model"),
            llm=LLMConfig(),
            runtime=RuntimeConfig(),
            tools=ToolPermissionsConfig(),
        )
        harness = self._make_harness_double()

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("tiny_agent_harness.cli.load_config", return_value=config) as load_config,
            patch("tiny_agent_harness.cli.TinyHarness", return_value=harness) as tiny_harness,
        ):
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir()
            config_path = Path(tmpdir) / "custom-config.yaml"
            config_path.write_text("provider: openai\nmodels:\n  default: demo-model\n", encoding="utf-8")
            exit_code = cli.main(
                [
                    "--config",
                    str(config_path),
                    "--workspace",
                    str(workspace),
                    "inspect",
                    "repo",
                ]
            )

        self.assertEqual(exit_code, 0)
        load_config.assert_called_once_with(config_path)
        tiny_harness.assert_called_once_with(
            config=config,
            workspace_root=str(workspace.resolve()),
        )
        harness.ch_input.queue.assert_called_once_with("inspect repo")
        harness.run.assert_called_once()

    @staticmethod
    def _make_harness_double():
        class _ChannelDouble:
            def __init__(self) -> None:
                self.add_channel = unittest.mock.Mock()

        class _InputDouble:
            def __init__(self) -> None:
                self.queue = unittest.mock.Mock()

        class _HarnessDouble:
            def __init__(self) -> None:
                self.ch_output = _ChannelDouble()
                self.ch_listener = _ChannelDouble()
                self.ch_input = _InputDouble()
                self.run = unittest.mock.Mock()

        return _HarnessDouble()


if __name__ == "__main__":
    unittest.main()
