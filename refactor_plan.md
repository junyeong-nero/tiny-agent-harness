# Refactor Plan

## 1. `schemas/__init__.py` 정리 — 죽은 이름 제거

- [x] `__all__` 에서 실제 존재하지 않는 이름 제거
  - `SupervisorState`, `PlannerStep`, `RunResult`, `RunState`
  - `ReviewerStep`, `WorkerStep`, `ExecutorInput`, `ExecutorOutput`, `ExecutorStep`
  - `Subtask`, `HarnessOutput` (re-export 유효성 확인)
- [x] 실제 export 목록과 `__all__` 동기화

---

## 2. `providers/` → `llm/providers/` 이동

- [x] `src/tiny_agent_harness/llm/providers/` 디렉토리 생성
- [x] `providers/base_provider.py` → `llm/providers/base.py`
- [x] `providers/openai_provider.py` → `llm/providers/openai.py`
- [x] `providers/openrouter_provider.py` → `llm/providers/openrouter.py`
- [x] `providers/__init__.py` → `llm/providers/__init__.py`
- [x] `llm/client.py`, `llm/factory.py` import 경로 수정
- [x] 프로젝트 전체에서 `from tiny_agent_harness.providers` import 경로 수정
- [x] 기존 `providers/` 디렉토리 제거
- [x] 테스트 통과 확인

---

## 3. `agents/shared.py` → `agents/protocols.py` 이름 변경

- [x] `agents/shared.py` → `agents/protocols.py` 로 이름 변경
- [x] `agents/` 내부 모든 모듈의 import 경로 수정
  - `base_agent.py`
  - `supervisor/agent.py`
  - `planner/agent.py`
  - `worker/agent.py`
  - `reviewer/agent.py`
- [x] 테스트 통과 확인

---

## 4. `BaseAgent` → `ToolCallingAgent` 이름 변경

- [x] `agents/base_agent.py` 내 클래스명 `BaseAgent` → `ToolCallingAgent` 변경
- [x] `agents/base_agent.py` → `agents/tool_calling_agent.py` 파일명 변경
- [x] `planner/agent.py`, `worker/agent.py`, `reviewer/agent.py` import 및 상속 수정
- [x] 테스트 통과 확인

---

## 5. `channels/` 정리

> 설계 의도: `InputChannel`은 여러 기기/소스가 push하는 **공개 게이트웨이**,
> `IngressQueue`는 내부 스토리지 레이어. 이 분리는 유지한다.
> 비동기 확장 시 `IngressQueue`만 `asyncio.Queue`로 교체하면 됨.

- [x] `InputChannel`의 미사용 필드 제거
  - `message_prefix: str` — 아무 데서도 참조 안 됨
  - `_counter = count(start=1)` — 아무 데서도 참조 안 됨
- [x] `EgressQueue` 제거 — `OutputChannel`이 콜백 방식을 쓰므로 실제로 미사용
- [x] `queue.py`에서 `IngressQueue`만 남김

**비동기 확장 시 고려사항 (지금 당장은 아님):**
- `IngressQueue`의 `deque` → `asyncio.Queue` 교체
- `harness.run()` → `async def run()` 전환
- `InputChannel.dequeue()` → `async def dequeue()`

---

## 6. 함수 래퍼 제거 (클래스+함수 이중 패턴)

각 agent 모듈에 있는 아래 패턴 제거:
```python
def worker_agent(input, llm_client, tool_caller) -> WorkerOutput:
    return WorkerAgent(llm_client, tool_caller).run(input)
```

- [x] `agents/planner/agent.py` — `planner_agent()` 함수 제거, 호출부를 클래스 직접 사용으로 변경
- [x] `agents/worker/agent.py` — `worker_agent()` 함수 제거
- [x] `agents/reviewer/agent.py` — `reviewer_agent()` 함수 제거
- [x] `agents/supervisor/agent.py` — `supervisor_agent()` 함수 제거
- [x] `harness.py` 호출부 수정
- [x] 테스트 통과 확인

---

## 7. `utils.py` 제거

- [x] `truncate()` 사용처 확인
- [x] 사용처 모듈 안으로 인라인하거나 해당 모듈 내 private 함수로 이동
- [x] `utils.py` 파일 삭제
- [x] 테스트 통과 확인
