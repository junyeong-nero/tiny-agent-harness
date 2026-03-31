import json
from typing import Literal, Sequence, TypeVar

from pydantic import BaseModel, ValidationError
from tiny_agent_harness.channels.listener import ListenerChannel
from tiny_agent_harness.llm.providers import BaseProvider, ChatMessage
from tiny_agent_harness.schemas import ListenerEvent, ModelsConfig


AgentName = Literal[
    "supervisor",
    "planner",
    "orchestrator",
    "explorer",
    "worker",
    "reviewer",
]
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
        listeners: ListenerChannel | None = None,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be greater than or equal to 0")

        self.provider = provider
        self.models = models
        self.max_retries = max_retries
        self.listeners = listeners or ListenerChannel()

    def _emit(
        self,
        kind: str,
        agent_name: AgentName | None = None,
        message: str = "",
        data: dict | None = None,
    ) -> None:
        event = ListenerEvent(
            kind=kind,
            agent=agent_name,
            message=message,
            data=data or {},
        )
        self.listeners.call(event)

    def resolve_model(self, agent_name: AgentName, model: str | None = None) -> str:
        if isinstance(model, str) and model.strip():
            return self.provider.resolve_model(model)

        model_by_agent = {
            "supervisor": self.models.supervisor,
            "planner": self.models.planner,
            "orchestrator": self.models.orchestrator,
            "explorer": self.models.explorer,
            "worker": self.models.worker,
            "reviewer": self.models.reviewer,
        }
        return self.provider.resolve_model(
            model_by_agent[agent_name] or self.models.default
        )

    def _prepare_messages(self, messages: Sequence[ChatMessage]) -> list[ChatMessage]:
        prepared_messages = [dict(message) for message in messages]
        return prepared_messages

    def _prepare_structured_messages(
        self,
        messages: Sequence[ChatMessage],
        response_model: type[BaseModel],
    ) -> list[ChatMessage]:
        prepared_messages = self._prepare_messages(messages)
        schema_json = json.dumps(
            response_model.model_json_schema(), indent=2, ensure_ascii=True
        )
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
        self._emit(
            kind="llm_request",
            agent_name=agent_name,
            message="sending request",
            data={
                "model": resolved_model,
                "messages": [dict(message) for message in messages],
            },
        )
        try:
            response = self.provider.chat(messages=messages, model=resolved_model)
        except Exception as exc:
            self._emit(
                kind="llm_error",
                agent_name=agent_name,
                message=str(exc),
                data={"model": resolved_model},
            )
            raise

        self._emit(
            kind="llm_response",
            agent_name=agent_name,
            message="received response",
            data={"model": resolved_model, "content": response},
        )
        return response

    def chat(
        self,
        messages: Sequence[ChatMessage],
        agent_name: AgentName,
        model: str | None = None,
    ) -> str:
        retry_limit = self.max_retries
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
    ) -> StructuredResponseT:
        retry_limit = self.max_retries
        prepared_messages = self._prepare_structured_messages(
            messages=messages, response_model=response_model
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
            except (ValidationError, ValueError) as exc:
                last_error = exc
                prepared_messages = prepared_messages + [
                    {"role": "assistant", "content": response_text},
                    {
                        "role": "user",
                        "content": (
                            f"Your response was invalid. Error: {exc}\n"
                            "Please respond again with valid JSON that matches the schema."
                        ),
                    },
                ]
            except RuntimeError as exc:
                last_error = exc

        raise RuntimeError(
            "structured llm request failed after retries"
        ) from last_error
