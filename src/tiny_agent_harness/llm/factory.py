from tiny_agent_harness.llm.client import LLMClient
from tiny_agent_harness.providers import BaseProvider, OpenAIProvider, OpenRouterProvider
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
    api_key: str | None = None,
    max_retries: int = 2,
) -> LLMClient:
    provider = create_provider(config=config, api_key=api_key)
    return LLMClient(
        provider=provider,
        models=config.models,
        max_retries=max_retries,
    )
