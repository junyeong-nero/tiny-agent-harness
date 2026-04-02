import unittest
from typing import Sequence

from pydantic import BaseModel

from tiny_agent_harness.llm.client import LLMClient
from tiny_agent_harness.llm.providers import BaseProvider, ChatMessage
from tiny_agent_harness.schemas import ModelsConfig


class StructuredReply(BaseModel):
    answer: str
    count: int


class StubProvider(BaseProvider):
    provider_name = "stub"

    def __init__(self, responses: Sequence[object]) -> None:
        super().__init__(api_key="test-key", default_model="stub-model")
        self._responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def chat(self, messages: Sequence[ChatMessage], model: str | None = None) -> str:
        self.calls.append(
            {
                "messages": [dict(message) for message in messages],
                "model": model,
            }
        )
        response = self._responses[len(self.calls) - 1]
        if isinstance(response, Exception):
            raise response
        return response


class TestLLMClientStructuredRetries(unittest.TestCase):
    def _make_client(
        self,
        responses: Sequence[object],
        max_retries: int = 1,
    ) -> tuple[LLMClient, StubProvider]:
        provider = StubProvider(responses=responses)
        client = LLMClient(
            provider=provider,
            models=ModelsConfig(default="stub-model"),
            max_retries=max_retries,
        )
        return client, provider

    def test_chat_structured_retries_provider_runtimeerror_without_history_pollution(
        self,
    ) -> None:
        client, provider = self._make_client(
            responses=[
                RuntimeError("temporary provider failure"),
                RuntimeError("final provider failure"),
            ],
            max_retries=1,
        )

        with self.assertRaises(RuntimeError) as ctx:
            client.chat_structured(
                messages=[{"role": "user", "content": "hello"}],
                agent_name="planner",
                response_model=StructuredReply,
            )

        self.assertEqual(str(ctx.exception), "structured llm request failed after retries")
        self.assertIsInstance(ctx.exception.__cause__, RuntimeError)
        self.assertEqual(str(ctx.exception.__cause__), "final provider failure")
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(provider.calls[0]["messages"], provider.calls[1]["messages"])

    def test_chat_structured_retries_provider_valueerror_without_history_pollution(
        self,
    ) -> None:
        client, provider = self._make_client(
            responses=[
                ValueError("temporary provider value error"),
                ValueError("final provider value error"),
            ],
            max_retries=1,
        )

        with self.assertRaises(RuntimeError) as ctx:
            client.chat_structured(
                messages=[{"role": "user", "content": "hello"}],
                agent_name="planner",
                response_model=StructuredReply,
            )

        self.assertEqual(str(ctx.exception), "structured llm request failed after retries")
        self.assertIsInstance(ctx.exception.__cause__, ValueError)
        self.assertEqual(str(ctx.exception.__cause__), "final provider value error")
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(provider.calls[0]["messages"], provider.calls[1]["messages"])

    def test_chat_structured_retries_invalid_json_with_feedback_prompt(self) -> None:
        client, provider = self._make_client(
            responses=[
                "not json",
                '{"answer": "fixed", "count": 2}',
            ],
            max_retries=1,
        )

        result = client.chat_structured(
            messages=[{"role": "user", "content": "hello"}],
            agent_name="planner",
            response_model=StructuredReply,
        )

        self.assertEqual(result.model_dump(), {"answer": "fixed", "count": 2})
        self.assertEqual(len(provider.calls), 2)

        first_messages = provider.calls[0]["messages"]
        second_messages = provider.calls[1]["messages"]

        self.assertEqual(second_messages[:-2], first_messages)
        self.assertEqual(second_messages[-2], {"role": "assistant", "content": "not json"})
        self.assertEqual(second_messages[-1]["role"], "user")
        self.assertIn("Your response was invalid.", second_messages[-1]["content"])
        self.assertIn(
            "Please respond again with valid JSON that matches the schema.",
            second_messages[-1]["content"],
        )

    def test_chat_structured_retries_schema_mismatch_with_feedback_prompt(self) -> None:
        client, provider = self._make_client(
            responses=[
                '{"answer": "missing count"}',
                '{"answer": "fixed", "count": 3}',
            ],
            max_retries=1,
        )

        result = client.chat_structured(
            messages=[{"role": "user", "content": "hello"}],
            agent_name="planner",
            response_model=StructuredReply,
        )

        self.assertEqual(result.model_dump(), {"answer": "fixed", "count": 3})
        self.assertEqual(len(provider.calls), 2)

        first_messages = provider.calls[0]["messages"]
        second_messages = provider.calls[1]["messages"]

        self.assertEqual(second_messages[:-2], first_messages)
        self.assertEqual(
            second_messages[-2],
            {"role": "assistant", "content": '{"answer": "missing count"}'},
        )
        self.assertEqual(second_messages[-1]["role"], "user")
        self.assertIn("Your response was invalid.", second_messages[-1]["content"])
        self.assertIn(
            "Please respond again with valid JSON that matches the schema.",
            second_messages[-1]["content"],
        )
