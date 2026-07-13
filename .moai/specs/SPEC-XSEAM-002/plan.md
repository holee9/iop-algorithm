---
id: SPEC-XSEAM-002
version: 0.5.1
status: planned
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
priority: medium
issue_number: 58
labels: [xseam, productization, csharp-ui, engine-contract, pythonnet, pipeline-composition]
---

# SPEC-XSEAM-002 — 구현 계획 (plan)

## 0. 구현 착수 전제

이 계획은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 마스터 plan M0.5를 상속한다. 사용자 승인 기록, 기준선 동결, `implementation_authorized=true`가 모두 존재하기 전에는 아래 마일스톤의 소스·XAML·테스트·패키지 변경을 시작하지 않는다. 내부 감사 통과나 기술적 구현 가능성만으로 이 전제를 충족했다고 보지 않는다.

진입 증거는 승인된 v0.5.1 기준선, 요구사항-인수-TC 추적 차이 0, 미결정 임계 0, 현재 worktree/commit을 가리키는 최종 감사 기록이다. 규범 변경이 발생하면 작업을 멈추고 기준선 재승인을 수행한다.

언어 중립 엔진 심의 전체 알고리즘 family + 파이프라인 조합·세션·지표 검증 UI 구현 계획. 시간 추정 없음 — Priority와 단계 순서로만 기술한다. Python 골든 모델은 동결 오라클로 무변경, 작업은 전부 기존 `apps/xdet-console/` C# 솔루션에 additive다.

## 1. 기술 접근 (Technical Approach)

### 1.1 심 조합 진입점 = `run_pipeline` 미러

- **`IXdetEngine`(durable 심) 확장**: XSEAM-001의 단일 `process`/`compute_*` 진입점에 `PipelineRunRequest → PipelineRunResult` 조합 진입점을 추가한다 — `pipeline.orchestrator.run_pipeline(frame, definition, registry, calib_map, params_map, *, panel_id, timestamp, domain)`을 미러한다. durable 심 어셈블리 `Xdet.Engine.Contract`에 위치하고 pythonnet 의존은 0이다.
- **조합 DTO**: spec의 `FrameEnvelope`, `HistoryEntryEnvelope`, `TypedValue`, `ParamsEnvelope`, `CalibSetEnvelope`, `PipelineRunRequest`, `StageFrameResult`, `PipelineRunResult`, `EngineError` 최소 계약을 그대로 구현한다. `TypedValue`는 명시된 scalar/array union이며 `Dictionary<string, object>`나 Python 객체를 Contract에 노출하지 않는다. 순서/조합 권한은 DTO가 표현만 하고 강제는 Python `PipelineDefinition.__post_init__`가 한다.
- **조합 어댑터(P1.5)**: XSEAM-001의 pythonnet in-process 어댑터가 generic `RunPipeline`을 구현 — DTO를 Python `XFrame`/`PipelineDefinition`/`CalibSet`/`Params`로 재구성 → `run_pipeline` 레지스트리를 `{stage: module.process}`로 구성(§1.4) → 실제 `pipeline.orchestrator.run_pipeline` unmodified 호출 → 결과(및 `intermediates`/history/domain/warnings)를 DTO로 역직렬화한다. `apps.gui.*` helper는 import하지 않는다. **조합·DSP 재계산 없음(트랜스포트)**.
- **P2(문서만)**: 네이티브 엔진이 동일 `RunPipeline`을 C ABI로 구현 → UI 무변경, 조합 경로도 XDET-TC-020/021 동일성 게이트 통과 필수(SPEC-XSEAM-001 FORWARD 승계).

### 1.2 다단계 조합 검증 UI (개별 → 부분집합/전체)

- **개별 스테이지(COMPOSE-1, VIEWER RUN-1 미러)**: 스테이지 1개 = `PipelineDefinition(stages=("offset",))`류. 스테이지 고유 `CalibSet`(offset=OFFSET `O_map` 등) + `Params`를 UI가 수집 → 심 경유 구동 → 입력/출력/diff/마스크 표시. `calib_kind_for_stage(stage)`로 스테이지가 요구하는 CalibKind를 UI가 안내.
- **부분집합/전체(COMPOSE-2, VIEWER RUN-2 미러)**: 정렬된 부분집합 = `("offset","gain","defect")`류; 전체 = `tuple(s for s in CANONICAL_ORDER if s != "post")`(§1.5). 각 스테이지가 자기 `CalibSet`·`Params`를 지님 → 단일 심 실행 → 조합 출력 + 스테이지별 전/후 표시.
- **중간 프레임 스크럽(COMPOSE-3)**: 입력 `XFrame.validation_mode=True`로 한 번 실행 → `result.intermediates[i]` = i번째 실행 스테이지 출력 → UI가 추가 실행 없이 각 스테이지 전/후 스크럽.
- **Correction Stack 조합 UI + 전체 해상도 캔버스**: 스테이지 다중 선택(체크/순서 표시) 패널 + 조합 실행 버튼 + 스테이지별 전/후·조합 결과를 표시하는 전체 해상도 이미지 캔버스. UI는 스테이지를 스스로 정렬·조합하지 않고 선택 집합을 심에 넘기며 순서 검증은 오케스트레이터가 한다(COMPOSE-5).

### 1.3 UI 원칙(SPEC-VIEWER-001 / XSEAM-001 상속)

- C-09 지표/DSP 자체 계산 0: UI/어댑터는 스테이지 출력·조합을 미계산, 엔진 결과만 표시.
- C-11 단방향 소비: UI→심→엔진, 역참조 없음.
- C-20 읽기-실행 전용: 골든 fixture/CalibSet/`data/` 쓰기 금지, 내보내기는 사용자 지정 디렉터리.

### 1.4 골든 계약 사실 (저작 시 AUTHORITATIVE 소스로 검증 — 구현 시 준수)

- **호출 형태**: 개별 = `PipelineDefinition(stages=("offset",))`; 부분집합 = `("offset","gain","defect")`; 전체(구동 가능) = `tuple(s for s in CANONICAL_ORDER if s != "post")`. `PipelineDefinition.full()`은 `post` 포함 전체를 반환하지만 `post`는 등록 모듈이 없어 구동 시 `CalibrationError`가 나므로 **전체 구동은 `post`를 제외한 부분수열로 한다**(예약 tail).
- **레지스트리**: `run_pipeline`에 넘기는 레지스트리는 `{stage: module.process}`(bare 콜러블, `ProcessCallable = Callable[[XFrame,CalibSet,Params],XFrame]`)여야 하며 `default_registry()`가 반환하는 `{stage: ProcessModule 객체}`가 **아니다** — `modules/registry.py` 도크스트링이 명시("does NOT replace … the per-run registry `run_pipeline` requires (stage -> process CALLABLE)"). 어댑터가 각 스테이지의 `.process`를 추출한다.
- **검증 모드 중간 프레임**: `frame.validation_mode=True` → `run_pipeline`이 각 스테이지 출력을 누적해 `replace(current, intermediates=preserved)`로 결과에 부착 → `result.intermediates[i]` = i번째 실행 스테이지 출력(단일 패스 전/후).
- **mse 상류 의존**: `mse`는 상류 노이즈 모델(α,σ) 없이 하드 실패 — `denoise` 선행 또는 α>0 사전 적재 프레임 필요. 결여 시 조합 버그가 아니라 모듈 자신의 명시 오류(MseError, SWR-803)로 표면화(어댑터는 그 오류를 그대로 전파).
- **다중 프레임 lag**: 상태형 lag(SWR-402)의 다중 프레임 정확성은 `pipeline/sequence.py::run_sequence`(시퀀스당 하나의 `LagCorrector`)로 얻으며 단일 프레임 `run_pipeline` 반복이 아니다. Lag 탭은 standalone sequence를 담당하고, generic 조합 seam의 단일-frame lag는 placeholder IRF sanity로 한정한다.
- **구동 가능 스테이지(SAMPLE 실측, QUARANTINE)**: offset(MasterDark)·gain(CalSet_19008)·defect(BPM) = 등록 실측 구동 가능(sanity, 비정본); lag = placeholder 고정 IRF; line_noise/saturation/geometry/grid/virtual_grid/denoise/mse/window = 합성 전용/#33 대기.

### 1.5 fidelity 동일성 프레임(load-bearing, XSEAM-001 상속)

- **조합(XFrame) 경로**: 부분집합/전체 조합의 심 경유 최종 XFrame을 Python 측에서 재구성 → 골든 직접 `run_pipeline` 출력과 `common.equivalence.diff_frames`(pixel/masks/noise 동일성 + `max_pixel_abs_diff` + `structurally_equal`)로 비교 → XDET-TC-021 허용오차(정수 bit-동일 / float ±1 LSB). 트랜스포트라 기대 delta = 0(값-동일); 초과 이탈 = FAIL.
- **중간 프레임 경로**: 검증 모드 `intermediates[i]`를 골든 직접 실행의 동일 스테이지 출력과 스테이지별 `diff_frames`로 비교하는 필수 fidelity 게이트로 둔다.

### 1.6 전체 알고리즘 family와 특수 합성

- catalog의 ACTION/SESSION을 FRAME_PROCESS, PIPELINE, SEQUENCE, STACK_METRIC, PROFILE_METRIC, CALIBRATION_BUILD, METRIC_SERIES, NDT_SESSION, TIER로 분류한다.
- DQE service는 MTF/NPS DTO를 검증하고 NPS support bin마다 실제 `metrics.mtf.mtf_value_at`을 호출한 뒤 실제 `metrics.dqe.compute_dqe`를 호출한다. UI/C# ViewModel은 수치 보간을 구현하지 않는다.
- tier service는 `decide_tier/select_pipeline/run_tier/time_tier`를 그대로 호출하고 rationale/variant/timing을 typed DTO로 운반한다.
- calibration service는 defect map, lag IRF, noise model, scatter 2개 builder를 실제 진입점으로 위임한다.
- session service는 Lag snapshot/restore와 NDT accumulator 상태 전이를 명시 event log로 운반한다.

## 2. 마일스톤 (우선순위 기반, 시간 추정 없음)

### M1 — 조합 심 진입점 + DTO (Priority High) — REQ-XSEAM-CONTRACT-6/7
- `Xdet.Engine.Contract`에 generic `RunPipeline`과 9개 family request/result, InputSet, availability/evidence, typed error를 추가한다(pythonnet 의존 0).
- DoD: XDET-TC-088(조합 진입점·DTO 존재 + 부분수열/게이트 강제가 오케스트레이터에 위임됨 확인).

### M2 — 조합 어댑터 (Priority High) — REQ-XSEAM-CONTRACT-6/7/8 / COMPOSE-1/2/3/6
- pythonnet 어댑터가 generic `RunPipeline` 구현: DTO↔Python 재구성, `{stage: module.process}` 레지스트리 구성, 실제 `run_pipeline` unmodified 호출, 검증 모드 `intermediates`·history/domain/warnings 역직렬화, typed `EngineError` 변환. Python GUI helper 의존을 정적 검사로 금지한다.
- DoD: XDET-TC-089(개별 스테이지), XDET-TC-090(부분집합/전체), XDET-TC-091(검증 모드 중간 프레임).

### M2A — metric/calibration/session/tier service (Priority High)
- feature family별 내부 service를 구현하고 실제 catalog EntryPoint를 호출한다. DQE fixed axis policy, tier 4함수, calibration builder 6연산, Lag/NDT state를 우선 구현한다.
- DoD: XDET-TC-155, 160~167의 Contract/integration leg.

### M3 — Correction Stack 조합 UI (Priority Medium) — REQ-XSEAM-COMPOSE-1/2/3
- WPF 조합 탭(스테이지 다중 선택 + 순서 표시 + 스테이지별 CalibSet/Params 입력) + 전체 해상도 이미지 캔버스(스테이지별 전/후 + 조합 출력). 심만 소비.
- DoD: XDET-TC-089/090/091 UI 구동(headless/smoke).

### M4 — 거부 가드 + 권한 격리 (Priority High) — REQ-XSEAM-COMPOSE-4/5
- 비-부분수열(`PipelineOrderError`)·불일치 CalibSet(`CalibrationError`) 거부·무단 대체 없음; C# 측 DSP/조합/캘리브레이션 합성 부재 + 읽기 전용.
- DoD: XDET-TC-092(거부 가드), XDET-TC-093(권한/읽기 전용 가드 + 골든 무변경).

### M5 — 조합 fidelity + 공존 검증 (Priority High, load-bearing)
- 부분집합/전체 조합 심 결과 vs 골든 직접 `run_pipeline`을 `diff_frames`로 대조(정확히 0/bit-동일 기대); Python 회귀·import-linter·골든 무변경 검증(`uv run pytest`, `uv run lint-imports`).
- DoD: XDET-TC-090/091 fidelity leg + XSEAM-001 XDET-TC-087류 무회귀 재확인.

## 3. 대상 파일 (신규/확장, 전부 `apps/xdet-console/` 하위 · 골든 무변경)

| 경로(제안) | 역할 | 요구 |
|---|---|---|
| `apps/xdet-console/src/Xdet.Engine.Contract/` | 9개 family + InputSet/availability/evidence/request/result/error DTO(durable 심, pythonnet 의존 0) | CONTRACT-6~14 |
| `apps/xdet-console/src/Xdet.Engine.PythonNet/` | 기능별 pipeline/metric/calibration/session/tier service, 실제 golden EntryPoint 호출, `apps.gui.*` 비의존 | CONTRACT-6~14, DQE/TIER/SESSION |
| `apps/xdet-console/src/Xdet.Console.App/` (실제 솔루션 WPF 프로젝트, Xdet.sln 검증) | Correction Stack 조합 UI(스테이지 다중 선택·순서) + 전체 해상도 이미지 캔버스 | COMPOSE-1/2/3 |
| `apps/xdet-console/tests/Xdet.Engine.Tests/` | xUnit 조합 테스트(`diff_frames` 재사용, 검증 모드 중간 프레임, typed error/DTO fidelity) | COMPOSE-1~6, CONTRACT-6/7/8 |

무변경(소비만): `pipeline/orchestrator.py`(`run_pipeline`·`PipelineDefinition`·`CANONICAL_ORDER`·`calib_kind_for_stage`·`_calibration_gate`·`PipelineOrderError`·`CalibrationError`) · `pipeline/sequence.py`(`run_sequence`) · `modules/registry.py`(`default_registry` 구별) · `modules/*.py`(`.process`) · `common/xframe.py`(`validation_mode`/`intermediates`) · `common/equivalence.py`(`diff_frames`) · `common/calibset.py` · `common/contract.py`. Python 코어·`apps/gui/`·import-linter 계약·`pyproject.toml` 불변. SPEC-XSEAM-001 문서 무편집.

## 4. 시험 케이스 매핑 (XDET-TC-088~093, 160~167)

| TC | 대상 | 요구 |
|---|---|---|
| XDET-TC-088 | 조합 진입점 `RunPipeline` + DTO 존재 + 부분수열/게이트 강제가 오케스트레이터 위임 | CONTRACT-6 |
| XDET-TC-089 | 개별 스테이지 심 경유 구동 + 입력/출력/diff/마스크 표시(offset/gain/defect SAMPLE sanity) | COMPOSE-1 |
| XDET-TC-090 | 부분집합/전체 단일 심 실행 + 조합 출력·스테이지별 전/후 + `diff_frames` 정확히 0 | COMPOSE-2 |
| XDET-TC-091 | 검증 모드 단일 패스 `intermediates` 반환 + 추가 실행 없이 스크럽 | COMPOSE-3 |
| XDET-TC-092 | 비-부분수열 `PipelineOrderError` + 불일치 CalibSet `CalibrationError` 거부, 무단 대체 없음 | COMPOSE-4 |
| XDET-TC-093 | C# DSP/조합/캘리브레이션 합성 부재 + 읽기 전용 + 골든 git diff 없음 | COMPOSE-5 |
| XDET-TC-160 | Python façade↔catalog↔manifest↔Contract↔GUI↔TC 전수 완결성 | COVERAGE-1/2 |
| XDET-TC-161 | family DTO와 동적 Params/CalibKind/input/output manifest | CONTRACT-9~14 |
| XDET-TC-162 | 12 stage pipeline + sequence generic seam | CONTRACT-6, COMPOSE |
| XDET-TC-163 | tier decide/select/run/time과 거부 가드 | TIER-1~4 |
| XDET-TC-164 | DQE golden-owned 합성·support filter·무외삽 | DQE-1~5 |
| XDET-TC-165 | strict IO/CalibSet/equivalence 공통 경계 | CONTRACT-10/13 |
| XDET-TC-166 | availability/evidence 분리와 user-supplied run | CONTRACT-13/14 |
| XDET-TC-167 | 모든 ACTION/SESSION GUI 도달성·mock 결과 0 | COVERAGE-2 |

TC 블록 근거: Gen 1(000~021)·VIEWER(030~037)·REALDATA(040~049)·ERGO(050~055)·CALDOM(060~067)·DQEDOC(070~073)·XSEAM-001(080~087) 범위 밖 신규 088~093(094~095 예약). C# 테스트는 `dotnet test`(xUnit)로 실행되며 Python 캡스톤 스캔(`tests/**/*.py`)과 무간섭(C# 소스는 `pyproject` `packages` 미포함·pytest 미수집).

## 5. 리스크 및 완화

| 리스크 | 완화 |
|---|---|
| 어댑터가 `default_registry()` ProcessModule 객체를 그대로 `run_pipeline`에 넘김(TypeError) | §1.4 레지스트리 사실 — `{stage: module.process}` bare 콜러블 구성; XDET-TC-088 |
| 전체 구동 시 `post` 포함으로 `CalibrationError` | `tuple(...if s != "post")` 부분수열로 전체 구동; §1.5·§1.4 |
| C#이 스테이지를 스스로 정렬·조합(제2 조합 권한) | REQ-XSEAM-COMPOSE-5 Unwanted 가드 + `PipelineDefinition.__post_init__` 부분수열 강제; XDET-TC-092/093 |
| C#이 결여 캘리브레이션을 합성(무단 대체) | REQ-XSEAM-COMPOSE-4/5 + `_calibration_gate` 거부; XDET-TC-092 |
| 구현자가 Python GUI helper를 실제 seam으로 재사용 | Contract-8 정적 금지 + adapter import 검사. 골든 `run_pipeline`/`modules.*.process`만 호출 |
| `mse` 조합 시 노이즈 모델 부재로 실패를 조합 버그로 오인 | §1.4 — MseError는 모듈 자신 오류, `denoise` 선행/α>0 프레임 필요; 어댑터는 그대로 전파 |
| SAMPLE 실측 조합을 정본 수치로 오용 | QUARANTINE(이슈 #29) — sanity(유한·비퇴화)만, 튜닝/EV 도출 금지; acceptance 라벨 |
| 조합 경로가 골든과 미묘히 다른 수치(P2 C++) | XDET-TC-020/021 동일성 프레임이 사전 설계된 게이트(XSEAM-001 FORWARD 승계) |
| DQE가 다시 영구 비활성으로 남음 | `mtf_value_at`+`compute_dqe` 실제 호출, support 밖 bin 제외, XDET-TC-155/164 |
| tier·builder·state가 탭 설명에만 있고 seam이 없음 | family별 Contract method + catalog coverage XDET-TC-160/161/163/167 |
| 등록 데이터가 없다는 이유로 algorithm control 비활성 | strict user input 허용 + availability/evidence 분리 XDET-TC-166 |

## 6. 의존성 및 순서

- SPEC-XSEAM-001의 스켈레톤 위에 M1(전체 family DTO) → M2/M2A(어댑터 service) → M3(UI)를 순차 적용한다. M4(가드)·M5(fidelity)는 M2A 후 시작한다.
- 외부: .NET 9 SDK, pythonnet(호스트 CPython = 저장소 `uv` 환경), ScottPlot, xUnit. Python 측 신규 의존 0, 골든 무변경.
