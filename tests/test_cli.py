import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import cli
from tiny_agent_harness.channels import InputChannel, OutputChannel
from tiny_agent_harness.handlers.listener import ListenerChannel
from tiny_agent_harness.schemas import (
    AppConfig,
    LLMConfig,
    ModelsConfig,
    RunResult,
    RunState,
    RuntimeConfig,
    ToolPermissionsConfig,
)


class CLITestCase(unittest.TestCase):
    def test_main_passes_provider_api_key_to_harness(self) -> None:
        state = RunState(task="demo goal", done=True)
        result = RunResult(status="completed", summary="demo summary")
        config = AppConfig(
            provider="openrouter",
            models=ModelsConfig(default="demo-model"),
            llm=LLMConfig(),
            runtime=RuntimeConfig(),
            tools=ToolPermissionsConfig(),
        )

        with (
            patch.object(sys, "argv", ["main.py", "demo goal"]),
            patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}, clear=True),
            patch("cli.load_config", return_value=config) as load_config,
            patch(
                "cli.create_llm_client", return_value="llm-client"
            ) as create_llm_client,
            patch("cli.run_harness", return_value=(state, result)) as run_harness,
        ):
            cli.main()

        load_config.assert_called_once()
        create_llm_client.assert_called_once_with(config, api_key="test-key")
        run_harness.assert_called_once()
        _, kwargs = run_harness.call_args
        self.assertEqual(kwargs["llm_client"], "llm-client")
        self.assertIsInstance(kwargs["listeners"], ListenerChannel)
        self.assertIsInstance(kwargs["output_handler"], OutputChannel)
        self.assertIsInstance(kwargs["input_channel"], InputChannel)
        self.assertFalse(kwargs["input_channel"].is_empty())
        self.assertEqual(kwargs["input_channel"].dequeue().payload.goal, "demo goal")

    def test_main_raises_when_provider_api_key_is_missing(self) -> None:
        config = AppConfig(
            provider="openrouter",
            models=ModelsConfig(default="demo-model"),
            llm=LLMConfig(),
            runtime=RuntimeConfig(),
            tools=ToolPermissionsConfig(),
        )

        with (
            patch.object(sys, "argv", ["main.py", "demo goal"]),
            patch.dict("os.environ", {}, clear=True),
            patch("cli.load_config", return_value=config),
        ):
            with self.assertRaisesRegex(
                ValueError, "missing API key for provider: openrouter"
            ):
                cli.main()

    def test_main_runs_interactively_until_quit(self) -> None:
        state = RunState(task="demo goal", done=True)
        result = RunResult(status="completed", summary="demo summary")
        config = AppConfig(
            provider="openrouter",
            models=ModelsConfig(default="demo-model"),
            llm=LLMConfig(),
            runtime=RuntimeConfig(),
            tools=ToolPermissionsConfig(),
        )

        with (
            patch.object(sys, "argv", ["main.py"]),
            patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}, clear=True),
            patch("cli.load_config", return_value=config),
            patch("cli.create_llm_client", return_value="llm-client"),
            patch("cli.run_harness", return_value=(state, result)) as run_harness,
            patch("builtins.input", side_effect=["demo goal", "quit"]),
        ):
            cli.main()

        run_harness.assert_called_once()
        _, kwargs = run_harness.call_args
        self.assertEqual(kwargs["input_channel"].dequeue().payload.goal, "demo goal")


if __name__ == "__main__":
    unittest.main()
