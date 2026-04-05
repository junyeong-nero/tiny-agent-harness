import json
from typing import Any, Literal, Sequence, TypeVar, get_args, get_origin

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
    "verifier",
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
        max_retries: int = 10,
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
            "verifier": self.models.verifier,
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

    def _validate_structured_response(
        self,
        response_text: str,
        response_model: type[StructuredResponseT],
    ) -> StructuredResponseT:
        response_payload = json.loads(response_text)
        response_payload = self._normalize_nested_model_fields(
            response_payload=response_payload,
            response_model=response_model,
        )
        return response_model.model_validate(response_payload)

    def _normalize_nested_model_fields(
        self,
        response_payload: Any,
        response_model: type[BaseModel],
    ) -> Any:
        if not isinstance(response_payload, dict):
            return response_payload

        normalized_payload = dict(response_payload)
        for field_name, field_info in response_model.model_fields.items():
            if field_name not in normalized_payload:
                continue

            normalized_payload[field_name] = self._normalize_value_for_annotation(
                value=normalized_payload[field_name],
                annotation=field_info.annotation,
            )

        return normalized_payload

    def _normalize_value_for_annotation(self, value: Any, annotation: Any) -> Any:
        nested_model = self._resolve_model_annotation(annotation)
        if nested_model is not None:
            return self._normalize_model_value(value=value, model_type=nested_model)

        origin = get_origin(annotation)
        if origin is list and isinstance(value, list):
            item_annotation = get_args(annotation)[0] if get_args(annotation) else Any
            return [
                self._normalize_value_for_annotation(item, item_annotation)
                for item in value
            ]

        if origin is dict and isinstance(value, dict):
            args = get_args(annotation)
            value_annotation = args[1] if len(args) == 2 else Any
            return {
                key: self._normalize_value_for_annotation(item, value_annotation)
                for key, item in value.items()
            }

        return value

    def _normalize_model_value(
        self,
        value: Any,
        model_type: type[BaseModel],
    ) -> Any:
        if not isinstance(value, dict):
            return value

        normalized_value: dict[str, Any] = {}
        for field_name, field_info in model_type.model_fields.items():
            if field_name not in value:
                continue

            normalized_value[field_name] = self._normalize_value_for_annotation(
                value=value[field_name],
                annotation=field_info.annotation,
            )

        return normalized_value

    def _resolve_model_annotation(self, annotation: Any) -> type[BaseModel] | None:
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return annotation

        for candidate in get_args(annotation):
            if isinstance(candidate, type) and issubclass(candidate, BaseModel):
                return candidate

        return None

    def _append_validation_retry_messages(
        self,
        messages: Sequence[ChatMessage],
        response_text: str,
        error: Exception,
    ) -> list[ChatMessage]:
        return list(messages) + [
            {"role": "assistant", "content": response_text},
            {
                "role": "user",
                "content": (
                    f"Your response was invalid. Error: {error}\n"
                    "Please respond again with valid JSON that matches the schema."
                ),
            },
        ]

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
            except Exception as exc:
                last_error = exc
                continue

            try:
                return self._validate_structured_response(
                    response_text=response_text,
                    response_model=response_model,
                )
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                prepared_messages = self._append_validation_retry_messages(
                    messages=prepared_messages,
                    response_text=response_text,
                    error=exc,
                )

        raise RuntimeError(
            "structured llm request failed after retries"
        ) from last_error
