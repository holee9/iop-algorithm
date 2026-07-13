---
id: SPEC-XGUI-MASTER
version: 0.5.1
status: planned
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
priority: high
issue_number: 58
labels: [xgui, csharp-ui, gui-redesign, verification-gui, master, golden-frozen]
---

# SPEC-XGUI-MASTER — C# 알고리즘 사용·검증 GUI 마스터 사양

## 목적

동결된 XDET Python 골든의 **전체 공개 사용자 가치 알고리즘**을 사용·검증하기 위한 C# WPF 앱을 `apps/xdet-console/`에 구축한다. 앱은 알고리즘을 재구현하지 않고 `IXdetEngine` seam을 통해 골든을 호출하며, 사용자가 실제/합성 입력을 선택하고 파라미터·캘리브레이션을 공급해 처리·캘리브레이션 builder·지표·NDT·pipeline/sequence/tier를 실행·비교·저장할 수 있게 한다.

기존 `apps/gui/` Python 검증 GUI는 계약·시험 선례이며 이번 재설계의 구현 대상이 아니다. 목표 앱은 `apps/xdet-console/` 하나다.

## 소스 우선순위

1. `CLAUDE.md`, `docs/XDET_SWR_spec_v1.2.md`, `docs/XDET_measurement_protocol_v1.0.md`
2. 동결 골든 `common/`, `modules/`, `pipeline/`, `metrics/`
3. `SPEC-XSEAM-001/002`, `SPEC-VIEWER-001`, `docs/GUI_CRITERIA.md`
4. 본 마스터의 [algorithm-catalog.md](algorithm-catalog.md)와 8개 `SPEC-XGUI-*` 하위 사양
5. `apps/xdet-console/docs/viewer-redesign.html` 시각 방향 자료

충돌 시 상위 소스를 따른다. UI 문서가 골든의 시그니처·파라미터·수치 동작을 변경하지 않는다.

## Environment / Assumptions

- Windows, .NET 9 WPF, `Xdet.Engine.Contract`, `Xdet.Engine.PythonNet`, 동결 Python 3.11+ 골든을 사용한다.
- `SPEC-XSEAM-002`의 `RunPipeline` 미러, 정렬 부분수열, 중간 프레임 DTO, 거부 가드가 조합 탭의 선행 계약이다.
- 등록 에드로지 SAMPLE은 QUARANTINE이며 sanity에만 사용한다. 수치 골든·EV 임계·튜닝·피팅의 근거로 사용하지 않는다.
- 정본 실측은 `SPEC-GUIDING-001` 취득 세트가 준비된 뒤 별도 승격한다.
- 마스크·노이즈·이력의 수치 권위는 메모리 내 `XFrame`/DTO에 있다. 16-bit raw 내보내기는 운영 산출물이며 완전한 XFrame 직렬화 포맷이 아니다.
- `IXdetEngine`은 WPF가 Python을 호출하는 유일한 공개 경계다. 프레임 처리 그룹은 `run_pipeline`, Lag는 `run_sequence`, NDT/Metrics는 지표 전용 seam 메서드를 사용하되 WPF가 Python 모듈을 직접 import하거나 호출하지 않는다.
- 등록 데이터가 없는 기능도 `xdet.input-set/1.0`을 만족하는 사용자 제공 입력으로 실행할 수 있어야 하며, 구현 가능성과 데이터 증거 등급을 혼동하지 않는다.
- P1은 알고리즘 속도 최적화를 하지 않지만, GUI 이벤트 루프·취소·상태 일관성·메모리 상한은 실제 사용을 위한 앱 품질 계약으로 구현한다.

## Requirements (EARS)

### REQ-XGUI-MASTER-ARCH — 구현 경계

- **REQ-XGUI-MASTER-ARCH-1 (Ubiquitous)** — 시스템은 `apps/xdet-console/` C# WPF 앱을 유일 구현 대상으로 사용해야 하며 `apps/gui/`는 참조 선례로만 소비해야 한다.
- **REQ-XGUI-MASTER-ARCH-2 (Unwanted)** — IF UI 또는 어댑터가 DSP, 지표, 파이프라인 순서, 캘리브레이션 판정을 자체 계산하려 하면 THEN 구현·시험은 이를 거부해야 한다(C-09/C-11, G-1~G-8).
- **REQ-XGUI-MASTER-ARCH-3 (Ubiquitous)** — 시스템은 `common/`, `modules/`, `pipeline/`, `metrics/`를 동결 오라클로 취급하고 기존 파일을 변경하지 않아야 한다.
- **REQ-XGUI-MASTER-ARCH-4 (Ubiquitous)** — 시스템은 `algorithm-catalog.md`의 모든 ACTION·SESSION·DERIVED·INFRASTRUCTURE 연산을 `FeatureId → EntryPoint → DTO → GUI → TC`로 추적해야 하며, 분류되지 않은 공개 연산이나 호출할 수 없는 ACTION/SESSION이 존재하면 완료 판정을 거부해야 한다.

### REQ-XGUI-MASTER-SHELL — 공통 앱 셸

- **REQ-XGUI-MASTER-SHELL-1 (Ubiquitous)** — 앱은 상주 폴더 트리, 가상화 썸네일 목록, 형제 필름스트립, 이전/다음 이동을 한 셸에서 제공해야 한다.
- **REQ-XGUI-MASTER-SHELL-2 (Event-Driven)** — WHEN 사용자가 raw 파일 또는 폴더를 선택하면 THEN 앱은 사이드카를 검증하고 형제 입력을 인덱싱한 뒤 선택 프레임의 provenance·shape·dtype·domain을 표시해야 한다.
- **REQ-XGUI-MASTER-SHELL-3 (Unwanted)** — IF 입력 메타데이터가 없거나 shape/dtype/panel/domain이 계약과 맞지 않으면 THEN 앱은 추정 기본값을 만들지 않고 명시 오류로 거부해야 한다.
- **REQ-XGUI-MASTER-SHELL-4 (Event-Driven)** — WHEN 사용자가 단일 프레임·정렬 스택·시퀀스·프로파일·캘리브레이션 series·metric series를 열면 THEN 앱은 `xdet.input-set/1.0`의 해당 `input_kind`로 검증하고 ordered entry와 각 파일 hash를 보존해야 한다.

### REQ-XGUI-MASTER-TABS — 목적별 8개 탭

- **REQ-XGUI-MASTER-TABS-1 (Ubiquitous)** — 앱은 Calibration, Lag, Line/Sat/Geo, Denoise, Enhancement, Grid/Virtual-Grid, NDT, Metrics의 8개 목적별 탭을 제공해야 한다.
- **REQ-XGUI-MASTER-TABS-2 (Ubiquitous)** — 각 탭은 자기 입력 세트, Params, CalibSet, 그룹 고유 뷰어, 실행·저장 상태를 독립적으로 소유하되 공통 셸과 비교·내보내기 컴포넌트를 재사용해야 한다.
- **REQ-XGUI-MASTER-TABS-3 (Event-Driven)** — WHEN 사용자가 탭을 전환하면 THEN 앱은 해당 탭의 상태를 보존하되 다른 탭의 실행 상태·CalibSet·Params를 암묵적으로 재사용하지 않아야 한다.

### REQ-XGUI-MASTER-SEAM — 엔진 위임

- **REQ-XGUI-MASTER-SEAM-1 (Ubiquitous)** — 모든 처리·지표 산출은 `IXdetEngine`을 통해 Python 골든에 위임되어야 한다.
- **REQ-XGUI-MASTER-SEAM-2 (Event-Driven)** — WHEN 사용자가 개별 스테이지를 실행하면 THEN seam은 정확한 `XFrame`, `CalibSet`, `Params`를 골든 진입점에 전달하고 엔진 결과 DTO를 반환해야 한다.
- **REQ-XGUI-MASTER-SEAM-3 (Event-Driven)** — WHEN 사용자가 정렬된 부분집합 또는 전체 조합을 실행하면 THEN seam은 `run_pipeline`을 한 번 호출하고 최종 출력과 `intermediates`를 반환해야 한다.
- **REQ-XGUI-MASTER-SEAM-4 (Unwanted)** — IF 요청 스테이지가 `CANONICAL_ORDER` 부분수열이 아니거나 CalibSet이 결여·불일치하면 THEN 앱은 `PipelineOrderError` 또는 `CalibrationError` 의미를 보존해 표시하고 대체값으로 계속하지 않아야 한다.
- **REQ-XGUI-MASTER-SEAM-5 (Ubiquitous)** — Lag·NDT·Metrics처럼 `run_pipeline` 대상이 아닌 기능도 WPF가 Python을 직접 호출하지 않고 `IXdetEngine`의 sequence/metric 전용 요청·결과 DTO를 통해 실행해야 한다. 이 메서드가 PythonNet 내부에서 호출하는 골든 공개 함수명은 결과 provenance에 기록해야 한다.
- **REQ-XGUI-MASTER-SEAM-6 (Ubiquitous)** — seam DTO는 최소 pixel·mask·noise와 함께 domain, validation mode, history(module/version/params hash/calibset id), `EvidenceGrade`, warnings를 손실 없이 운반해야 하며, 조합 결과는 실행 스테이지별 intermediate DTO를 순서대로 운반해야 한다.
- **REQ-XGUI-MASTER-SEAM-7 (Ubiquitous)** — `IXdetEngine`은 FRAME_PROCESS, PIPELINE, SEQUENCE, STACK_METRIC, PROFILE_METRIC, CALIBRATION_BUILD, METRIC_SERIES, NDT_SESSION, TIER family의 typed request/result를 제공해야 하며 Contract 바깥으로 `PyObject`·`dynamic`·임의 `object` payload를 노출하지 않아야 한다.
- **REQ-XGUI-MASTER-SEAM-8 (Event-Driven)** — WHEN 사용자가 tier 판단·강제 downgrade·tier 실행·구조 timing을 요청하면 THEN seam은 `pipeline.tier.decide_tier/select_pipeline/run_tier/time_tier`를 호출하고 decision rationale·selected definition·timing record를 반환해야 한다. silent default tier와 강제 upgrade는 허용하지 않는다.

### REQ-XGUI-MASTER-JOB — 실행 상태·취소·동시성

- **REQ-XGUI-MASTER-JOB-1 (Event-Driven)** — WHEN 사용자가 처리·시퀀스·지표 실행을 요청하면 THEN 앱은 전역 고유 `run_id`를 발급하고 `Queued → Validating → Running → Marshalling → Completed|Failed|Canceled` 상태를 해당 탭에 표시해야 한다.
- **REQ-XGUI-MASTER-JOB-2 (Ubiquitous)** — 모든 PythonNet 엔진 호출은 UI 스레드 밖의 job coordinator에서 수행하고, 단일 Python 엔진/GIL 경계에는 한 번에 하나의 호출만 진입하도록 직렬화해야 한다.
- **REQ-XGUI-MASTER-JOB-3 (Event-Driven)** — WHEN 사용자가 실행을 취소하면 THEN 앱은 해당 `run_id`를 즉시 Canceled로 표시하고, 골든 호출이 협력 취소를 지원하지 않더라도 늦게 반환한 결과가 탭 상태·파일·최근 결과를 덮지 못하게 해야 한다.
- **REQ-XGUI-MASTER-JOB-4 (Unwanted)** — IF 엔진이 세부 진행률을 반환하지 않으면 THEN 앱은 허위 백분율을 만들지 않고 현재 phase와 경과 시간만 표시해야 한다.
- **REQ-XGUI-MASTER-JOB-5 (State-Driven)** — WHILE 한 탭의 실행이 활성 상태이면 앱은 그 탭의 중복 실행·저장을 막되 탐색·비활성 탭 조회·취소 조작은 응답 가능하게 유지해야 한다.
- **REQ-XGUI-MASTER-JOB-6 (Ubiquitous)** — 3072² 프레임의 W/L·zoom/pan·probe는 알고리즘 재실행이나 매 이벤트 전체 배열 복사 없이 동작해야 하며, before/after/diff와 마스크의 상주 메모리는 명시적 LRU/해제 정책으로 제한해야 한다(C-01~C-04, C-18~C-19).

### REQ-XGUI-MASTER-VIEW — 공통 검증 화면

- **REQ-XGUI-MASTER-VIEW-1 (Ubiquitous)** — 프레임 산출 탭은 before/after/diff, 공유 W/L, zoom/pan, 픽셀 probe, blink, 마스크 오버레이, 처리 이력을 제공해야 한다.
- **REQ-XGUI-MASTER-VIEW-2 (State-Driven)** — WHILE `validation_mode` 중간 프레임이 존재하면 앱은 추가 엔진 호출 없이 스테이지별 전/후를 스크럽해야 한다.
- **REQ-XGUI-MASTER-VIEW-3 (Ubiquitous)** — 표시되는 수치·곡선·진단은 엔진 반환 DTO 또는 골든 공개 함수 결과의 read-only 표현이어야 하며 UI가 새 수치를 산출하지 않아야 한다.

### REQ-XGUI-MASTER-PARAM — 입력·Params·CalibSet manifest

- **REQ-XGUI-MASTER-PARAM-1 (Ubiquitous)** — `IXdetEngine`은 각 대상 기능에 대해 `FeatureId`, qualified Python `EntryPoint`, 9-family kind, `InputKind`, required/optional Params, required CalibKind, output DTO kind, `AlgorithmAvailability`를 담은 versioned `AlgorithmCatalogManifest`를 제공해야 한다. 실행별 `EvidenceGrade`는 이 정적 manifest가 아니라 result/run manifest에 기록한다.
- **REQ-XGUI-MASTER-PARAM-2 (Ubiquitous)** — 각 `ParamDefinition`은 `Key`, scalar/enum/array `ValueType`, unit, required 여부, 값 제약, default의 권위 소스(`Params/config/none`), selector 기반 `VisibleWhen`을 포함해야 한다. UI는 manifest를 렌더할 뿐 numeric default·범위·필수 키를 자체 하드코딩하지 않아야 한다.
- **REQ-XGUI-MASTER-PARAM-3 (State-Driven)** — WHILE denoise/MSE처럼 selector에 따라 required Params가 달라지면 adapter는 현재 selector Params로 골든 `required_params(params)`를 호출해 manifest를 갱신하고, 실행 직전에 표시된 필수 키 집합과 골든 반환 집합이 동일한지 검증해야 한다.
- **REQ-XGUI-MASTER-PARAM-4 (Unwanted)** — IF 문서/SWR metadata의 키가 골든 `REQUIRED_PARAMS`·`required_params`와 불일치하거나 default 권위 소스가 없으면 THEN 앱은 해당 기능을 실행 가능으로 표시하지 않고 manifest mismatch를 진단해야 한다.

### REQ-XGUI-MASTER-EXPORT — 운영 산출물과 보호

- **REQ-XGUI-MASTER-EXPORT-1 (Event-Driven)** — WHEN 사용자가 프레임 결과를 저장하면 THEN 앱은 사용자 지정 폴더에 `<name>_result.raw`와 `<name>_result.json`을 생성해야 한다.
- **REQ-XGUI-MASTER-EXPORT-2 (Ubiquitous)** — raw-DN 결과는 `uint16` little-endian으로, display-normalized 결과는 `round(clip(x,0,1)*65535)`로 저장하고 사이드카에 `source_domain`, `export_domain`, `domain_max`, `quantization`을 기록해야 한다.
- **REQ-XGUI-MASTER-EXPORT-3 (State-Driven)** — WHILE 결과에 마스크가 존재하면 앱은 XFrame `MASK_DTYPE`과 동일한 `<name>_result_mask.raw` `uint8` bitmask와 플래그 사전을 사이드카에 기록해야 한다.
- **REQ-XGUI-MASTER-EXPORT-4 (Unwanted)** — IF 출력 경로가 저장소 `data/` 아래로 해석되면 THEN 엔진의 C-20 경로 가드는 저장을 거부해야 한다.
- **REQ-XGUI-MASTER-EXPORT-5 (Ubiquitous)** — 내보낸 raw는 운영·재열기 산출물로 라벨해야 하며, `XFrame`의 float32·noise·history 전체를 보존하는 골든 스냅샷이라고 주장하지 않아야 한다.
- **REQ-XGUI-MASTER-EXPORT-6 (Ubiquitous)** — 모든 frame sidecar와 metric/report JSON은 동일한 `run_manifest`를 포함해야 한다. 최소 필드는 `schema_version`, `run_id`, UTC timestamp, FeatureId/family/`AlgorithmAvailability`, input 상대/표시 경로와 SHA-256/`EvidenceGrade`, resolution/dtype, source/export domain, ordered qualified EntryPoints, canonical Params/hash, CalibSet id/kind/provenance/payload hash, adapter/Python/golden version, validation mode, warnings/typed error, 생성한 raw/mask/report hash다.
- **REQ-XGUI-MASTER-EXPORT-7 (Event-Driven)** — WHEN 사용자가 저장 산출물을 다시 열어 검증하면 THEN 앱은 sidecar schema/hash를 먼저 검증하고, 같은 입력·Params·CalibSet이 가용한 경우 재실행 결과와 저장 직전 in-memory DTO를 각각 비교해 `artifact round-trip`과 `run reproducibility`를 구분해 표시해야 한다.

### REQ-XGUI-MASTER-CAP — 실행 가능성과 데이터 증거

- **REQ-XGUI-MASTER-CAP-1 (Ubiquitous)** — 각 FeatureId는 `AlgorithmAvailability(IMPLEMENTED|NOT_IMPLEMENTED|PREREQUISITE_MISSING|UNSUPPORTED)`와 실행별 `EvidenceGrade(SYNTHETIC_VERIFIED|SAMPLE_SANITY|USER_SUPPLIED_UNVERIFIED|GUIDING_CANDIDATE|GOLDEN_APPROVED)`를 별도 필드로 표시해야 한다.
- **REQ-XGUI-MASTER-CAP-2 (Event-Driven)** — WHEN 필요한 입력·Params·CalibSet이 제공되면 THEN 등록 정본 데이터의 유무와 무관하게 IMPLEMENTED 알고리즘을 실행할 수 있어야 하며, 외부 실측 입력은 승인 전 `USER_SUPPLIED_UNVERIFIED`로 기록해야 한다.
- **REQ-XGUI-MASTER-CAP-3 (Unwanted)** — IF 실행 증거가 SAMPLE_SANITY이면 THEN 앱과 시험은 유한·비퇴화·구조 성립만 판정하고 EV·튜닝·피팅 결과를 확정하지 않아야 한다.
- **REQ-XGUI-MASTER-CAP-4 (Unwanted)** — IF evidence grade가 `SYNTHETIC_VERIFIED`, `SAMPLE_SANITY`, `USER_SUPPLIED_UNVERIFIED`이면 THEN UI·리포트·완료 판정은 이를 정본 실측 검증 완료로 표현하지 않아야 한다.

### REQ-XGUI-MASTER-TRACE — 중앙 시험 추적

- **REQ-XGUI-MASTER-TRACE-1 (Ubiquitous)** — XGUI 시험 ID는 그룹 096부터 159까지와 공통 완결성 `XDET-TC-160~167` 중앙 레지스트리를 따라야 하며 하위 SPEC이 임의 재배정하지 않아야 한다.
- **REQ-XGUI-MASTER-TRACE-2 (Ubiquitous)** — 각 GUI-E2E 시험은 기존 알고리즘 TC를 대체하지 않고 UI·seam·입출력·거부·표시 계약을 검증해야 한다.
- **REQ-XGUI-MASTER-TRACE-3 (Ubiquitous)** — 구현 PR은 사용된 GUI-E2E ID를 `docs/XDET_TestSpec_v1.0.md`와 자동화 테스트 이름에 1:1 등록해야 하며, `제안 TC`·중복 ID·문서에만 존재하는 PASS를 허용하지 않아야 한다.

### REQ-XGUI-MASTER-DQE — DQE 경계

- **REQ-XGUI-MASTER-DQE-1 (Event-Driven)** — WHEN 사용자가 MTF와 NPS 결과를 선택해 DQE 합성을 요청하면 THEN engine은 axis/unit/pixel-pitch/domain/provenance를 검증하고 `NPS_BINS_WITHIN_MTF_SUPPORT_V1` 정책으로 MTF support 안의 NPS bin을 선택해야 한다.
- **REQ-XGUI-MASTER-DQE-2 (Ubiquitous)** — engine은 선택된 각 주파수에서 골든 `metrics.mtf.mtf_value_at`을 호출해 MTF를 얻은 뒤 동일 axis의 NNPS와 함께 `metrics.dqe.compute_dqe`를 호출해야 하며, 두 EntryPoint와 upstream run/hash·선택/제외 bin을 결과 provenance에 기록해야 한다.
- **REQ-XGUI-MASTER-DQE-3 (Unwanted)** — IF WPF 또는 C# UI 계층이 보간·DQE 수치·외삽을 계산하거나 engine이 MTF support 밖의 NPS bin을 endpoint 값으로 외삽하려 하면 THEN 실행·시험은 이를 거부해야 한다.
- **REQ-XGUI-MASTER-DQE-4 (State-Driven)** — WHILE 등록 슬랜티드-엣지 정본 데이터가 없으면 DQE 알고리즘은 실행 가능하되 결과 evidence grade는 입력에 따라 `SYNTHETIC_VERIFIED` 또는 `USER_SUPPLIED_UNVERIFIED`를 초과해서는 안 된다.

### REQ-XGUI-MASTER-GATE — 문서 승인과 구현 착수

- **REQ-XGUI-MASTER-GATE-1 (Ubiquitous)** — 시스템 구현은 [baseline-control.md](baseline-control.md)의 G0 열두 조건을 모두 충족하고 사용자가 기준선 버전을 명시적으로 승인하기 전에는 시작되지 않아야 한다.
- **REQ-XGUI-MASTER-GATE-2 (Unwanted)** — IF 내부 감사, 기존 회귀시험, 정적 집합 검사 또는 작성자 판단만 통과했으면 THEN 문서를 `APPROVED_AND_FROZEN` 또는 구현 허가 상태로 표시해서는 안 된다.
- **REQ-XGUI-MASTER-GATE-3 (Event-Driven)** — WHEN 사용자가 기준선을 승인하면 THEN 승인된 버전·승인 일시·범위를 `baseline-control.md`에 기록하고 모든 규범 문서의 `approval_state`와 `implementation_authorized`를 원자적으로 동기화해야 한다.
- **REQ-XGUI-MASTER-GATE-4 (Event-Driven)** — WHEN 승인 뒤 알고리즘 범위, DTO, Params/CalibSet, 실행 순서, 수치 기준, TC 배정 또는 저장 포맷이 바뀌면 THEN 기준선 버전을 올리고 영향 분석·전수 교차검증·사용자 재승인을 수행해야 한다.
- **REQ-XGUI-MASTER-GATE-5 (Unwanted)** — IF 구현 중 사양 결함이 발견되면 THEN 코드에서 기본값이나 임의 해석으로 우회해서는 안 되며 문서와 영향 TC를 먼저 개정해야 한다.
- **REQ-XGUI-MASTER-GATE-6 (State-Driven)** — WHILE `implementation_authorized=false`이면 계획의 M1 이후 소스·XAML·테스트·패키지·빌드 설정 변경은 금지돼야 한다.

## 중앙 TC 레지스트리

| 그룹 | 할당 블록 | 현재 사용 |
|---|---:|---:|
| Calibration | 096~103 | 096~103 |
| Lag | 104~111 | 104~111 |
| Line/Sat/Geo | 112~119 | 112~119 |
| Denoise | 120~127 | 120~127 |
| Enhancement | 128~135 | 128~135 |
| Grid/Virtual-Grid | 136~143 | 136~143 |
| NDT | 144~151 | 144~151 |
| Metrics | 152~159 | 152~159 |
| Shared completeness | 160~167 | 160~167 |

096~167의 의미는 중앙 TestSpec과 algorithm catalog에서 고정한다. 구현 중 새 의미를 즉석 배정하거나 하나의 자동화 이름을 여러 의미로 재사용하지 않는다.

## Exclusions (What NOT to Build)

- C# 또는 UI 측 알고리즘·지표·보간·판정 재구현
- Python 골든, 기존 Python GUI 또는 골든 데이터의 수정
- 비정렬 파이프라인 실행과 무단 CalibSet/Params 기본값
- SAMPLE로부터 EV·튜닝·피팅·수치 골든 도출
- DQE 축 정렬·보간·외삽을 WPF/UI에서 구현
- Qt/PySide/napari를 제품 GUI 프레임워크 또는 WPF 실행 경계로 도입
- DL denoise, DL scatter, ADR, C++ 네이티브 엔진

## Dependencies

- `SPEC-XSEAM-002`: 조합 seam과 중간 프레임
- `SPEC-GUIDING-001`: 정본 실측 승격
- `SPEC-ERGO-001`: Params introspection
- `SPEC-VIEWER-001`: 이미지 상호작용·비교·가드 선례
- 8개 하위 `SPEC-XGUI-*`: 그룹별 입력·뷰어·인수 기준
- [algorithm-catalog.md](algorithm-catalog.md): 공개 연산 전수 분류와 FeatureId/DTO/GUI/TC 추적성
- [traceability-matrix.md](traceability-matrix.md): 모든 EARS 요구사항의 인수·TC·증거 연결
- [baseline-control.md](baseline-control.md): 사용자 승인, 기준선 동결, 구현 착수 통제
