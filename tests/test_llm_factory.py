import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tiny_agent_harness.llm import LLMClient, create_llm_client, create_provider
from tiny_agent_harness.providers import OpenAIProvider, OpenRouterProvider
from tiny_agent_harness.schemas import AppConfig, ModelsConfig


class LLMFactoryTestCase(unittest.TestCase):
    def test_create_provider_returns_openrouter_provider(self) -> None:
        config = AppConfig(
            provider="openrouter",
            models=ModelsConfig(default="demo-model"),
        )

        provider = create_provider(config, api_key="test-key")

        self.assertIsInstance(provider, OpenRouterProvider)
        self.assertEqual(provider.default_model, "demo-model")

    def test_create_provider_returns_openai_provider(self) -> None:
        config = AppConfig(
            provider="openai",
            models=ModelsConfig(default="demo-model"),
        )

        provider = create_provider(config, api_key="test-key")

        self.assertIsInstance(provider, OpenAIProvider)
        self.assertEqual(provider.default_model, "demo-model")

    def test_create_llm_client_builds_llm_layer(self) -> None:
        config = AppConfig(
            provider="openrouter",
            models=ModelsConfig(default="demo-model"),
        )

        client = create_llm_client(config, api_key="test-key", max_retries=3)

        self.assertIsInstance(client, LLMClient)
        self.assertIsInstance(client.provider, OpenRouterProvider)
        self.assertEqual(client.max_retries, 3)

    def test_create_provider_rejects_unknown_provider(self) -> None:
        config = AppConfig(
            provider="unknown",
            models=ModelsConfig(default="demo-model"),
        )

        with self.assertRaises(ValueError):
            create_provider(config, api_key="test-key")


if __name__ == "__main__":
    unittest.main()
