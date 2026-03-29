import os

from tiny_agent_harness.handlers.listener import ListenerChannel
from tiny_agent_harness.llm.client import LLMClient
from tiny_agent_harness.providers import (
    BaseProvider,
    OpenAIProvider,
    OpenRouterProvider,
)
from tiny_agent_harness.schemas import AppConfig


def create_provider(config: AppConfig, api_key: str | None = None) -> BaseProvider:
    provider_name = config.provider.strip().lower()
    default_model = config.models.default

    if provider_name == "openrouter":
        return OpenRouterProvider(
            api_key=api_key,
            default_model=default_model,
        )

    if provider_name == "openai":
        return OpenAIProvider(
            api_key=api_key,
            default_model=default_model,
        )

    raise ValueError(f"unsupported provider: {config.provider}")


def create_llm_client(
    config: AppConfig,
    max_retries: int | None = None,
    listeners: ListenerChannel | None = None,
) -> LLMClient:
    provider_name = config.provider.strip().lower()
    if provider_name == "openrouter":
        resolved_api_key = os.environ.get("OPENROUTER_API_KEY")
    elif provider_name == "openai":
        resolved_api_key = os.environ.get("OPENAI_API_KEY")
    else:
        raise ValueError(f"unsupported provider: {config.provider}")
    if not resolved_api_key:
        raise ValueError(f"missing API key for provider: {config.provider}")

    provider = create_provider(config=config, api_key=resolved_api_key)
    return LLMClient(
        provider=provider,
        models=config.models,
        max_retries=config.llm.max_retries if max_retries is None else max_retries,
        listeners=listeners,
    )
