import json
from typing import Literal, Sequence, TypeVar

from pydantic import BaseModel, ValidationError
from tiny_agent_harness.providers import BaseProvider, ChatMessage
from tiny_agent_harness.schemas import ModelsConfig


AgentName = Literal["orchestrator", "executor", "reviewer"]
StructuredResponseT = TypeVar("StructuredResponseT", bound=BaseModel)

JSON_RESPONSE_INSTRUCTION = (
    "Return valid JSON only. Do not wrap it in markdown fences. "
    "The response must match this JSON schema:\n{schema}"
)


class LLMClient:
    def __init__(
        self,
        provider: BaseProvider,
        models: ModelsConfig,
        max_retries: int = 2,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be greater than or equal to 0")

        self.provider = provider
        self.models = models
        self.max_retries = max_retries

    def resolve_model(self, agent_name: AgentName, model: str | None = None) -> str:
        if isinstance(model, str) and model.strip():
            return self.provider.resolve_model(model)

        model_by_agent = {
            "orchestrator": self.models.orchestrator,
            "executor": self.models.executor,
            "reviewer": self.models.reviewer,
        }
        return self.provider.resolve_model(model_by_agent[agent_name] or self.models.default)

    def _prepare_messages(self, messages: Sequence[ChatMessage]) -> list[ChatMessage]:
        prepared_messages = [dict(message) for message in messages]
        return prepared_messages

    def _prepare_structured_messages(
        self,
        messages: Sequence[ChatMessage],
        response_model: type[BaseModel],
    ) -> list[ChatMessage]:
        prepared_messages = self._prepare_messages(messages)
        schema_json = json.dumps(response_model.model_json_schema(), indent=2, ensure_ascii=True)
        instruction = JSON_RESPONSE_INSTRUCTION.format(schema=schema_json)

        if prepared_messages and prepared_messages[0]["role"] == "system":
            prepared_messages[0] = {
                "role": "system",
                "content": f"{prepared_messages[0]['content']}\n\n{instruction}",
            }
        else:
            prepared_messages.insert(0, {"role": "system", "content": instruction})

        return prepared_messages

    def _chat_once(
        self,
        messages: Sequence[ChatMessage],
        agent_name: AgentName,
        model: str | None = None,
    ) -> str:
        resolved_model = self.resolve_model(agent_name=agent_name, model=model)
        return self.provider.chat(messages=messages, model=resolved_model)

    def chat(
        self,
        messages: Sequence[ChatMessage],
        agent_name: AgentName,
        model: str | None = None,
        max_retries: int | None = None,
    ) -> str:
        retry_limit = self.max_retries if max_retries is None else max_retries
        prepared_messages = self._prepare_messages(messages=messages)

        last_error: Exception | None = None
        for _ in range(retry_limit + 1):
            try:
                return self._chat_once(
                    messages=prepared_messages,
                    agent_name=agent_name,
                    model=model,
                )
            except Exception as exc:
                last_error = exc

        raise RuntimeError("llm request failed after retries") from last_error

    def chat_structured(
        self,
        messages: Sequence[ChatMessage],
        agent_name: AgentName,
        response_model: type[StructuredResponseT],
        model: str | None = None,
        max_retries: int | None = None,
    ) -> StructuredResponseT:
        retry_limit = self.max_retries if max_retries is None else max_retries
        prepared_messages = self._prepare_structured_messages(
            messages=messages,
            response_model=response_model,
        )

        last_error: Exception | None = None
        for _ in range(retry_limit + 1):
            try:
                response_text = self._chat_once(
                    messages=prepared_messages,
                    agent_name=agent_name,
                    model=model,
                )
                return response_model.model_validate_json(response_text)
            except (ValidationError, RuntimeError, ValueError) as exc:
                last_error = exc

        raise RuntimeError("structured llm request failed after retries") from last_error
