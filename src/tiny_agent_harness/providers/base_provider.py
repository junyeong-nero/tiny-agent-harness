from abc import ABC, abstractmethod
from typing import Any, Literal, Sequence, TypedDict


class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class BaseProvider(ABC):
    provider_name: str = "base"

    def __init__(self, api_key: str, default_model: str | None = None) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("api_key must be a non-empty string")

        self.api_key = api_key.strip()
        self.default_model = default_model.strip() if default_model else None

    def resolve_model(self, model: str | None = None) -> str:
        resolved_model = model.strip() if isinstance(model, str) and model.strip() else self.default_model
        if not resolved_model:
            raise ValueError("model must be provided either explicitly or via default_model")
        return resolved_model

    def prompt(
        self,
        user_prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> str:
        messages: list[ChatMessage] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        return self.chat(messages=messages, model=model)

    @staticmethod
    def normalize_response_content(content: Any) -> str:
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    item_type = item.get("type")
                    text = item.get("text")
                else:
                    item_type = getattr(item, "type", None)
                    text = getattr(item, "text", None)

                if item_type == "text" and isinstance(text, str):
                    text_parts.append(text)

            joined_text = "".join(text_parts).strip()
            if joined_text:
                return joined_text

        raise ValueError("provider response did not contain text content")

    @abstractmethod
    def chat(self, messages: Sequence[ChatMessage], model: str | None = None) -> str:
        raise NotImplementedError
