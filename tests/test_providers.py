import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tiny_agent_harness.providers import BaseProvider, OpenAIProvider, OpenRouterProvider


class FakeProvider(BaseProvider):
    provider_name = "fake"

    def __init__(self) -> None:
        super().__init__(api_key="fake-key", default_model="fake-model")
        self.last_messages = None
        self.last_model = None

    def chat(self, messages, model=None) -> str:
        self.last_messages = list(messages)
        self.last_model = self.resolve_model(model)
        return "ok"


class ProviderTestCase(unittest.TestCase):
    def test_base_provider_prompt_builds_messages(self) -> None:
        provider = FakeProvider()

        result = provider.prompt(
            user_prompt="say hi",
            system_prompt="be concise",
        )

        self.assertEqual(result, "ok")
        self.assertEqual(provider.last_model, "fake-model")
        self.assertEqual(
            provider.last_messages,
            [
                {"role": "system", "content": "be concise"},
                {"role": "user", "content": "say hi"},
            ],
        )

    def test_openrouter_provider_uses_default_base_url(self) -> None:
        provider = OpenRouterProvider(
            api_key="test-key",
            default_model="test-model",
        )

        self.assertEqual(provider.provider_name, "openrouter")
        self.assertEqual(provider.base_url, OpenRouterProvider.default_base_url)
        self.assertEqual(provider.resolve_model(), "test-model")

    def test_openai_provider_uses_explicit_model(self) -> None:
        provider = OpenAIProvider(
            api_key="test-key",
            default_model="default-model",
        )

        self.assertEqual(provider.provider_name, "openai")
        self.assertEqual(provider.resolve_model("override-model"), "override-model")


if __name__ == "__main__":
    unittest.main()
