import tiny_agent_harness
from tiny_agent_harness.channels import IngressQueue, ListenerChannel, OutputChannel
from tiny_agent_harness.channels.input import InputChannel
from tiny_agent_harness.harness import TinyHarness
from tiny_agent_harness.llm import LLMClient, create_llm_client, create_provider
from tiny_agent_harness.llm.providers import (
    BaseProvider,
    OpenAIProvider,
    OpenRouterProvider,
)


def test_root_package___all___lists_only_live_exports():
    assert set(tiny_agent_harness.__all__) == {
        "BaseProvider",
        "TinyHarness",
        "LLMClient",
        "IngressQueue",
        "InputChannel",
        "ListenerChannel",
        "OpenAIProvider",
        "OpenRouterProvider",
        "OutputChannel",
        "create_llm_client",
        "create_provider",
    }
    for name in tiny_agent_harness.__all__:
        assert hasattr(tiny_agent_harness, name), f"missing export: {name}"


def test_root_package_reexports_runtime_types():
    assert tiny_agent_harness.BaseProvider is BaseProvider
    assert tiny_agent_harness.TinyHarness is TinyHarness
    assert tiny_agent_harness.LLMClient is LLMClient
    assert tiny_agent_harness.IngressQueue is IngressQueue
    assert tiny_agent_harness.InputChannel is InputChannel
    assert tiny_agent_harness.ListenerChannel is ListenerChannel
    assert tiny_agent_harness.OutputChannel is OutputChannel
    assert tiny_agent_harness.OpenAIProvider is OpenAIProvider
    assert tiny_agent_harness.OpenRouterProvider is OpenRouterProvider
    assert tiny_agent_harness.create_llm_client is create_llm_client
    assert tiny_agent_harness.create_provider is create_provider
