# Runtime Stabilization Checklist

목표: 아래 4개 항목을 이 순서대로 정리한다. 앞 단계에서 런타임 실패를 줄이고, 마지막 단계에서 실제 harness 경로를 통합 테스트로 고정한다.

## 1. LLMClient 예외 처리

- [x] `chat_structured()`에서 `response_text`가 할당되기 전에 참조되는 경로를 제거한다.
- [x] provider 호출 실패와 JSON/schema validation 실패를 같은 예외 경로로 처리하지 않도록 분리한다.
- [x] provider 실패 시에는 메시지 히스토리를 오염시키지 않고 재시도한다.
- [x] JSON/schema validation 실패 시에만 assistant 응답과 교정 프롬프트를 히스토리에 추가한다.
- [x] 재시도 소진 후에는 원인을 보존한 예외를 일관되게 반환한다.
- [x] 테스트 추가: provider `RuntimeError`.
- [x] 테스트 추가: provider `ValueError`.
- [x] 테스트 추가: invalid JSON 후 재시도 성공.
- [x] 테스트 추가: schema mismatch 후 재시도 성공.

완료 기준:
- [x] provider 실패가 `UnboundLocalError`로 바뀌지 않는다.
- [x] `max_retries`가 provider 실패와 validation 실패 모두에서 의도대로 동작한다.

## 2. Recoverable Tool Failure

- [x] disallowed tool call을 예외 대신 `ToolResult(ok=False)`로 반환하도록 정리한다.
- [x] unknown tool call도 예외 대신 `ToolResult(ok=False)`로 반환하도록 정리한다.
- [x] tool argument validation 실패는 recoverable한 `ToolResult` 경로로 통일한다.
- [x] `ToolCallingAgent`가 failed tool result를 대화 히스토리에 넣고 다음 응답을 계속 받도록 유지한다.
- [x] tool 실행 중 발생한 실제 예외를 listener 이벤트와 `ToolResult.error`에 일관되게 남기도록 정리한다.
- [x] 테스트 추가: unknown tool.
- [x] 테스트 추가: disallowed tool.
- [x] 테스트 추가: invalid tool arguments.
- [x] 테스트 추가: 첫 tool call 실패 후 두 번째 응답에서 수정된 tool call로 회복.

완료 기준:
- [x] 잘못된 `tool_call` 한 번으로 run 전체가 예외 종료되지 않는다.
- [x] 모델이 tool failure를 보고 스스로 다음 행동을 수정할 수 있다.

## 3. Step-Limit 실패 Semantics

- [x] `max_tool_steps`를 넘겼는데도 `tool_call`이 남아 있는 상태를 명시적 실패로 취급한다.
- [x] 실패 표현은 스키마 기반 `status="failed"` 결과로 통일한다.
- [x] planner, explorer, worker, verifier 전부 같은 규칙을 사용하도록 공통화한다.
- [x] supervisor가 subagent step-limit 실패를 받았을 때 즉시 최종 실패로 정리한다.
- [x] listener 이벤트와 최종 summary에서 "미완료인데 성공처럼 보이는" 상태를 제거한다.
- [x] 테스트 추가: planner step-limit 초과.
- [x] 테스트 추가: worker step-limit 초과.
- [x] 테스트 추가: verifier step-limit 초과.
- [x] 테스트 추가: supervisor가 미완료 subagent 결과를 최종 성공으로 오인하지 않음.

완료 기준:
- [x] `tool_call`이 남은 결과가 `completed`처럼 소비되지 않는다.
- [x] step-limit 초과가 사용자와 테스트 모두에게 명확한 실패로 보인다.

## 4. 실제 Harness 통합 테스트

- [x] `tests/conftest.py`에서 `tiny_agent_harness.harness` 전체 mock을 제거하거나 최소 범위로 축소한다.
- [x] `TinyHarness._run()` happy path 통합 테스트를 추가한다.
- [x] `TinyHarness.run()`이 input queue에서 request를 꺼내 output event를 내보내는 경로를 검증한다.
- [x] skill resolution 성공 경로를 검증한다.
- [x] unknown skill 실패 경로와 `run_failed` listener event를 검증한다.
- [x] supervisor 실패가 output response와 listener event에 반영되는지 검증한다.
- [x] malformed tool call 또는 subagent 예외가 recoverable 정책과 맞물려 어떻게 보이는지 검증한다.
- [x] 패키지 공개 API import 테스트를 추가해 dead export를 막는다.
- [x] 필요하면 CLI one-shot smoke test를 추가해 실제 진입점까지 점검한다.

완료 기준:
- [x] harness 핵심 경로가 unit test mock 없이 실제 객체 조합으로 검증된다.
- [x] 패키지 import/export 문제와 런타임 이벤트 흐름 문제가 테스트에서 바로 드러난다.

## 마무리 체크

- [x] `PYTHONPATH=src uv run pytest` 전체 통과.
- [x] 변경된 실패 semantics를 README 또는 개발자 문서에 반영.
- [x] follow-up 후보 정리: config의 runtime step-limit 외부화, CLI explorer 노출, dead export 정리.

후속 후보 메모:
- config에 supervisor/subagent step limit을 노출해서 현재 하드코딩된 `3`/`10` 값을 제거한다.
- CLI의 help/status/agent 설명에서 explorer를 planner/worker/verifier와 같은 수준으로 드러낸다.
- 공개 export surface를 다시 점검하고, import 테스트로 막고 있는 dead export/alias를 정리한다.
