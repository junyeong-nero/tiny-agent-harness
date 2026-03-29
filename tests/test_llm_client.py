import sys
import unittest
from pathlib import Path

from pydantic import BaseModel


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cli import collecting_listener
from tiny_agent_harness.channels.listener import ListenerChannel
from tiny_agent_harness.llm import LLMClient
from tiny_agent_harness.providers import BaseProvider
from tiny_agent_harness.schemas import ListenerEvent, ModelsConfig


class ReviewSchema(BaseModel):
    ok: bool


class FakeProvider(BaseProvider):
    provider_name = "fake"

    def __init__(self, responses: list[str], failures_before_success: int = 0) -> None:
        super().__init__(api_key="fake-key", default_model="default-model")
        self.responses = responses
        self.failures_before_success = failures_before_success
        self.calls = 0
        self.last_messages = None
        self.last_model = None

    def chat(self, messages, model=None) -> str:
        self.calls += 1
        self.last_messages = list(messages)
        self.last_model = model

        if self.failures_before_success > 0:
            self.failures_before_success -= 1
            raise RuntimeError("temporary failure")

        if not self.responses:
            raise RuntimeError("no fake response configured")

        return self.responses.pop(0)


class LLMClientTestCase(unittest.TestCase):
    def test_chat_uses_agent_specific_model(self) -> None:
        provider = FakeProvider(responses=["ok"])
        client = LLMClient(
            provider=provider,
            models=ModelsConfig(
                default="default-model",
                executor="executor-model",
            ),
        )

        result = client.chat(
            messages=[{"role": "user", "content": "hello"}],
            agent_name="executor",
        )

        self.assertEqual(result, "ok")
        self.assertEqual(provider.last_model, "executor-model")

    def test_chat_retries_until_success(self) -> None:
        provider = FakeProvider(
            responses=["ok after retry"],
            failures_before_success=2,
        )
        client = LLMClient(
            provider=provider,
            models=ModelsConfig(default="default-model"),
            max_retries=2,
        )

        result = client.chat(
            messages=[{"role": "user", "content": "retry please"}],
            agent_name="orchestrator",
        )

        self.assertEqual(result, "ok after retry")
        self.assertEqual(provider.calls, 3)

    def test_chat_structured_returns_validated_pydantic_model(self) -> None:
        provider = FakeProvider(responses=['{"ok": true}'])
        client = LLMClient(
            provider=provider,
            models=ModelsConfig(default="default-model"),
        )

        result = client.chat_structured(
            messages=[{"role": "user", "content": "return json"}],
            agent_name="reviewer",
            response_model=ReviewSchema,
        )

        self.assertEqual(result, ReviewSchema(ok=True))
        self.assertEqual(provider.last_messages[0]["role"], "system")
        self.assertIn("Return valid JSON only", provider.last_messages[0]["content"])
        self.assertIn('"title": "ReviewSchema"', provider.last_messages[0]["content"])

    def test_chat_structured_retries_after_validation_failure(self) -> None:
        provider = FakeProvider(
            responses=["not json", '{"ok": true}'],
        )
        client = LLMClient(
            provider=provider,
            models=ModelsConfig(default="default-model"),
            max_retries=1,
        )

        result = client.chat_structured(
            messages=[{"role": "user", "content": "return json"}],
            agent_name="reviewer",
            response_model=ReviewSchema,
        )

        self.assertEqual(result.ok, True)
        self.assertEqual(provider.calls, 2)

    def test_chat_emits_listener_events(self) -> None:
        provider = FakeProvider(responses=["ok"])
        events: list[ListenerEvent] = []
        listener = ListenerChannel()
        listener.add_channel("collector", collecting_listener(events))
        client = LLMClient(
            provider=provider,
            models=ModelsConfig(default="default-model"),
            listeners=listener,
        )

        result = client.chat(
            messages=[{"role": "user", "content": "hello"}],
            agent_name="executor",
        )

        self.assertEqual(result, "ok")
        self.assertEqual([event.kind for event in events], ["llm_request", "llm_response"])
        self.assertEqual(events[0].agent, "executor")


if __name__ == "__main__":
    unittest.main()
