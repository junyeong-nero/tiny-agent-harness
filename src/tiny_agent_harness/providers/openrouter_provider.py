import os
from typing import Sequence

import requests

from tiny_agent_harness.providers.base_provider import BaseProvider, ChatMessage


class OpenRouterProvider(BaseProvider):
    provider_name = "openrouter"
    default_base_url = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        resolved_api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        super().__init__(api_key=resolved_api_key, default_model=default_model)
        self.base_url = base_url or self.default_base_url

    def chat(self, messages: Sequence[ChatMessage], model: str | None = None) -> str:
        response = requests.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.resolve_model(model),
                "messages": list(messages),
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        return self.normalize_response_content(
            payload["choices"][0]["message"]["content"]
        )
