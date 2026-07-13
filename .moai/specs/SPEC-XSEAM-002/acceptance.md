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

# SPEC-XSEAM-002 — 인수 기준 (acceptance)

> 본 인수기준의 모든 EARS ID·중앙 TC·필수 증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다. `baseline-control.md`의 G0와 사용자 승인 전에는 이 체크리스트를 구현 완료 증거로 사용할 수 없으며 모든 TC는 `PLANNED` 상태를 유지한다.

다단계 조합 검증(개별 스테이지 → 부분집합/전체 조합 → 검증 모드 중간 프레임 + 거부·권한 가드)의 Given-When-Then. 모든 기준은 관측 가능(빌드 성공 / 심 조합 구동 / `diff_frames` delta 정확히 0 — 트랜스포트, ±1 LSB는 P2 예약 / 오케스트레이터 명시 오류로 거부 / 골든 파일 무변경)해야 한다. 각 시나리오는 XDET-TC-088~093에 귀속한다. 실측(SAMPLE·에드로지) 구동은 **QUARANTINE(이슈 #29)** — sanity(유한·비퇴화·구조 성립)만 단언하고 수치 골든 주장은 하지 않는다.

## Scenarios (Given-When-Then)

### Scenario 1 — 조합 심 진입점 + DTO (XDET-TC-088, REQ-XSEAM-CONTRACT-6/7/8)
- **Given** SPEC-XSEAM-001의 `apps/xdet-console/` 솔루션과 `Xdet.Engine.Contract`가 있고,
- **When** `dotnet build`로 계약 어셈블리를 빌드하면,
- **Then** `IXdetEngine`에 `PipelineRunRequest → PipelineRunResult` generic 진입점이 존재하고, spec의 `FrameEnvelope`·`HistoryEntryEnvelope`·`TypedValue`·`ParamsEnvelope`·`CalibSetEnvelope`·`StageFrameResult`·`EngineError` 필수 필드가 정의되며, Contract 공개면에 `dynamic`/`PyObject`/`object` payload가 없어야 한다. 부분수열/게이트 강제 로직은 C# 측에 없고 계약 어셈블리의 pythonnet 의존은 0이어야 한다. adapter 정적 의존 검사에서 `apps.gui.module_panel`·`apps.gui.pipeline_panel` import가 0이어야 한다.

### Scenario 2 — 개별 스테이지 검증 (XDET-TC-089, REQ-XSEAM-COMPOSE-1) — VIEWER RUN-1 미러
- **Given** 조합 어댑터와 임베드 CPython(저장소 `uv` 환경)이 있고, 단일 스테이지 `offset`와 그 고유 입력(등록 SAMPLE `MasterDark`→CalibSet(OFFSET) `O_map` + Params `raw_saturation_threshold`)이 주어지면,
- **When** 사용자가 그 스테이지 하나를 선택하고 심 조합 진입점을 `PipelineDefinition(stages=("offset",))`으로 호출하면,
- **Then** 어댑터가 `{"offset": offset.process}` 레지스트리로 실제 `run_pipeline`을 unmodified 호출하고, UI가 그 스테이지의 입력/출력/diff/마스크 결과를 표시하며(모든 수치는 골든 산출, C-09), 출력 XFrame 통계가 유한·비퇴화(SAMPLE sanity)여야 한다. (gain=`CalSet_19008`→GAIN `G_map`, defect=`BPM`→DEFECT `class_map`도 동일 방식으로 개별 구동 가능; lag는 placeholder 고정 IRF sanity; 그 외 스테이지는 합성 입력 또는 #33 대기.)

### Scenario 3 — 부분집합/전체 조합 검증 (XDET-TC-090, REQ-XSEAM-COMPOSE-2) — VIEWER RUN-2 미러 — **load-bearing**
- **Given** 개별로 확인된 스테이지들이 각자 고유 `CalibSet`·`Params`를 지니고(등록 SAMPLE 부분집합 예: `("offset","gain","defect")` — 셋 다 등록 실측 구동 가능),
- **When** 사용자가 그 정렬된 부분집합(또는 전체 = `tuple(s for s in CANONICAL_ORDER if s != "post")`)을 선택해 단일 심 파이프라인 실행을 요청하면,
- **Then** 심이 그 부분수열에 대해 `run_pipeline`을 한 번 구동해 조합 출력과 각 스테이지의 전/후를 표시하고, 그 조합 최종 XFrame을 Python 골든 직접 `run_pipeline` 출력과 `common.equivalence.diff_frames`로 비교했을 때 `structurally_equal`가 True이고 `max_pixel_abs_diff`가 XDET-TC-021 허용오차 이내(트랜스포트이므로 정확히 0/bit-동일 기대)여야 한다.

### Scenario 4 — 검증 모드 중간 프레임 스크럽 (XDET-TC-091, REQ-XSEAM-COMPOSE-3)
- **Given** 입력 XFrame이 `validation_mode=True`이고 조합 부분집합(또는 전체)이 선택된 상태에서,
- **When** 그 조합을 심 경유로 **한 번** 실행하면,
- **Then** 심이 그 단일 패스에서 실행된 모든 스테이지의 중간 프레임을 `XFrame.intermediates`로 반환하고(`intermediates[i]` = i번째 실행 스테이지 출력), UI가 추가 심 실행을 발행하지 않고 각 스테이지의 전/후를 스크럽할 수 있어야 한다. (선택적: 각 `intermediates[i]`를 골든 직접 실행의 동일 스테이지 출력과 스테이지별 `diff_frames`로 대조 시 정확히 0 delta.)

### Scenario 5 — 부분수열·캘리브레이션 거부 가드 (XDET-TC-092, REQ-XSEAM-COMPOSE-4)
- **Given** 조합 진입점이 임의 스테이지 집합·CalibSet 맵을 받고,
- **When** (a) `CANONICAL_ORDER` 부분수열이 아닌 집합(예: `("gain","offset")` 역순)을 요청하거나, (b) 선택 스테이지 중 하나의 CalibSet이 부재하거나 해상도·panel_id가 불일치하도록 요청하면,
- **Then** (a)는 `PipelineDefinition.__post_init__`의 `PipelineOrderError`로, (b)는 `_calibration_gate`의 `CalibrationError`로 프레임 처리 이전에 거부되고, 어떤 기본 캘리브레이션도 대체되지 않아야 한다(SWR-000-2/-5). 두 오류는 `EngineError.Code/Type/Stage/Context`에 구별되어 보존되고 부분 출력은 성공 결과로 커밋되지 않아야 한다.

### Scenario 6 — C# 권한/읽기 전용 가드 (XDET-TC-093, REQ-XSEAM-COMPOSE-5)
- **Given** 어댑터·UI가 조합을 구동하고,
- **When** 심 경유 실행 후 C# 측 코드 경로와 의존 방향·쓰기 대상을 검사하면,
- **Then** (i) 모든 스테이지 출력·조합이 실제 Python 골든(`run_pipeline`·`modules.*.process`)에서 발생하고 C# 측에 어떤 DSP 산술·스테이지 정렬/조합 로직·캘리브레이션 합성도 없어야 하며(조합 권한은 오케스트레이터, DSP는 골든 — C-09/C-11), (ii) 어댑터가 `apps.gui.*` helper를 import/호출하지 않아야 하고, (iii) 어떤 UI 동작도 골든 fixture·CalibSet·`data/`에 쓰지 않으며(C-20; 내보내기는 사용자 지정 디렉터리), (iv) `common/`·`modules/`·`metrics/`·`pipeline/` 하위 파일이 무변경(git diff 없음)이어야 한다.

### Scenario 7 — DQE 골든 소유 합성

- **Given** 호환되는 MTF/NPS MetricSeriesEnvelope의 자연 주파수축이 서로 다르고,
- **When** `DqeComposeRequest`를 실행하면,
- **Then** engine은 MTF support 안의 NPS bin만 선택해 각 bin마다 골든 `mtf_value_at`을 호출한 후 `compute_dqe`를 호출하고, 선택/제외 bin·두 upstream hash·두 EntryPoint를 결과에 기록해야 한다. support 밖 endpoint clamp·외삽과 UI 보간은 0건이어야 한다.

### Scenario 8 — tier 전체 경로

- **Given** capability, injected tier policy, tier variants가 있고,
- **When** decide/select/run/time 모드를 각각 호출하면,
- **Then** 실제 `pipeline.tier` 4개 진입점의 typed 결과가 반환되고 forced upgrade·missing variant·missing policy가 명시 거부되며 timing 결과로 절대 성능 합격 판정을 만들지 않아야 한다.

### Scenario 9 — calibration/session family

- **Given** defect/IRF/noise/scatter builder 입력과 Lag/NDT session 입력이 있을 때,
- **When** 각 ACTION/SESSION을 실행하면,
- **Then** 실제 builder/state EntryPoint가 호출되고 populated CalibSet 또는 ordered state/event DTO가 반환되며, 암묵 state 재사용과 rejected-shot mutation이 없어야 한다.

### Scenario 10 — catalog 전수 완결성

- **Given** Python 공개 façade, algorithm catalog, manifest, Contract, GUI action registry, 중앙 TC가 있을 때,
- **When** 집합을 비교하면,
- **Then** 미분류 공개 대상·중복 FeatureId·DTO 없는 ACTION/SESSION·orphan GUI control·TC 없는 기능이 모두 0건이어야 한다.

## 요구사항-시나리오 추적

| 요구사항 | 시나리오 / 중앙 TC |
|---|---|
| `REQ-XSEAM-CONTRACT-{6..14}` | 1, 9, 10 / 161, 166 |
| `REQ-XSEAM-COMPOSE-{1..6}` | 2~6 / 162 |
| `REQ-XSEAM-DQE-{1..5}` | 7 / 164 |
| `REQ-XSEAM-TIER-{1..4}` | 8 / 163 |
| `REQ-XSEAM-SESSION-{1..3}` | 9 / 104~111, 144~151 |
| `REQ-XSEAM-COVERAGE-{1..2}` | 10 / 160, 161, 167 |

상세 증거 필드는 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다. 범위 안의 모든 개별 ID가 전개되지 않으면 인수 실패다.

## Edge Cases

- **비-부분수열 조합은 FAIL (REQ-XSEAM-COMPOSE-4)** — 역순·미지 스테이지·중복 스테이지 집합을 조합 진입점에 넘기면 `PipelineOrderError`로 거부돼야 한다 — 통과로 침묵되면 안 된다(음성 대조: 역순 `("gain","offset")` 주입 시 실제로 예외 발생 확인).
- **결여/불일치 캘리브레이션은 FAIL·무단 대체 없음 (REQ-XSEAM-COMPOSE-4)** — 선택 스테이지의 CalibSet이 없거나 해상도/panel_id 불일치이면 `CalibrationError`로 프레임 처리 전에 거부되고 기본값이 대체되면 안 된다(SWR-000-5; 음성 대조: 특정 스테이지 CalibSet 제거 시 실제로 거부 확인).
- **`mse` 조합의 상류 노이즈 모델 부재 (plan §1.4)** — `denoise` 없이 `mse`를 조합에 포함하고 α>0 프레임도 아니면, 이는 조합 버그가 아니라 모듈 자신의 명시 오류(MseError, SWR-803)로 표면화하며 어댑터가 그대로 전파해야 한다(조합 로직이 삼켜서는 안 됨).
- **조합 fidelity 불일치는 FAIL (REQ-XSEAM-COMPOSE-2)** — 심 경유 조합 최종 XFrame이 골든 직접 `run_pipeline` 출력으로부터 XDET-TC-021 허용오차를 초과 이탈하면(예: 스테이지 간 마샬링이 float32를 승격/절단) fidelity 시험이 반드시 FAIL 해야 한다 — 통과로 침묵되면 안 된다(음성 신뢰성: 조합 중간 버퍼에 1 LSB 초과 섭동 주입 시 실제 FAIL 확인; XSEAM-001 offset 섭동 시험의 조합 경로 미러).
- **C# 조합·DSP 재구현 (REQ-XSEAM-COMPOSE-5)** — C# 측이 스테이지를 스스로 정렬/조합하거나 스테이지 출력을 스스로 계산하거나 결여 캘리브레이션을 합성하면 인수 실패 — 조합은 `PipelineDefinition`(오케스트레이터), 모든 DSP는 골든이 산출해야 한다.
- **SAMPLE 실측 조합의 수치 오용 (QUARANTINE, 이슈 #29)** — 등록 SAMPLE(에드로지) 조합 구동 결과를 정본 수치/EV 임계 도출·튜닝·적합에 사용하면 인수 실패 — sanity(유한·비퇴화·구조)만 허용, 정본 수치 조합 검증은 정본 지침세트(#33) 도착 후 별건.

## Definition of Done (체크리스트)

- [ ] `IXdetEngine`에 9개 family request/result와 InputSet/availability/evidence/error DTO 정의(pythonnet 의존 0, dynamic/PyObject/object payload 0) (XDET-TC-088/161, CONTRACT-6~14)
- [ ] 어댑터가 `{stage: module.process}` 레지스트리를 구성해 실제 `run_pipeline` unmodified 호출(`default_registry()` 객체 직접 전달 아님) (XDET-TC-089/090, CONTRACT-6)
- [ ] 어댑터의 `apps.gui.module_panel`/`pipeline_panel` 의존 0, Python GUI helper는 대조 선례로만 존재 (XDET-TC-088/093, CONTRACT-8)
- [ ] 개별 스테이지(offset/gain/defect SAMPLE sanity) 심 경유 구동 + 입력/출력/diff/마스크 표시(수치는 골든 산출) (XDET-TC-089, COMPOSE-1)
- [ ] 정렬된 부분집합/전체(`post` 제외) 단일 심 실행 + 조합 출력·스테이지별 전/후 표시 (XDET-TC-090, COMPOSE-2)
- [ ] 조합 fidelity: 심 조합 최종 XFrame vs 골든 직접 `run_pipeline`을 `diff_frames`로 `structurally_equal` True + `max_pixel_abs_diff` 정확히 0(±1 LSB는 P2 예약) (XDET-TC-090, COMPOSE-2)
- [ ] 검증 모드 단일 패스 `intermediates` 반환 + 추가 실행 없이 스테이지별 전/후 스크럽 (XDET-TC-091, COMPOSE-3)
- [ ] 비-부분수열 `PipelineOrderError` + 결여/불일치 CalibSet `CalibrationError` 거부, 무단 대체 없음(음성 대조 포함) (XDET-TC-092, COMPOSE-4)
- [ ] 오류형·stage·context가 typed `EngineError`에 보존되고 실패 실행의 부분 결과가 성공으로 커밋되지 않음 (XDET-TC-092, COMPOSE-6)
- [ ] C# 측 DSP 산술·스테이지 정렬/조합·캘리브레이션 합성 부재 + 읽기 전용(골든/CalibSet/`data/` 쓰기 없음) (XDET-TC-093, COMPOSE-5)
- [ ] `common/modules/pipeline/metrics` + `apps/gui/` 무변경(git diff 없음) + SPEC-XSEAM-001 문서 무편집 (XDET-TC-093)
- [ ] `uv run pytest` 무회귀 green + `uv run lint-imports` green·불변 + `apps/xdet-console/` Python 트리 격리(pyproject 미포함·pytest 미수집)
- [ ] SAMPLE 실측 조합은 sanity(유한·비퇴화)만 단언, 수치 골든/EV 도출·튜닝 없음(QUARANTINE, 이슈 #29)
- [ ] DQE가 `mtf_value_at`+`compute_dqe`로 실행되고 support 밖 bin은 제외되며 UI 보간/외삽이 0건 (XDET-TC-155/164)
- [ ] tier decide/select/run/time, calibration builder, Lag state, NDT accumulator가 typed seam으로 실제 호출됨 (XDET-TC-163/167)
- [ ] `AlgorithmCatalogCoverageTests`가 façade/catalog/manifest/Contract/GUI/TC 6집합의 누락·중복·orphan 0건을 증명 (XDET-TC-160)
- [ ] strict user-supplied input은 등록 데이터 부재와 무관하게 실행되고 `USER_SUPPLIED_UNVERIFIED`로 기록 (XDET-TC-166)
- [ ] 어떤 C++/네이티브 조합 엔진도 구현하지 않음(XSEAM Stage 2/P2 범위)

## 판정 원칙 (측정=판정 분리)

- 조합 fidelity 허용오차(XDET-TC-021: 정수 bit-동일 / float ±1 LSB)는 CLAUDE.md T10 동일성 프레임에서 인용하며 심 내부에 하드코딩하지 않는다. P1.5 트랜스포트의 관측 delta는 정확히 0(bit-동일) 기대이고 ±1 LSB는 P2 C++ 조합 재계산 예약분이다.
- 조합/순서 권한은 `PipelineDefinition`(오케스트레이터)에, 캘리브레이션 admission은 `_calibration_gate`에 있으며 C#은 이를 판정하지 않고 결과만 표시한다(측정=판정 분리; C-09/C-11).
- SAMPLE 실측 수치는 비정본(QUARANTINE) — 조합 인수의 load-bearing 기준은 골든 대비 **동일성(delta 0)**·**명시 거부**·**무회귀**이지 SAMPLE 절대 수치가 아니다.

## v0.5.1 shared operation closure acceptance

- **Given** catalog manifest, injected tier policy, pipeline variants, sequence trigger가 있고,
- **When** Contract가 `modules.registry.default_registry`, `pipeline.orchestrator.PipelineDefinition.full`, `pipeline.orchestrator.calib_kind_for_stage`, `pipeline.orchestrator.run_pipeline`, `pipeline.sequence.run_sequence`, `pipeline.sequence.FBTrigger.request`, `pipeline.sequence.FBTrigger.confirm`, `pipeline.sequence.NoOpFBTrigger.request`, `pipeline.sequence.NoOpFBTrigger.confirm`, `pipeline.tier.decide_tier`, `pipeline.tier.select_pipeline`, `pipeline.tier.run_tier`, `pipeline.tier.time_tier`를 각 typed family로 호출하면,
- **Then** qualified EntryPoint와 request/result/error trace가 XDET-TC-161~163에 남고, forced upgrade는 거부되며 forced downgrade·offline trigger·cold/warm timing 구조가 보존되어야 한다.
