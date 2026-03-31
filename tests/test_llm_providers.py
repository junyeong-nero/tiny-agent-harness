import unittest

from tiny_agent_harness import BaseProvider, OpenAIProvider, OpenRouterProvider
from tiny_agent_harness.llm.factory import create_provider
from tiny_agent_harness.schemas import Config, ModelsConfig


class TestLLMProviders(unittest.TestCase):
    def test_package_reexports_provider_types(self):
        from tiny_agent_harness.llm.providers import (
            BaseProvider as InternalBaseProvider,
            OpenAIProvider as InternalOpenAIProvider,
            OpenRouterProvider as InternalOpenRouterProvider,
        )

        self.assertIs(BaseProvider, InternalBaseProvider)
        self.assertIs(OpenAIProvider, InternalOpenAIProvider)
        self.assertIs(OpenRouterProvider, InternalOpenRouterProvider)

    def test_create_provider_returns_openai_provider(self):
        config = Config(provider="openai", models=ModelsConfig(default="gpt-4o-mini"))

        provider = create_provider(config=config, api_key="test-key")

        self.assertIsInstance(provider, OpenAIProvider)
        self.assertEqual(provider.default_model, "gpt-4o-mini")

    def test_create_provider_returns_openrouter_provider(self):
        config = Config(
            provider="openrouter", models=ModelsConfig(default="openai/gpt-4o-mini")
        )

        provider = create_provider(config=config, api_key="test-key")

        self.assertIsInstance(provider, OpenRouterProvider)
        self.assertEqual(provider.default_model, "openai/gpt-4o-mini")

