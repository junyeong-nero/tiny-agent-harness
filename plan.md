# Claude-Style Multi-Agent Refactor Checklist

## 목표

- [ ] 현재 `orchestrator -> worker -> reviewer` 구조를 Claude Code 개념에 더 가깝게 재편한다.
- [ ] 역할을 `supervisor`, `planner`, `explorer`, `worker`, `reviewer`로 분리한다.
- [ ] 첫 구현은 병렬 subagent 없이 직렬 파이프라인으로 제한한다.
- [ ] 초기 직렬 흐름을 `planner -> explorer -> planner -> worker -> reviewer`로 만든다.
- [ ] 기존 `BaseAgent`, `ToolCaller`, `Pydantic schemas`, `unittest` 기반을 최대한 재사용한다.

## 현재 상태 요약

- [ ] `agents/worker/`가 이미 존재하고 `executor` 디렉터리는 제거된 상태를 기준선으로 삼는다.
- [ ] 런타임, 설정, 스키마에 남아 있는 `orchestrator` 중심 개념을 점진적으로 정리한다.
- [ ] `schemas/config.py`의 `executor` 하위 호환 로직은 전환 기간 동안 유지한다.
- [ ] `tools/tool_caller.py`의 actor별 tool restriction 기능을 역할 분리 기반으로 계속 활용한다.
- [ ] `tests/test_runtime.py`에 남아 있는 오래된 참조를 리팩터링 과정에서 함께 정리한다.
- [ ] 이번 작업의 핵심을 "도구 시스템 신설"이 아니라 "역할/상태/런타임 분리"로 정의한다.

## 목표 아키텍처

### 에이전트 역할

- [ ] `supervisor`는 전체 세션 조율과 실행 순서 관리에 집중한다.
- [ ] `supervisor`는 planner, explorer, worker, reviewer의 실행 순서와 재시도 루프를 관리한다.
- [ ] `planner`는 사용자 요청과 이전 결과를 바탕으로 계획을 세운다.
- [ ] `planner`는 explorer subtask와 worker subtask를 구분해 생성한다.
- [ ] `planner`는 reviewer 피드백을 받아 재계획한다.
- [ ] `explorer`는 읽기 전용 도구만 사용한다.
- [ ] `explorer`는 코드 수정 없이 `findings`, `evidence`, `recommended_files`를 반환한다.
- [ ] `worker`는 실제 수정과 명령 실행만 담당한다.
- [ ] `worker`는 planner가 넘긴 구현 subtask만 수행한다.
- [ ] `reviewer`는 목표 충족 여부와 회귀 위험, 누락 검증을 확인한다.
- [ ] `reviewer`는 실패 시 planner가 재계획할 수 있도록 구체 피드백을 남긴다.

### 런타임 흐름

- [ ] 사용자 prompt 입력 시 supervisor가 전체 run state를 초기화한다.
- [ ] planner가 초기 plan을 생성한다.
- [ ] explorer subtask를 실행한다.
- [ ] planner가 exploration evidence를 반영해 worker plan으로 재계획한다.
- [ ] worker subtasks를 실행한다.
- [ ] reviewer가 결과를 검토한다.
- [ ] reviewer가 `retry`를 반환하면 planner로 피드백을 전달해 재계획한다.
- [ ] reviewer가 `approve`를 반환하면 종료한다.
- [ ] 첫 구현에서는 explorer 1개, worker 1개만 직렬로 실행해도 충분하다고 본다.

## 스키마 리팩터링

### 새로 도입할 핵심 모델

- [ ] `Subtask` 모델을 도입한다.
  필드: `id`, `kind: explore | implement | verify`, `instructions`, `context`, `allowed_tools`, `depends_on`
- [ ] `PlanStep` 모델을 도입한다.
  필드: `status: tool_call | delegate_explorer | delegate_worker | reply | complete_plan`, `summary`, `tool_call`, `subtasks`
- [ ] `ExplorerOutput` 모델을 도입한다.
  필드: `status`, `summary`, `findings`, `evidence`, `recommended_files`
- [ ] `WorkerOutput` 모델을 도입한다.
  필드: `status`, `summary`, `artifacts`, `changed_files`, `test_results`
- [ ] `ReviewerOutput` 모델을 도입한다.
  필드: `decision: approve | retry`, `feedback`, `risks`, `missing_checks`

### `RunState` 확장

- [ ] `RunState`에 `plan`을 추가한다.
- [ ] `RunState`에 `completed_subtasks`를 추가한다.
- [ ] `RunState`에 `exploration_notes`를 추가한다.
- [ ] `RunState`에 `worker_results`를 추가한다.
- [ ] `RunState`에 `review_cycles`를 추가한다.

### 하위 호환 전략

- [ ] 기존 import가 즉시 깨지지 않도록 alias를 남긴다.
- [ ] `OrchestratorStep -> PlanStep` 과도 alias를 유지한다.
- [ ] `ExecutorInput/Output/Step -> Worker*` alias를 유지한다.
- [ ] config alias도 당분간 유지한다.
- [ ] 내부 구현은 새 이름 기준으로만 확장한다.

## 디렉터리 구조

- [ ] 목표 구조를 아래와 같이 맞춘다.

```text
src/tiny_agent_harness/agents/
  supervisor/
    agent.py
    prompt.py
  planner/
    agent.py
    prompt.py
  explorer/
    agent.py
    prompt.py
  worker/
    agent.py
    prompt.py
  reviewer/
    agent.py
    prompt.py
  base_agent.py
  shared.py
```

- [ ] 전환 과정에서는 기존 `orchestrator/`를 바로 삭제하지 않는다.
- [ ] 1차에서는 `orchestrator`를 `planner` 역할에 가깝게 축소한다.
- [ ] 2차에서는 `supervisor`를 추가하고 `harness.py`에서 orchestrator 의존을 제거한다.
- [ ] 3차에서는 `orchestrator/`를 삭제하거나 deprecated wrapper로 축소한다.

## Tool 권한 매핑

- [ ] `src/tiny_agent_harness/tools/tool_caller.py`는 가능한 한 그대로 재사용한다.
- [ ] 변경 포인트는 actor 이름과 config schema로 제한한다.
- [ ] `planner` 허용 도구를 `list_files`, `search`로 제한한다.
- [ ] `explorer` 허용 도구를 `list_files`, `search`, `read_file`, `git_diff`로 제한한다.
- [ ] `worker` 허용 도구를 `bash`, `read_file`, `search`, `list_files`, `apply_patch`로 제한한다.
- [ ] `reviewer` 허용 도구를 `read_file`, `search`, `list_files`, `git_diff`로 제한한다.
- [ ] `supervisor`는 기본적으로 tool 없이 두고, 필요 시 `list_files`만 허용한다.
- [ ] planner는 읽기 전용 도구만 사용하도록 보장한다.
- [ ] explorer는 절대 쓰기 도구를 갖지 않도록 보장한다.
- [ ] reviewer도 수정 도구를 갖지 않도록 보장한다.
- [ ] worker만 `bash`와 `apply_patch`를 사용할 수 있도록 보장한다.

## Config 리팩터링

### models

- [ ] `default`
- [ ] `supervisor`
- [ ] `planner`
- [ ] `explorer`
- [ ] `worker`
- [ ] `reviewer`

### runtime

- [ ] `supervisor_max_retries`
- [ ] `planner_max_tool_steps`
- [ ] `explorer_max_tool_steps`
- [ ] `worker_max_tool_steps`
- [ ] `reviewer_max_tool_steps`

### tools

- [ ] `supervisor`
- [ ] `planner`
- [ ] `explorer`
- [ ] `worker`
- [ ] `reviewer`

### 마이그레이션 원칙

- [ ] 기존 `orchestrator` 설정은 당분간 `planner` 또는 `supervisor + planner` 기본값으로 흡수한다.
- [ ] 기존 config 파일이 깨지지 않도록 `AliasChoices`를 활용한다.
- [ ] 새 config key로 직렬 migration이 끝난 뒤에만 구식 key 제거를 검토한다.

## 단계별 구현 계획

### Phase 0. 현재 상태 정리

- [x] `tests/test_runtime.py`의 오래된 이름 참조를 정리한다.
- [x] 현재 `worker` 기준으로 테스트를 먼저 맞춘다.
- [x] `orchestrator`가 아직 planner 역할을 겸하고 있음을 명시한다.
- [x] 현재 구조를 정확히 반영하는 테스트 세트를 확보한다.

### Phase 1. Planner 도입, orchestrator 역할 축소

- [x] `agents/planner/agent.py`와 `agents/planner/prompt.py`를 추가한다.
- [x] `OrchestratorStep` 계열을 `PlanStep`, `Subtask` 중심으로 확장한다.
- [x] `RunState`에 `plan`, `review_cycles` 등을 추가한다.
- [x] 기존 orchestrator 구현을 planner wrapper 또는 deprecated adapter로 축소한다.
- [x] 이 단계에서는 `supervisor` 없이 `harness.py`가 planner를 직접 호출해도 되도록 유지한다.
- [x] planner가 worker subtask 또는 direct reply를 생성할 수 있도록 만든다.
- [x] 기존 단일-task 동작이 유지되도록 만든다.

### Phase 2. Supervisor 도입

- [ ] `agents/supervisor/agent.py`와 `agents/supervisor/prompt.py`를 추가한다.
- [ ] `harness.py`를 planner/worker/reviewer 순서를 supervisor 중심으로 재구성한다.
- [ ] `OrchestrationResult`를 supervisor 중심 결과 모델로 재설계한다.
- [ ] supervisor는 직접 tool을 쓰지 않는 방향을 기본값으로 유지한다.
- [ ] direct reply 여부는 planner가 결정하고, supervisor는 그 결정을 실행만 하도록 설계한다.
- [ ] `run_harness`가 더 이상 orchestrator에 직접 의존하지 않게 만든다.

### Phase 3. Explorer 추가

- [ ] `agents/explorer/agent.py`와 `agents/explorer/prompt.py`를 추가한다.
- [ ] `ExplorerOutput` 스키마를 추가한다.
- [ ] planner가 먼저 explorer subtask를 만들고, 그 근거를 받아 worker subtask를 다시 생성하도록 변경한다.
- [ ] `RunState.exploration_notes`와 `RunState.completed_subtasks`를 사용하기 시작한다.
- [ ] 첫 구현은 explorer 1회만 허용하는 범위로 제한한다.
- [ ] 병렬 subagent는 이 단계 범위 밖으로 둔다.
- [ ] `planner -> explorer -> planner -> worker -> reviewer` 직렬 루프가 동작하게 만든다.

### Phase 4. Reviewer 강화

- [ ] `ReviewerOutput`에 `risks`, `missing_checks`를 추가한다.
- [ ] reviewer prompt를 "원래 사용자 요청 기준 검증" 중심으로 강화한다.
- [ ] test evidence, changed files, git diff 기반 검토 흐름을 추가한다.
- [ ] retry 시 planner가 reviewer feedback을 직접 소비할 수 있게 만든다.

### Phase 5. Deprecated path 제거

- [ ] `orchestrator` 관련 alias를 축소하거나 제거한다.
- [ ] config의 구식 alias를 정리한다.
- [ ] 문서와 README를 업데이트한다.
- [ ] 외부 API와 내부 코드가 같은 개념어를 사용하도록 맞춘다.

## 파일별 구현 순서

- [ ] `src/tiny_agent_harness/schemas/agents.py`에서 새 state, subtask, output 모델을 먼저 정의한다.
- [ ] `src/tiny_agent_harness/schemas/config.py`에 planner, explorer, supervisor, reviewer, worker 설정 키를 추가한다.
- [ ] `src/tiny_agent_harness/tools/tool_caller.py`에는 필요 시 actor 이름 확장만 반영한다.
- [ ] `src/tiny_agent_harness/agents/planner/agent.py`를 구현한다.
- [ ] `src/tiny_agent_harness/agents/planner/prompt.py`를 구현한다.
- [ ] `src/tiny_agent_harness/agents/supervisor/agent.py`를 구현한다.
- [ ] `src/tiny_agent_harness/agents/supervisor/prompt.py`를 구현한다.
- [ ] `src/tiny_agent_harness/agents/explorer/agent.py`를 구현한다.
- [ ] `src/tiny_agent_harness/agents/explorer/prompt.py`를 구현한다.
- [ ] `src/tiny_agent_harness/agents/worker/agent.py`에서 `Subtask.kind=implement` 기준 입력 해석을 보강한다.
- [ ] `src/tiny_agent_harness/agents/reviewer/agent.py`를 구현한다.
- [ ] `src/tiny_agent_harness/harness.py`에 최종 직렬 루프를 연결한다.
- [ ] `src/tiny_agent_harness/agents/__init__.py`를 갱신한다.
- [ ] `config.yaml`을 갱신한다.
- [ ] `src/tiny_agent_harness/default_config.yaml`을 갱신한다.
- [ ] `tests/test_runtime.py`를 갱신한다.
- [ ] 관련 schema/config/tool tests를 추가한다.

## 테스트 계획

- [ ] planner가 direct reply를 반환하는 경우를 테스트한다.
- [ ] planner가 explorer subtask를 생성하는 경우를 테스트한다.
- [ ] explorer가 read-only tool 호출 후 findings를 반환하는 경우를 테스트한다.
- [ ] planner가 exploration evidence를 받아 worker subtask로 재계획하는 경우를 테스트한다.
- [ ] worker가 tool call 후 `changed_files`, `test_results`를 포함해 완료하는 경우를 테스트한다.
- [ ] reviewer가 `approve`를 반환하는 경우를 테스트한다.
- [ ] reviewer가 `retry`와 `missing_checks`를 반환하는 경우를 테스트한다.
- [ ] supervisor가 retry 루프를 돌며 state를 누적하는 경우를 테스트한다.
- [ ] config에서 구식 `orchestrator` 또는 `executor` key를 읽어도 새 구조로 해석되는 경우를 테스트한다.

## 리스크와 대응

### 1. 이름 변경과 동작 변경이 동시에 일어나는 문제

- [ ] rename보다 schema와 flow 분리를 먼저 진행한다.
- [ ] alias를 남겨 테스트를 단계적으로 옮긴다.

### 2. 테스트가 현재 코드와 이미 어긋나 있는 문제

- [ ] refactor 전 Phase 0에서 테스트를 먼저 현재 상태에 맞춘다.
- [ ] 이후 phase별로 테스트를 추가한다.

### 3. config 호환성 파손

- [ ] `AliasChoices` 기반 이행 기간을 유지한다.
- [ ] `default_config.yaml`과 루트 `config.yaml`을 함께 갱신한다.

### 4. explorer와 reviewer 권한 누수

- [ ] `ToolPermissionsConfig`에서 쓰기 도구를 구조적으로 배제한다.
- [ ] actor별 허용 툴 테스트를 추가한다.

## 첫 구현 범위 제안

- [ ] planner를 추가한다.
- [ ] explorer를 추가한다.
- [ ] supervisor는 얇은 순차 조율자만 구현한다.
- [ ] 병렬 subagent는 구현하지 않는다.
- [ ] 단일 explorer subtask만 지원한다.
- [ ] 단일 worker subtask만 지원한다.
- [ ] reviewer feedback 기반 1회 재시도만 지원한다.
- [ ] "계획, 탐색, 수정, 검토 분리"를 확보하면서 구현 복잡도를 통제한다.

## 완료 기준

- [ ] 코드 경로상 `planner -> explorer -> planner -> worker -> reviewer`가 실제로 실행된다.
- [ ] explorer는 쓰기 도구를 사용할 수 없다.
- [ ] worker만 수정 도구를 사용할 수 있다.
- [ ] reviewer는 승인 또는 재시도와 함께 구조화된 피드백을 남긴다.
- [ ] config는 새 actor 이름을 기본으로 사용하되, 구식 key도 일정 기간 읽을 수 있다.
- [ ] 테스트가 새 흐름을 기준으로 통과한다.

## 메모

- [ ] 현재 레포는 이미 `worker` rename이 일부 진행된 상태임을 전제로 한다.
- [ ] 출발점을 "executor를 worker로 rename"이 아니라 "orchestrator를 planner/supervisor로 분리"로 둔다.
- [ ] 실제 구현 우선순위는 rename보다 런타임 분리와 상태 모델 확장에 둔다.
