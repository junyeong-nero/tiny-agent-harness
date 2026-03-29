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


def _resolve_api_key(provider_name: str) -> str:
    env_keys = {"openrouter": "OPENROUTER_API_KEY", "openai": "OPENAI_API_KEY"}
    env_var = env_keys.get(provider_name)
    if env_var is None:
        raise ValueError(f"unsupported provider: {provider_name}")
    api_key = os.environ.get(env_var)
    if not api_key:
        raise ValueError(f"missing API key: {env_var} is not set")
    return api_key


def create_llm_client(
    config: AppConfig,
    max_retries: int | None = None,
    listeners: ListenerChannel | None = None,
) -> LLMClient:
    provider_name = config.provider.strip().lower()
    api_key = _resolve_api_key(provider_name)
    provider = create_provider(config=config, api_key=api_key)
    return LLMClient(
        provider=provider,
        models=config.models,
        max_retries=config.llm.max_retries if max_retries is None else max_retries,
        listeners=listeners,
    )
