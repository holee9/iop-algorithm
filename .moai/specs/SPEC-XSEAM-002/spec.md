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

# SPEC-XSEAM-002 — 언어 중립 전체 알고리즘 엔진 심 + 조합·세션·지표 검증 UI

> 본 사양은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 `traceability-matrix.md`를 상속한다. 사용자 승인·기준선 동결·`implementation_authorized=true` 전에는 구현 입력으로 실행하지 않으며, 승인 뒤 규범 변경은 버전 상승과 재승인을 요구한다.

C# WPF 검증 GUI(이슈 #58, C# GUI 재설계)의 **다단계(다중 선택·조합) 스테이지 적용 검증** 확장이다. [SPEC-XSEAM-001](../SPEC-XSEAM-001/spec.md)(P1.5 얇은 수직 슬라이스, 병합·동결)을 **증강(augment)** 하며 **편집하지 않는다**. XSEAM-001은 모듈 1개(`offset`) + 지표 1개(MTF)를 심 경유로 구동하는 얇은 슬라이스였고 **전체 파이프라인 실행·스테이지별 비교를 명시적으로 범위 밖으로 두었다**("전체 파이프라인 실행, 스테이지별 비교는 P1.5 범위 밖", XSEAM-001 spec.md:92). 본 SPEC은 그 배제된 능력을 심 계약에 채운다.

**문제(사용자 요구):** 각 보정/처리 스테이지는 저마다 **구별되는 입력**(offset/dark, gain/flat, defect map, …)을 가지므로 스테이지별 결과를 개별로 확인할 수 있어야 하고, 개별 적용이 확인된 뒤에는 **선택한 부분집합/전체 조합** 결과도 검증할 수 있어야 한다. 검증 결과, **동결된 Python 골든 엔진은 이미 조합 실행을 완전히 지원한다**(`pipeline.orchestrator.run_pipeline` + `PipelineDefinition`). 실제 격차는 (a) 언어 중립 심 `IXdetEngine`이 `process`/`compute_*`만 미러하고 `run_pipeline` 미러(조합 진입점)가 **없다는 것**, (b) XSEAM-001 슬라이스가 조합을 배제했다는 것 두 가지다. 조합 자체는 골든에 이미 있으므로 본 SPEC은 **심에 조합 진입점을 노출**하고 **C# UI가 그것을 소비**하도록만 한다 — DSP도 조합 권한도 C#에 두지 않는다.

v0.5.1은 여기서 한 단계 더 나아가 파이프라인뿐 아니라 calibration builder, stack/profile metric, NDT session, DQE composition, tier까지 [SPEC-XGUI-MASTER algorithm catalog](../SPEC-XGUI-MASTER/algorithm-catalog.md)의 전체 ACTION/SESSION 경계를 `IXdetEngine`에 노출한다. 단지 파일명이 문서에 존재하는 것으로는 완료가 아니며, 모든 FeatureId가 typed request/result와 실제 golden EntryPoint를 가져야 한다. 또한 G0 사용자 승인·동결 전에는 구현을 시작하지 않는다.

**Python 선례:** [SPEC-VIEWER-001](../SPEC-VIEWER-001/spec.md)(napari→pyqtgraph 검증 GUI, status: implemented)의 Python 뷰어가 이미 이 능력을 명세했다 — **REQ-VIEW-RUN-1**(단일 모듈을 `ProcessModule.process`로 직접 실행 → 입력/출력 쌍)과 **REQ-VIEW-RUN-2**(파이프라인 부분/전체 실행 → 스테이지별 전/후, `run_pipeline`·`CANONICAL_ORDER`). SPEC-XSEAM-002는 C# 심에 대해 RUN-1(개별)·RUN-2(부분/전체)를 미러한다.

- 근거(변경 없음, 소비만): `pipeline/orchestrator.py::run_pipeline(frame, definition, registry, calib_map, params_map, *, panel_id, timestamp, domain)`(단일 조합 진입점, @MX:ANCHOR SWR-000-8/-2) · `PipelineDefinition(stages)`(정렬된 스테이지 부분집합 = 조합 권한, `CANONICAL_ORDER` 부분수열 강제, `__post_init__` 위반 시 `PipelineOrderError`) · `CANONICAL_ORDER`(offset→gain→defect→lag→line_noise→saturation→geometry→grid→virtual_grid→denoise→mse→window→**post**, post는 예약 tail·등록 모듈 없음) · `_calibration_gate`(부재/불일치 CalibSet 거부 → `CalibrationError`, 무단 기본값 대체 금지) · `calib_kind_for_stage(stage)->CalibKind`(스테이지↔CalibKind 공개 접근자; 미등록 스테이지는 `CalibKind.OTHER`) · `pipeline/sequence.py::run_sequence`(상태형 lag용 시퀀스 러너) · `modules/registry.py::default_registry`(스테이지→ProcessModule; run_pipeline이 요구하는 것과 구별됨) · `common/xframe.py`(XFrame, `validation_mode`→`intermediates`) · `common/equivalence.py::diff_frames`(동일성 훅) · `modules/{offset,gain,defect,…}.py::process`
- 상속 원칙: SPEC-XSEAM-001과 동일하게 SPEC-VIEWER-001의 [HARD] 원칙을 C#으로 상속 — **읽기-실행 전용**(C-20), **지표/DSP 자체 계산 0**(C-09: UI/어댑터는 스스로 계산하지 않고 실제 엔진 결과만 표시), **단방향 소비**(C-11). 조합/순서 권한은 **Python 오케스트레이터에 남는다**(C#은 스테이지를 정렬·조합하지 않는다).
- 완료 정의(DoD): (1) 심 `IXdetEngine`이 `run_pipeline`을 미러하는 조합 진입점 + `PipelineDefinition`/`calib_map`/`params_map`/`intermediates` DTO를 노출(XDET-TC-088) → (2) 어댑터가 스테이지별 CalibSet/Params로 개별 스테이지를 심 경유 구동·표시(XDET-TC-089) → (3) 정렬된 부분집합/전체를 단일 심 실행으로 구동 + 조합 출력·스테이지별 전/후 표시(XDET-TC-090) → (4) 검증 모드 단일 패스로 `XFrame.intermediates` 반환·추가 실행 없이 스크럽(XDET-TC-091) → (5) 비-부분수열/불일치 캘리브레이션은 오케스트레이터 명시 오류로 거부·무단 대체 없음(XDET-TC-092) → (6) C# 측 DSP·조합·캘리브레이션 합성 부재 + 읽기 전용(XDET-TC-093). 골든 무변경, C++ 엔진 이식은 범위 밖.
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.4.0 (2026-07-13)** — 전체 알고리즘 범위 보강. 9개 실행 family, calibration builder/NDT session/tier DTO, AlgorithmAvailability/EvidenceGrade 분리, catalog coverage를 추가했다. 기존 골든 `metrics.mtf.mtf_value_at`을 이용하는 engine-owned DQE 합성 경로를 확정해 DQE의 영구 비활성 결정을 제거했다.

- **v0.3.0 (2026-07-13)** — XGUI 의미 교차검토 반영. generic request/result DTO의 필수 필드, Python GUI helper 비의존, typed error, XFrame history/domain/data-grade 운반을 확정했다. .NET 기준을 현재 앱과 동일한 .NET 9로 정정했다.

- **v0.2.0 (2026-07-13)** — SPEC-XGUI 문서 복구와 정합. 현재 C# `RunPipeline`이 offset→gain 고정 슬라이스임을 명시하고 generic ordered subset 계약, SAMPLE 3-stage sanity, stage-by-stage fidelity를 확정했다. 골든은 변경하지 않는다.

- **v0.1.0 (2026-07-12)** — 초안 생성. GitHub 이슈 #58(C# GUI 재설계). SPEC-XSEAM-001(이슈 #50)을 **증강**(편집 아님). 2개 요구 그룹(CONTRACT/COMPOSE) EARS 6개(CONTRACT-6 + COMPOSE-1~5). 시험케이스 블록 **XDET-TC-088~093**(Gen 1 000~021 / VIEWER 030~037 / REALDATA 040~049 / ERGO 050~055 / CALDOM 060~067 / DQEDOC 070~073 / XSEAM-001 080~087 범위 밖 신규 블록; 094~095 예약). 저작 시 **AUTHORITATIVE 소스로 검증한 사실**: (a) `run_pipeline`이 요구하는 레지스트리는 `{stage: module.process}`(bare 콜러블)이며 `default_registry()`가 반환하는 `{stage: ProcessModule 객체}`가 **아니다** — `modules/registry.py` 도크스트링이 "does NOT replace … the per-run registry `run_pipeline` requires (stage -> process CALLABLE)"로 명시(어댑터는 `.process`를 추출해 전달). (b) `PipelineDefinition.full()`은 `post`를 **포함한** `CANONICAL_ORDER` 전체를 반환하지만 `post`는 등록 모듈이 없어 실제 구동 시 `CalibrationError("stage 'post': no processing callable registered")`가 발생 → **구동 가능한 전체 파이프라인 = `tuple(s for s in CANONICAL_ORDER if s != "post")`**. (c) `frame.validation_mode`가 True면 `run_pipeline`이 스테이지별 출력을 `replace(current, intermediates=preserved)`로 결과에 부착 → `result.intermediates[i]` = i번째 실행 스테이지의 출력(단일 패스 전/후). (d) 실측(SAMPLE·비정본, 이슈 #29 QUARANTINE) 등록 데이터로 **구동 가능한 스테이지 = offset(MasterDark)·gain(CalSet_19008)·defect(BPM)**; lag는 placeholder 고정 IRF(비정본); 나머지(line_noise/saturation/geometry/grid/virtual_grid/denoise/mse/window)는 합성 전용/#33 대기. (e) `calib_kind_for_stage`는 **공개** 접근자(사설 `_KIND_BY_STAGE` 아님). (f) SWR-000-2(순서 고정)·SWR-000-5(무단 기본값 대체 금지) 확인. 확정 설계 결정: 조합 권한은 골든 오케스트레이터에 남기고(C#은 미러 DTO만 전달) 심은 순수 트랜스포트(XSEAM-001 상속) — 관측 fidelity delta는 여전히 정확히 0 기대.

## Environment / Assumptions

- **본 SPEC은 T-스테이지가 아니다.** `CANONICAL_ORDER` 스테이지 추가·`process(...)->XFrame` 시그니처 변경·신규 `CalibKind`·`_KIND_BY_STAGE` 변경이 전혀 없다. Python 코어 4계층과 오케스트레이터 표면은 불변이며, 본 SPEC은 그 위에 **C# 조합 소비자**를 additive로 얹는다(SPEC-XSEAM-001·SPEC-VIEWER-001 검증 도구 계열의 확장).
- **XSEAM-001 증강, 무편집.** 본 SPEC은 병합·동결된 SPEC-XSEAM-001을 편집하지 않는다. XSEAM-001의 얇은 슬라이스(offset+MTF, 조합 배제)를 상위 집합으로 확장하되, XSEAM-001의 확정 아키텍처(`IXdetEngine` durable 심 / pythonnet in-process 어댑터 / WPF+ScottPlot UI / `apps/xdet-console/` 격리 / 골든 동결 오라클)를 그대로 계승한다.
- **조합은 골든에 이미 있다 — 심에는 없다.** `pipeline.orchestrator.run_pipeline`이 `PipelineDefinition`(정렬된 스테이지 부분집합) + 스테이지별 `CalibSet` 맵 + 스테이지별 `Params` 맵을 받아 부분집합/전체 조합을 이미 구동한다. 격차는 언어 중립 심 `IXdetEngine`이 `process`/`compute_*`만 미러하고 이 조합 진입점을 미러하지 않는다는 것뿐이다. 본 SPEC은 그 미러를 추가한다.
- **조합/순서 권한은 Python 오케스트레이터에 남는다.** 고정 정준 순서(SWR-000-2)와 캘리브레이션 진입 게이트(SWR-000-5, 부재/해상도·panel_id 불일치 거부)는 `PipelineDefinition.__post_init__`(부분수열 강제 → `PipelineOrderError`)와 `_calibration_gate`(→ `CalibrationError`)가 강제한다. C# 측은 스테이지를 스스로 정렬·조합하거나 캘리브레이션을 합성하지 않고 미러 DTO만 전달한다.
- **레지스트리 형태(검증됨).** `run_pipeline`의 `registry` 인자는 `Mapping[str, ProcessCallable]`(= `{stage: module.process}` bare 콜러블)이다. `modules/registry.py::default_registry()`는 `{stage: ProcessModule 객체}`(또는 `lag`용 신규 `LagCorrector()` 인스턴스)를 반환하며 GUI 모듈 선택 UI(REQ-VIEW-CORE-2)와 `run_harness`용이고 `run_pipeline`용이 **아니다**(레지스트리 도크스트링 명시). 어댑터는 각 스테이지의 `.process`를 추출해 `run_pipeline` 레지스트리를 구성한다.
- **전체 파이프라인의 구동 가능 집합(검증됨).** `PipelineDefinition.full()`은 `post` 포함 `CANONICAL_ORDER` 전체를 반환하나 `post`는 등록 모듈이 없어 구동 불가(`CalibrationError`). 따라서 C# 심이 구동하는 "전체 등록 파이프라인" = `PipelineDefinition(stages=tuple(s for s in CANONICAL_ORDER if s != "post"))`. 전체 구동은 진입 게이트가 각 등록 스테이지마다 해상도·panel_id 일치 CalibSet을 요구하며, 미등록 kind 스테이지(saturation/geometry/grid/mse/window)는 CalibSet(OTHER) placeholder로 게이트를 만족한다.
- **검증 모드 단일 패스 중간 프레임(검증됨).** 입력 `XFrame.validation_mode`가 True면 `run_pipeline`이 스테이지별 출력을 누적해 결과에 `intermediates`로 부착한다(`result.intermediates[i]` = i번째 실행 스테이지 출력). 조합 실행 한 번으로 모든 스테이지 전/후가 확보되어 추가 실행 없이 스크럽 가능하다.
- **스테이지별 구별 입력.** 각 보정 스테이지는 고유의 `CalibSet`(offset=OFFSET `O_map`, gain=GAIN `G_map`, defect=DEFECT `class_map`, denoise=NOISE (α,σ), virtual_grid=SCATTER 커널, …)과 고유의 `Params`를 소비한다. `calib_kind_for_stage(stage)`가 스테이지가 요구하는 CalibKind를 알려준다. UI/어댑터는 스테이지별로 그 구별 입력을 수집해 `calib_map`/`params_map`으로 전달한다.
- **등록 데이터와 실행 가능성 분리(SAMPLE·비정본, QUARANTINE 이슈 #29).** 등록 edrogi SAMPLE로 직접 sanity 가능한 스테이지는 offset·gain·defect이며 lag는 placeholder IRF다. 나머지는 저장소 등록 evidence가 합성 또는 #33 대기라는 뜻일 뿐 알고리즘 비활성 의미가 아니다. strict schema를 만족한 사용자 입력은 실행하고 `USER_SUPPLIED_UNVERIFIED`로 기록한다. SAMPLE은 유한·비퇴화·구조 sanity만 확인하며 수치 golden·튜닝·적합에 쓰지 않는다.
- **모듈 간 조합 제약(검증됨).** `mse` 스테이지는 상류 노이즈 모델(α,σ) 없이 하드 실패한다 — `denoise`를 먼저 거치거나 α>0으로 사전 적재된 프레임이 필요하며, 결여 시 조합 버그가 아니라 **모듈 자신의 명시 오류**(MseError, SWR-803 게이트)로 표면화한다. 다중 프레임 lag 정확성은 `pipeline/sequence.py::run_sequence`(시퀀스당 하나의 상태형 `LagCorrector`)로 얻으며 단일 프레임 `run_pipeline` 반복이 아니다.
- **Fidelity(load-bearing, XSEAM-001 상속).** 조합 심 경유 결과가 Python 골든 직접 `run_pipeline` 출력과 XDET-TC-021 허용오차 내로 일치함을 단언한다(XFrame 경로는 `diff_frames` 재사용). 어댑터는 트랜스포트라 관측 delta는 정확히 0(bit-동일) 기대이며 ±1 LSB envelope는 P2 C++ 재계산 예약분이다.
- **환경.** Python은 `uv run`으로만 실행(`uv run pytest`, `uv run lint-imports`), 현재 C# 앱은 .NET 9 WPF(`dotnet`)를 사용한다. 정확성·재현성이 목적이며 알고리즘/마샬링 속도 최적화는 목적이 아니다. 단, UI 스레드 비차단·취소 후 늦은 결과 억제는 성능 최적화가 아니라 앱 상태 안전성 요구다.

## Requirements (EARS)

### REQ-XSEAM-CONTRACT — 조합 심 진입점: `run_pipeline` 미러 (SWR-000-2/-5, SPEC-XSEAM-001 CONTRACT 연장, XDET-TC-088)

> XSEAM-001의 REQ-XSEAM-CONTRACT-1~5(단일 `process`/`compute_*` 미러)에 이어 6번으로 조합 진입점을 추가한다(번호 연속, 충돌 없음).

- **REQ-XSEAM-CONTRACT-6 (Ubiquitous)** — C# 엔진 심 `IXdetEngine`은 `pipeline.orchestrator.run_pipeline`을 미러하는 파이프라인 조합 진입점을 노출해야 하며, 정렬된 스테이지 부분집합(`CANONICAL_ORDER`의 부분수열 — `PipelineDefinition` 미러)·스테이지별 `CalibSet` 맵·스테이지별 `Params` 맵을 입력받아, 부분집합 또는 전체 등록 파이프라인이 조합을 C# 측에서 재구현하지 않고 durable 심을 거쳐 구동되어야 한다 — 고정 정준 순서와 캘리브레이션 진입 게이트는 C# 측이 아니라 Python 오케스트레이터가 강제해야 한다(SWR-000-2 순서 고정 / SWR-000-5 기본값 무단 대체 금지).
- **REQ-XSEAM-CONTRACT-7 (Ubiquitous)** — generic 진입점은 아래 `PipelineRunRequest`와 `PipelineRunResult`의 필수 필드를 갖는 언어 중립 DTO를 사용해야 하며 `object`/dynamic Python 객체를 Contract 밖으로 노출하지 않아야 한다.
- **REQ-XSEAM-CONTRACT-8 (Unwanted)** — IF PythonNet 어댑터가 `apps.gui.module_panel.run_module`, `apps.gui.pipeline_panel.run_partial_pipeline` 또는 그 밖의 Python GUI helper를 실행 경계로 사용하려 하면 THEN 구현·시험은 이를 거부해야 한다. 어댑터는 `pipeline.orchestrator.run_pipeline`과 각 `modules.*.process` 공개 골든 진입점을 직접 미러하고 Python GUI는 대조 선례로만 사용해야 한다.
- **REQ-XSEAM-CONTRACT-9 (Ubiquitous)** — `IXdetEngine`은 FRAME_PROCESS, PIPELINE, SEQUENCE, STACK_METRIC, PROFILE_METRIC, CALIBRATION_BUILD, METRIC_SERIES, NDT_SESSION, TIER family를 typed request/result로 노출해야 한다.
- **REQ-XSEAM-CONTRACT-10 (Ubiquitous)** — 모든 request/result는 `FeatureId`, 실제 Python `EntryPoint[]`, `RunId`, input/Params/CalibSet hash, `AlgorithmAvailability`, 실행별 `EvidenceGrade`, warnings와 engine/golden version을 포함해야 한다.
- **REQ-XSEAM-CONTRACT-11 (Event-Driven)** — WHEN `AlgorithmCatalogManifest`를 생성하면 THEN adapter는 Python 공개 façade와 `REQUIRED_PARAMS`/`required_params(params)`/함수 시그니처를 대조하고 catalog에 없는 연산 또는 Contract가 없는 ACTION/SESSION을 `MANIFEST_CATALOG_MISMATCH`로 보고해야 한다.
- **REQ-XSEAM-CONTRACT-12 (Event-Driven)** — WHEN calibration builder가 실행되면 THEN engine은 source series와 builder metadata를 실제 builder 함수에 전달하고 populated CalibSet payload·provenance·source hash·fit diagnostics를 반환해야 한다.
- **REQ-XSEAM-CONTRACT-13 (Event-Driven)** — WHEN 사용자 제공 실측 input-set이 schema와 required inputs를 만족하면 THEN adapter는 등록 데이터가 아니라는 이유로 실행을 거부하지 않고 `USER_SUPPLIED_UNVERIFIED` evidence로 실행해야 한다.
- **REQ-XSEAM-CONTRACT-14 (Unwanted)** — IF registration data availability와 algorithm implementation availability가 하나의 enum으로 평탄화되거나 합성 데이터 부재가 기능 자체 비활성 사유로 사용되면 THEN Contract 검증은 이를 거부해야 한다.

#### 언어 중립 DTO 최소 계약

| DTO | 필수 필드 |
|---|---|
| `FrameEnvelope` | `Pixel(float32[])`, `Rows`, `Cols`, `Masks(uint8[])`, `NoiseAlpha`, `NoiseSigma`, `Domain`, `ValidationMode`, `History[]`, `EvidenceGrade`, `Warnings[]` |
| `HistoryEntryEnvelope` | `ModuleName`, `ModuleVersion`, `ParamsHash`, `CalibSetId` |
| `TypedValue` | null/bool/int64/double/string 또는 dtype·shape가 명시된 1D/2D numeric array 중 하나. NaN/Infinity와 임의 CLR/Python 객체는 금지 |
| `AlgorithmCatalogEntry` | `FeatureId`, qualified `EntryPoints[]`, exposure, family, input/output kind, required/optional ParamSchema, required CalibKind, GUI owner/command id, TC ids, `AlgorithmAvailability` |
| `AlgorithmCatalogManifest` | schema/version/golden hash, unique ordered `Entries[]`; 실행별 `EvidenceGrade`는 포함하지 않고 result/run manifest가 소유 |
| `ParamsEnvelope` | `Values: IReadOnlyDictionary<string, TypedValue>`, canonical `Sha256` |
| `CalibSetEnvelope` | `Id`, `Kind`, `Resolution`, `PanelId`, `ValidFrom/To`, `Provenance`, `Payload`, payload `Sha256` |
| `PipelineRunRequest` | `RunId`, `Input`, 사용자 선택 순서를 보존한 `Stages`, stage별 `CalibMap`, stage별 `ParamsMap`, `PanelId`, `TimestampUtc`, `Domain`, `ValidationMode` |
| `StageFrameResult` | `Stage`, `Input`, `Output`, `Warnings[]` |
| `PipelineRunResult` | `RunId`, `Output`, 실행 순서의 `Intermediates[]`, `StagesRun`, `Diagnostics`, `Warnings[]` |
| `InputSetEnvelope` | `SchemaVersion`, `DatasetId`, `InputKind`, ordered `Entries(path/hash/sidecar hash)`, resolution/dtype/panel/domain/beam quality, acquisition metadata, evidence grade |
| `SequenceRunRequest/Result` | ordered frames/timestamps, definition/maps, trigger/state policy / ordered frames, state summary, per-frame diagnostics |
| `MetricRequestEnvelope` | single frame/stack/profile/metric-series 중 하나, ROI/landmark/dose metadata, Params, source hashes |
| `MetricResultEnvelope` | axes(name/unit/values), series(name/unit/values), scalars, condition, warnings, source/upstream run hashes |
| `CalibrationBuildRequest/Result` | builder FeatureId, typed source series, panel/resolution/validity/provenance, builder args / populated CalibSet, fit diagnostics, source hashes |
| `NdtSessionRequest/Result` | session id, ordered shots, ROI/SRb/Params, snapshot policy / accumulator state, shot log, target state, report inputs |
| `DqeComposeRequest/Result` | MTF/NPS MetricSeriesEnvelope, compatibility metadata, Params, fixed AxisPolicy / DQE MetricResult, selected/excluded bins, upstream hashes |
| `TierRequest/Result` | capability, `tier_policy`, forced tier, variants, run/timing mode / decision rationale, selected definition, run result 또는 TimingRecord |
| `EngineError` | `RunId`, `FeatureId`, 안정적인 `Code`, Python 예외의 `Type`, 사용자 메시지, `stage`, `details`, `recoverable`, `input_field`. Python traceback은 진단 로그에만 저장 |

예외형→code의 폐쇄형 매핑은 `../SPEC-XGUI-MASTER/algorithm-catalog.md` §3.1을 따른다. source의 17개 공개 예외형이 모두 매핑돼야 하며 예상하지 못한 예외만 `INTERNAL`을 사용할 수 있다.

`Intermediates[i]`는 `StagesRun[i]`의 출력이어야 한다. 첫 stage의 before는 request input, 이후 stage의 before는 직전 intermediate로 결정하며, UI가 이를 재계산하거나 stage를 다시 실행하지 않는다. Contract의 canonical Params/CalibSet hash는 SPEC-XGUI-MASTER foundation §3.1을 따른다.

### REQ-XSEAM-COMPOSE — 다단계 조합 검증: 개별 → 부분집합/전체 → 중간 프레임 · 거부 가드 (SPEC-VIEWER-001 RUN-1/RUN-2 C# 미러, C-09/C-11/C-20, XDET-TC-089~093)

- **REQ-XSEAM-COMPOSE-1 (Event-Driven)** — WHEN 사용자가 단일 처리 스테이지를 선택하고 그 스테이지 고유의 `CalibSet`과 `Params`를 공급하면, THEN UI는 그 스테이지를 `IXdetEngine`을 거쳐 개별 구동하고 그 스테이지의 입력/출력/diff/마스크 결과를 표시해야 한다(스테이지마다 구별되는 캘리브레이션 입력; 모든 수치는 골든 엔진 산출 — C-09; SPEC-VIEWER-001 REQ-VIEW-RUN-1의 C# 미러).
- **REQ-XSEAM-COMPOSE-2 (Event-Driven)** — WHEN 사용자가 정렬된 부분집합(2개 이상) 또는 전체 스테이지 집합을 선택하고 각 스테이지가 고유의 `CalibSet`·`Params`를 지니면, THEN UI는 그 정렬된 부분집합에 대한 단일 심 파이프라인 실행(REQ-XSEAM-CONTRACT-6 진입점)을 요청하고 조합 출력과 각 스테이지의 전/후를 함께 표시하여, 개별 확인된 스테이지 집합이 하나의 조합 결과로 검증되어야 한다(SPEC-VIEWER-001 REQ-VIEW-RUN-2의 C# 미러).
- **REQ-XSEAM-COMPOSE-3 (Event-Driven)** — WHEN 조합 부분집합 또는 전체 실행이 검증 모드(입력 `XFrame.validation_mode=True`)로 요청되면(REQ-XSEAM-CONTRACT-6 진입점이 그 단일 패스의 중간 프레임 생산자), THEN 심은 실행된 모든 스테이지의 중간 프레임(`XFrame.intermediates`)을 그 단일 패스에서 반환하고, UI는 추가 실행을 발행하지 않고 각 스테이지의 전/후를 스크럽할 수 있어야 한다.
- **REQ-XSEAM-COMPOSE-4 (Unwanted)** — IF 요청된 스테이지 부분집합이 `CANONICAL_ORDER`의 부분수열이 아니거나(→ `PipelineOrderError`) 선택된 스테이지 중 하나라도 해상도·panel_id가 일치하는 `CalibSet`을 결여하면(→ `CalibrationError`), THEN 그 실행은 오케스트레이터의 명시적 오류로 거부되고 어떤 기본 캘리브레이션도 대체되지 않아야 한다(SWR-000-2 + SWR-000-5를 심을 통해 보존).
- **REQ-XSEAM-COMPOSE-5 (Unwanted)** — IF C# UI 또는 어댑터가 어떤 스테이지 출력을 스스로 계산하거나, 스테이지를 스스로 정렬·조합하거나, 결여된 스테이지별 캘리브레이션을 합성하면, THEN 이는 거부되어야 한다(조합 권한은 Python 오케스트레이터에, 모든 DSP는 골든 엔진에 — C-09/C-11, 골든 읽기 전용, C-20).
- **REQ-XSEAM-COMPOSE-6 (Event-Driven)** — WHEN Python이 `PipelineOrderError`, `CalibrationError` 또는 모듈 고유 오류를 반환하면 THEN 어댑터는 오류형·stage·누락 Params/CalibSet context를 `EngineError`에 보존하고, UI는 일반 실패 문자열로 평탄화하거나 부분 출력을 성공으로 커밋하지 않아야 한다.

### REQ-XSEAM-DQE — 골든 소유 DQE 합성

- **REQ-XSEAM-DQE-1 (Event-Driven)** — WHEN `DqeComposeRequest`가 MTF·NPS 결과를 참조하면 THEN engine은 axis가 유한·엄격 증가이고 unit=`lp/mm`, pixel pitch·domain·beam quality가 호환되는지 검증해야 한다.
- **REQ-XSEAM-DQE-2 (Ubiquitous)** — engine은 `AxisPolicy=NPS_BINS_WITHIN_MTF_SUPPORT_V1`로 MTF support 안의 NPS bin만 선택하고 각 bin마다 실제 `metrics.mtf.mtf_value_at`을 호출한 뒤 실제 `metrics.dqe.compute_dqe`를 호출해야 한다.
- **REQ-XSEAM-DQE-3 (Unwanted)** — IF target frequency가 MTF support 밖이면 THEN endpoint clamp나 외삽으로 MTF를 만들지 않고 해당 bin을 제외하며 index/reason을 결과에 기록해야 한다.
- **REQ-XSEAM-DQE-4 (Unwanted)** — IF WPF 또는 C# ViewModel이 interpolation·axis resampling·DQE 공식을 계산하면 THEN 정적 검사와 음성 대조 시험은 실패해야 한다.
- **REQ-XSEAM-DQE-5 (Event-Driven)** — WHEN DQE가 완료되면 THEN provenance는 `mtf_value_at`, `compute_dqe`, AxisPolicy, upstream MTF/NPS run/hash, 선택/제외 bin, Params hash를 모두 기록해야 한다.

### REQ-XSEAM-TIER — tier 판단·실행·구조 timing

- **REQ-XSEAM-TIER-1 (Event-Driven)** — WHEN capability와 injected `tier_policy`가 제공되면 THEN engine은 `pipeline.tier.decide_tier`를 호출해 detected/chosen tier, forced 여부, rationale를 반환해야 한다.
- **REQ-XSEAM-TIER-2 (Unwanted)** — IF capability/policy가 없거나 강제 tier가 detected ceiling을 초과하거나 variant가 없으면 THEN silent default/fallback 없이 `TierDecisionError` 의미를 보존해 거부해야 한다.
- **REQ-XSEAM-TIER-3 (Event-Driven)** — WHEN tier 실행을 요청하면 THEN engine은 `select_pipeline`과 `run_tier`를 통해 기존 `run_pipeline` 게이트를 그대로 사용해야 한다.
- **REQ-XSEAM-TIER-4 (Event-Driven)** — WHEN timing을 요청하면 THEN engine은 `time_tier`의 cold/warm/runs/median을 반환하되 P1 GUI는 절대 시간 합격·실패를 계산하지 않아야 한다.

### REQ-XSEAM-SESSION — 상태형 연산

- **REQ-XSEAM-SESSION-1 (Ubiquitous)** — 각 Lag run은 fresh `LagCorrector`를 사용하고 암묵적으로 이전 run state를 재사용하지 않아야 한다.
- **REQ-XSEAM-SESSION-2 (Event-Driven)** — WHEN 사용자가 명시 snapshot/restore를 요청하면 THEN `LagCorrector.serialize_state/load_state` 결과와 source run/state hash가 session event log에 기록되어야 한다.
- **REQ-XSEAM-SESSION-3 (Event-Driven)** — WHEN NDT shot이 수락되면 THEN `SNRnAccumulator.update` 뒤 current/shot_log/target_reached/target_frame_index를 typed result로 반환해야 하며, 거부된 shot은 accumulator state를 바꾸지 않아야 한다.

### REQ-XSEAM-COVERAGE — 전수 계약 완결성

- **REQ-XSEAM-COVERAGE-1 (Ubiquitous)** — `AlgorithmCatalogCoverageTests`는 Python 공개 대상 연산, catalog FeatureId, `AlgorithmCatalogManifest`, Contract method/family, GUI action/session, 중앙 TC의 6개 집합을 비교해 누락·중복·orphan을 0건으로 유지해야 한다.
- **REQ-XSEAM-COVERAGE-2 (Unwanted)** — IF ACTION/SESSION FeatureId가 문서에만 있고 실제 `IXdetEngine` 호출 경로가 없거나 GUI control이 mock/fake result를 반환하면 THEN 완료 판정을 거부해야 한다.

## Exclusions (What NOT to Build)

- **C++ 엔진 이식 없음(SPEC-XSEAM Stage 2)** — 본 SPEC은 조합 심 진입점과 그 C# 소비를 계획·명세할 뿐, C++/C ABI 네이티브 엔진(`NativeXdetEngine`)이나 네이티브 조합 커널을 구현하지 않는다. C++ 이식은 XSEAM Stage 2(P2) 범위이며, 조합 경로도 XDET-TC-020/021 동일성 프레임으로 그때 게이트된다(SPEC-XSEAM-001 REQ-XSEAM-FORWARD 승계).
- **비-offset 수치 fidelity envelope 없음** — 조합 fidelity 단언은 트랜스포트 정확성(관측 delta = 0/bit-동일) 확인이다. offset 외 각 스테이지의 수치 골든 fidelity 특성화(스테이지별 ±1 LSB 예산 소진, 정밀 EV 대조)는 P2 C++ 재계산 몫이며, ±1 LSB envelope는 그때를 위한 예약분이다(P1.5 트랜스포트가 소비하지 않음).
- **성능·마샬링 최적화 없음** — 대용량 3072² 프레임의 스테이지별 중간 프레임 마샬링 비용/스루풋 최적화는 범위 밖이다(트랜스포트 정확성·조합 정합성 증명이 목적; SPEC-XSEAM-001의 IPC/RPC 폴백 범위로 이연).
- **골든 모델 변경 없음** — `pipeline/orchestrator.py`(`run_pipeline`·`PipelineDefinition`·`CANONICAL_ORDER`·`calib_kind_for_stage`·`_calibration_gate`)·`pipeline/sequence.py`·`modules/`·`common/`·`metrics/`는 동결 오라클로 편집하지 않는다. 심은 이들을 읽기 전용으로 소비한다(REQ-XSEAM-COMPOSE-5).
- **C#에서의 조합·DSP 재구현 없음** — 스테이지 순서/조합 결정은 `PipelineDefinition`(오케스트레이터)에, 모든 DSP는 골든에 남는다. C#은 미러 DTO 전달·표시만 한다.
- **신규 파이프라인 스테이지·CalibKind 없음** — 조합은 기존 `CANONICAL_ORDER`·기존 CalibKind로만 이뤄진다. 본 SPEC은 스테이지나 kind를 신설하지 않는다.
- **정본 수치 검증 없음(QUARANTINE)** — SAMPLE 실측(에드로지) 조합 구동은 sanity(유한·비퇴화·구조) 확인이며 수치 골든/EV 임계 도출·튜닝·적합에 쓰지 않는다(이슈 #29). 정본 수치 조합 검증은 정본 지침세트(이슈 #33) 도착 후 별건이다.
- **Gen 2·배포 없음** — DL/ADR, 웹 서버·다중 사용자·배포는 범위 밖(SPEC-XSEAM-001 Exclusions 승계).

## 확정 결정 (v0.5.1)

1. WPF 조합 UI는 기존 `apps/xdet-console/src/Xdet.Console.App/`을 확장한다.
2. 등록 SAMPLE 조합 sanity는 offset→gain→defect 3스테이지까지 수행한다. lag는 비정본 placeholder 라벨, 나머지는 합성/#33 라벨을 유지한다.
3. fidelity는 최종 XFrame뿐 아니라 validation mode의 모든 stage intermediate를 `diff_frames`로 대조한다.
4. 현재 `IXdetEngine.RunPipeline`은 offset→gain 고정 슬라이스이므로, 본 계약의 완료에는 ordered stage subset·CalibMap·ParamsMap·intermediates를 수용하는 generic overload 또는 동등한 언어 중립 진입점이 필요하다.
5. generic 진입점은 기존 고정 offset→gain overload를 호환용으로 둘 수 있으나, 8그룹 GUI는 `PipelineRunRequest` 기반 계약만 사용한다.
6. Python GUI helper는 시험 선례일 뿐 어댑터 실행 의존성이 아니다.
7. 파이프라인만이 아니라 catalog의 모든 ACTION/SESSION은 9개 typed family 중 하나로 `IXdetEngine`을 경유한다.
8. DQE는 비활성 기능이 아니다. 기존 골든 `mtf_value_at`과 `compute_dqe`를 engine-owned 고정 축 정책으로 합성한다.
9. `pipeline.tier`의 decide/select/run/time과 lag/NDT state는 공통 typed 계약으로 구현한다.
10. 등록 데이터 가용성과 알고리즘 구현 여부를 분리하며 strict 사용자 제공 input-set 실행을 지원한다.

## v0.5.1 shared public operation closure

| Python EntryPoint | Contract 역할 | TC |
|---|---|---|
| `modules.registry.default_registry` | process manifest source | 161 |
| `pipeline.orchestrator.PipelineDefinition.full` | full definition/introspection | 162 |
| `pipeline.orchestrator.calib_kind_for_stage` | stage CalibKind manifest | 161~162 |
| `pipeline.orchestrator.run_pipeline` | PIPELINE handler | 162 |
| `pipeline.sequence.run_sequence` | SEQUENCE handler | 162 |
| `pipeline.sequence.FBTrigger.request` | trigger session port | 162 |
| `pipeline.sequence.FBTrigger.confirm` | trigger session port | 162 |
| `pipeline.sequence.NoOpFBTrigger.request` | offline trigger session | 162 |
| `pipeline.sequence.NoOpFBTrigger.confirm` | offline trigger session | 162 |
| `pipeline.tier.decide_tier` | TIER decision handler | 163 |
| `pipeline.tier.select_pipeline` | TIER selection handler | 163 |
| `pipeline.tier.run_tier` | TIER run handler | 163 |
| `pipeline.tier.time_tier` | TIER timing handler | 163 |

이 표와 algorithm catalog의 qualified EntryPoint 집합이 어긋나면 Contract coverage test가 실패한다.
