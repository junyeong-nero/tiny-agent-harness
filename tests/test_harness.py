from typing import Any, Callable, Sequence

import tiny_agent_harness.harness as harness_module
from tiny_agent_harness.cli import main
from tiny_agent_harness.harness import TinyHarness
from tiny_agent_harness.llm.client import LLMClient
from tiny_agent_harness.llm.providers import BaseProvider, ChatMessage
from tiny_agent_harness.schemas import (
    Config,
    HarnessInput,
    LLMConfig,
    ListenerEvent,
    ModelsConfig,
    SubAgentCall,
    SupervisorOutput,
    ToolInput,
    ToolPermissionsConfig,
    WorkerOutput,
)


ProviderResponse = (
    str
    | Exception
    | Callable[[Sequence[ChatMessage], str | None], str]
)


class ScriptedProvider(BaseProvider):
    provider_name = "scripted"

    def __init__(self, responses: Sequence[ProviderResponse]) -> None:
        super().__init__(api_key="test-key", default_model="test-model")
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def chat(
        self,
        messages: Sequence[ChatMessage],
        model: str | None = None,
    ) -> str:
        self.calls.append(
            {
                "messages": [dict(message) for message in messages],
                "model": model,
            }
        )
        if not self._responses:
            raise AssertionError("unexpected provider call")

        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if callable(response):
            return response(messages, model)
        return response


def _config() -> Config:
    return Config(
        provider="openai",
        models=ModelsConfig(default="test-model"),
        llm=LLMConfig(max_retries=0),
        tools=ToolPermissionsConfig(),
    )


def _patch_llm_client(
    monkeypatch,
    provider: ScriptedProvider,
) -> None:
    def _create_llm_client(config: Config, listeners=None) -> LLMClient:
        return LLMClient(
            provider=provider,
            models=config.models,
            max_retries=config.llm.max_retries,
            listeners=listeners,
        )

    monkeypatch.setattr(harness_module, "create_llm_client", _create_llm_client)


def _build_harness(monkeypatch, tmp_path, provider: ScriptedProvider) -> TinyHarness:
    _patch_llm_client(monkeypatch, provider)
    return TinyHarness(config=_config(), workspace_root=str(tmp_path))


def _attach_collectors(
    harness: TinyHarness,
) -> tuple[list[ListenerEvent], list[Any]]:
    listener_events: list[ListenerEvent] = []
    output_events: list[Any] = []
    harness.ch_listener.add_channel(
        "test-listener",
        lambda _, event: listener_events.append(event),
    )
    harness.ch_output.add_channel(
        "test-output",
        lambda _, event: output_events.append(event),
    )
    return listener_events, output_events


def _listener_kinds(events: Sequence[ListenerEvent]) -> list[str]:
    return [event.kind for event in events]


def test__run_happy_path_integration(monkeypatch, tmp_path):
    provider = ScriptedProvider(
        [
            SupervisorOutput(
                task="say hello",
                status="completed",
                summary="hello from harness",
            ).model_dump_json()
        ]
    )
    harness = _build_harness(monkeypatch, tmp_path, provider)
    listener_events, _ = _attach_collectors(harness)

    result = harness._run(HarnessInput(task="say hello", session_id="session-1"))

    assert result.task == "say hello"
    assert result.session_id == "session-1"
    assert result.summary == "hello from harness"
    assert _listener_kinds(listener_events) == [
        "run_started",
        "llm_request",
        "llm_response",
        "run_completed",
    ]
    assert listener_events[-1].data == {
        "status": "completed",
        "summary": "hello from harness",
    }


def test_run_dequeues_request_and_emits_output_event(monkeypatch, tmp_path):
    provider = ScriptedProvider(
        [
            SupervisorOutput(
                task="queued task",
                status="completed",
                summary="processed from queue",
            ).model_dump_json()
        ]
    )
    harness = _build_harness(monkeypatch, tmp_path, provider)
    _, output_events = _attach_collectors(harness)
    harness.ch_input.queue("queued task", session_id="session-queue")

    harness.run()

    assert harness.ch_input.is_empty() is True
    assert len(output_events) == 1
    output_event = output_events[0]
    assert output_event.session_id == "session-queue"
    assert output_event.payload.query == "queued task"
    assert output_event.payload.summary == "processed from queue"
    assert output_event.payload.done is True


def test_run_resolves_skill_successfully(monkeypatch, tmp_path):
    def _assert_resolved_prompt(
        messages: Sequence[ChatMessage],
        _: str | None,
    ) -> str:
        assert messages[1]["content"].startswith("task: Split changes into logical commits.")
        assert "Additional instructions: group by feature" in messages[1]["content"]
        return SupervisorOutput(
            task="resolved commit task",
            status="completed",
            summary="commit workflow ready",
        ).model_dump_json()

    provider = ScriptedProvider([_assert_resolved_prompt])
    harness = _build_harness(monkeypatch, tmp_path, provider)
    listener_events, _ = _attach_collectors(harness)

    result = harness._run(
        HarnessInput(task="/commit group by feature", session_id="session-skill")
    )

    assert result.summary == "commit workflow ready"
    assert _listener_kinds(listener_events) == [
        "run_started",
        "skill_resolved",
        "llm_request",
        "llm_response",
        "run_completed",
    ]
    skill_event = listener_events[1]
    assert skill_event.data["skill"] == "commit"
    assert skill_event.data["args"] == "group by feature"
    assert "Split changes into logical commits." in skill_event.data["prompt"]


def test_unknown_skill_emits_run_failed_and_empty_output(monkeypatch, tmp_path):
    provider = ScriptedProvider([])
    harness = _build_harness(monkeypatch, tmp_path, provider)
    listener_events, output_events = _attach_collectors(harness)
    harness.ch_input.queue("/missing do something", session_id="session-missing")

    harness.run()

    assert provider.calls == []
    assert len(output_events) == 1
    assert output_events[0].payload.summary == ""
    assert _listener_kinds(listener_events) == [
        "run_started",
        "skill_error",
        "run_failed",
    ]
    assert listener_events[1].message == "unknown skill: missing"
    assert listener_events[2].message == "skill resolution failed"


def test_supervisor_failure_is_reflected_in_response_and_listener_events(
    monkeypatch,
    tmp_path,
):
    provider = ScriptedProvider(
        [
            SupervisorOutput(
                task="blocked task",
                status="failed",
                summary="cannot complete requested change",
            ).model_dump_json()
        ]
    )
    harness = _build_harness(monkeypatch, tmp_path, provider)
    listener_events, output_events = _attach_collectors(harness)
    harness.ch_input.queue("blocked task", session_id="session-failed")

    harness.run()

    assert len(output_events) == 1
    assert output_events[0].payload.summary == "cannot complete requested change"
    assert _listener_kinds(listener_events) == [
        "run_started",
        "llm_request",
        "llm_response",
        "run_failed",
    ]
    assert listener_events[-1].data == {
        "status": "failed",
        "summary": "cannot complete requested change",
    }


def test_malformed_tool_call_is_recoverable_in_harness_run(
    monkeypatch,
    tmp_path,
):
    provider = ScriptedProvider(
        [
            SupervisorOutput(
                task="repair flow",
                status="subagent_call",
                subagent_call=SubAgentCall(agent="worker", task="inspect target file"),
                summary="delegate to worker",
            ).model_dump_json(),
            WorkerOutput(
                task="inspect target file",
                status="completed",
                summary="attempt invalid read",
                tool_call=ToolInput(tool="read_file", arguments={}),
            ).model_dump_json(),
            WorkerOutput(
                task="inspect target file",
                status="completed",
                summary="recovered after tool failure",
            ).model_dump_json(),
            SupervisorOutput(
                task="repair flow",
                status="completed",
                summary="worker recovered from malformed tool call",
            ).model_dump_json(),
        ]
    )
    harness = _build_harness(monkeypatch, tmp_path, provider)
    listener_events, output_events = _attach_collectors(harness)
    harness.ch_input.queue("repair flow", session_id="session-recoverable")

    harness.run()

    assert len(provider.calls) == 4
    assert len(output_events) == 1
    assert output_events[0].payload.summary == "worker recovered from malformed tool call"

    tool_finished = next(
        event for event in listener_events if event.kind == "tool_call_finished"
    )
    assert tool_finished.data["tool"] == "read_file"
    assert tool_finished.data["ok"] is False
    assert "ValidationError" in tool_finished.data["error"]
    assert "path" in tool_finished.data["error"]

    retry_messages = provider.calls[2]["messages"]
    assert retry_messages[-1]["role"] == "user"
    assert "tool=read_file" in retry_messages[-1]["content"]
    assert "ok=False" in retry_messages[-1]["content"]
    assert listener_events[-1].kind == "run_completed"


def test_cli_one_shot_smoke_runs_real_harness_entrypoint(
    monkeypatch,
    tmp_path,
    capsys,
):
    provider = ScriptedProvider(
        [
            SupervisorOutput(
                task="cli smoke",
                status="completed",
                summary="cli smoke ok",
            ).model_dump_json()
        ]
    )
    _patch_llm_client(monkeypatch, provider)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "provider: openai\n"
        "models:\n"
        "  default: test-model\n"
        "llm:\n"
        "  max_retries: 0\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--config",
            str(config_path),
            "--workspace",
            str(tmp_path),
            "hello",
            "from",
            "cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "cli smoke ok" in captured.out
