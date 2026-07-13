---
id: SPEC-XGUI-MASTER-ALGORITHM-CATALOG
version: 0.5.1
status: planned
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-13
updated: 2026-07-13
author: codex
labels: [xgui, algorithm-catalog, traceability, wpf, pythonnet]
---

# SPEC-XGUI-MASTER — 전체 알고리즘 GUI 계약 카탈로그

## 1. 목적과 완료 정의

이 문서는 저장소의 공개 처리·지표·캘리브레이션·조합 연산이 GUI 설계에서 누락되지 않게 하는 구현 계약이다. 단순히 탭 이름이나 Python 파일을 나열하지 않는다. 모든 대상 연산은 다음 항목을 가져야 한다.

1. 안정적인 `FeatureId`와 실제 Python `EntryPoint`
2. GUI 노출 방식(`ACTION`, `SESSION`, `DERIVED`, `INFRASTRUCTURE`)
3. 입력 family와 typed request/result DTO
4. Params 권위 소스와 CalibSet 요구
5. 소유 GUI 그룹과 자동화 예정 TC
6. 실행 가능성과 검증 증거 등급의 분리
7. 원본 Python 예외형과 손실 없는 typed error 분류

대상 집합은 서로 다른 세 집합으로 고정한다. `TARGET_OPERATION_SET`은 `modules` 22개, `metrics` 30개, `pipeline` 12개인 공개 대상 64개다. `SAMPLE_HELPER_SET`은 명시 whitelist인 `scripts.ingest_edrogi.build_{offset,gain,defect}_calibset` 3개다. `COMMON_INFRASTRUCTURE_SET`은 `common/equivalence.py` 2개, `common/io.py` 1개, `CalibSet.validate/load/save` 3개인 6개다. 따라서 구현 범위 표기는 **target 67개(64+3), common infrastructure 6개, catalog qualified callable 총 73개**로 한다. 데이터 carrier의 단순 필드 접근은 별도 버튼을 만들지 않지만 세션/파생 결과 DTO에 반드시 보존한다. 새 공개 연산이 추가됐는데 이 카탈로그에 분류되지 않으면 Contract 빌드와 GUI 완료 판정은 실패해야 한다(XDET-TC-160).

## 2. 노출 등급과 상태 모델

| 노출 | 의미 | GUI 계약 |
|---|---|---|
| `ACTION` | 사용자가 입력·Params·CalibSet을 공급하고 직접 실행 | 명시적 실행 control, typed request/result, 오류·취소·export |
| `SESSION` | 여러 호출 사이 상태를 유지하는 워크플로 | session id, ordered event log, snapshot/restore, accepted/rejected transition |
| `DERIVED` | ACTION/SESSION 결과의 진단·곡선·보조 산출 | 별도 Python 직접 호출 또는 부모 엔진 호출 안에서 생산하고 결과 DTO에 포함; UI 재계산 금지 |
| `INFRASTRUCTURE` | load, orchestration, tier, equivalence 같은 공통 실행 기반 | 공통 셸 또는 실행 설정에서 사용하며 숨은 우회 경로 금지 |

`AlgorithmAvailability`와 실행별 `EvidenceGrade`는 서로 다른 축이다.

- `AlgorithmAvailability`: `IMPLEMENTED`, `NOT_IMPLEMENTED`, `PREREQUISITE_MISSING`, `UNSUPPORTED`
- `EvidenceGrade`: `SYNTHETIC_VERIFIED`, `SAMPLE_SANITY`, `USER_SUPPLIED_UNVERIFIED`, `GUIDING_CANDIDATE`, `GOLDEN_APPROVED`

등록 실측 데이터가 없다는 이유로 구현된 알고리즘을 실행 불가로 표시하지 않는다. 알고리즘 구현 여부와 현재 실행에 공급된 데이터의 증거 수준을 각각 표시한다. 반대로 합성 시험이 통과했다는 이유로 실측 정본 검증 완료를 주장하지 않는다.

## 3. 실행 family와 언어 중립 DTO

| Family | Request 핵심 필드 | Result 핵심 필드 |
|---|---|---|
| `FRAME_PROCESS` | `RunId`, `FeatureId`, `FrameEnvelope`, `CalibSetEnvelope`, `ParamsEnvelope`, context | input/output frame, diff, masks, history, warnings |
| `PIPELINE` | ordered stages, frame, stage별 CalibMap/ParamsMap, validation mode | final frame, ordered intermediates, stage diagnostics |
| `SEQUENCE` | ordered frames, timestamps, definition, trigger policy, state policy | ordered outputs, sequence state summary, per-frame diagnostics |
| `STACK_METRIC` | ordered frame stack, optional ROI/dose metadata, Params | axes, series, scalars, condition, warnings |
| `PROFILE_METRIC` | profile values/unit/spacing, landmark DTO, Params | MetricResult envelope 또는 typed NDT result |
| `CALIBRATION_BUILD` | source stack/series, panel/resolution/validity/provenance, builder args | populated CalibSet envelope, fit diagnostics, source hashes |
| `METRIC_SERIES` | axis/series/unit/provenance envelopes, Params | composed metric series and invalid-bin diagnostics |
| `NDT_SESSION` | session id, ordered shots, ROI/SRb/Params, snapshot policy | accumulator state, shot log, target state, report inputs |
| `TIER` | capability, injected tier policy, forced tier, variant map, run input | decision, selected definition, run result or timing record |

Contract 바깥으로 `PyObject`, `dynamic`, 임의 `object` payload를 노출하지 않는다. 가변 데이터는 `TypedValue`의 닫힌 kind 집합과 명시 shape/dtype/unit을 사용한다.

### 3.1 typed error 계약

모든 실패 결과는 `EngineError(code, python_type, feature_id, stage, message, details, run_id, recoverable, input_field)`로 변환한다. `python_type`과 원래 메시지를 보존하고, 사용자가 고칠 수 있는 필드·stage를 `details`에 구조화한다. UI는 오류를 성공/빈 결과로 바꾸거나 기본 Params·CalibSet으로 재시도하지 않는다. 예상하지 못한 예외만 `INTERNAL`로 분류하며 traceback은 진단 로그에만 남기고 사용자 화면에는 노출하지 않는다.

| Python 예외형 | EngineError code | recoverable | GUI 동작 |
|---|---|---:|---|
| `CalibSchemaError`, `DefectMapSchemaError` | `CALIBRATION_INVALID` | true | kind/schema/shape/panel/domain 필드 강조, 실행 차단 |
| `LagCalibError`, `LagIRFCalibrationError` | `CALIBRATION_INVALID` | true | LAG payload/IRF 원인과 입력 경로 표시 |
| `NoiseModelCalibrationError`, `ScatterKernelCalibrationError` | `CALIBRATION_BUILD_FAILED` | true | source series와 builder diagnostics 표시 |
| `CalibrationError` | `CALIBRATION_MISSING_OR_MISMATCHED` | true | 누락 stage와 기대 kind 표시 |
| `PipelineOrderError` | `PIPELINE_ORDER_INVALID` | true | 요청 순서와 canonical order 표시 |
| `DenoiseError`, `GridError`, `MseError`, `VirtualGridError`, `WindowError` | `ALGORITHM_INPUT_INVALID` | true | feature/stage/field와 원본 예외형 표시 |
| `LagStateError` | `SESSION_STATE_INVALID` | true | source run/state hash와 허용 전이 표시 |
| `MetricReadError` | `METRIC_INPUT_INVALID` | true | axis/unit/shape/finite 조건 표시 |
| `FBTriggerError` | `SEQUENCE_TRIGGER_INVALID` | true | trigger index/policy 조건 표시 |
| `TierDecisionError` | `TIER_DECISION_INVALID` | true | capability/policy/forced tier/variant 원인 표시 |
| 위 목록 밖의 검증 `ValueError`/`RuntimeError` | `ENGINE_VALIDATION_FAILED` | false | 원본 type/message 보존, 자동 재시도 금지 |
| 예상하지 못한 예외 | `INTERNAL` | false | run_id와 진단 로그 참조만 표시, 결과 commit 금지 |

취소는 Python 예외형에 덮어쓰지 않는다. 사용자가 취소한 `run_id`는 UI 상태를 `Canceled`로 확정하고, 이후 반환한 성공/실패 DTO는 진단 로그에는 남길 수 있지만 최신 결과·artifact·session state에 commit하지 않는다.

## 4. 처리 모듈 전수 매핑

| FeatureId | Python EntryPoint | 노출 | Family / 결과 | Params·Calib 권위 | GUI / TC |
|---|---|---|---|---|---|
| `proc.offset` | `modules.offset.process` | ACTION | FRAME_PROCESS / XFrame | `REQUIRED_PARAMS`; OFFSET | Calibration / 101 |
| `proc.gain` | `modules.gain.process` | ACTION | FRAME_PROCESS / XFrame | `REQUIRED_PARAMS`; GAIN | Calibration / 101 |
| `proc.defect` | `modules.defect.process` | ACTION | FRAME_PROCESS / XFrame | `REQUIRED_PARAMS`; DEFECT | Calibration / 101 |
| `proc.lag` | `modules.lag.LagCorrector.process` | SESSION | SEQUENCE / XFrame[] | `REQUIRED_PARAMS`; LAG | Lag / 104~105 |
| `proc.line-noise` | `modules.line_noise.process` | ACTION | FRAME_PROCESS / XFrame | `REQUIRED_PARAMS`; OTHER | Line/Sat/Geo / 112 |
| `proc.saturation` | `modules.saturation.process` | ACTION | FRAME_PROCESS / XFrame | `REQUIRED_PARAMS`; OTHER | Line/Sat/Geo / 113 |
| `proc.geometry` | `modules.geometry.process` | ACTION | FRAME_PROCESS / XFrame | `REQUIRED_PARAMS`; GEOMETRY | Line/Sat/Geo / 114 |
| `proc.grid` | `modules.grid.process` | ACTION | FRAME_PROCESS / XFrame | `REQUIRED_PARAMS`; OTHER | Grid / 136~137 |
| `proc.virtual-grid` | `modules.virtual_grid.process` | ACTION | FRAME_PROCESS / XFrame | `REQUIRED_PARAMS`; SCATTER | Grid / 138 |
| `proc.denoise` | `modules.denoise.process` | ACTION | FRAME_PROCESS / XFrame | `required_params(params)`; NOISE | Denoise / 120~125 |
| `proc.mse` | `modules.mse.process` | ACTION | FRAME_PROCESS / XFrame | `required_params(params)`; OTHER | Enhancement / 128~129 |
| `proc.window` | `modules.window.process` | ACTION | FRAME_PROCESS / XFrame | `REQUIRED_PARAMS`; OTHER | Enhancement / 130~131 |

## 5. 캘리브레이션 builder 전수 매핑

| FeatureId | Python EntryPoint | 입력 / 결과 | GUI / TC |
|---|---|---|---|
| `calib.defect-map` | `metrics.defect_map.build_defect_map` | ordered dark+flat stacks + builder metadata / DEFECT CalibSet | Calibration / 097 |
| `calib.defect-morphology` | `metrics.defect_map.classify_morphology` | defect candidate map + morphology thresholds / class map | Calibration derived / 097 |
| `calib.lag-irf` | `metrics.lag_irf.fit_lag_irf` | `StepResponse[]` / LAG CalibSet | Calibration / 098 |
| `calib.noise-model` | `metrics.noise_model.fit_noise_model` | `DoseLevel[]` / NOISE CalibSet | Calibration / 099 |
| `calib.scatter-parametric` | `metrics.scatter_kernel.build_scatter_kernel` | thickness/kV + builder args / SCATTER CalibSet | Calibration, Grid / 100, 139 |
| `calib.scatter-sample-fit` | `metrics.scatter_kernel.fit_scatter_kernel_from_samples` | primary/scatter arrays + fixed sigmas / SCATTER CalibSet | Calibration, Grid / 100, 140 |
| `calib.sample-offset` | `scripts.ingest_edrogi.build_offset_calibset` | registered edrogi MasterDark / fixed SAMPLE OFFSET CalibSet | Calibration SAMPLE preset / 096 |
| `calib.sample-gain` | `scripts.ingest_edrogi.build_gain_calibset` | registered edrogi CalSet flat / fixed SAMPLE GAIN CalibSet | Calibration SAMPLE preset / 096 |
| `calib.sample-defect` | `scripts.ingest_edrogi.build_defect_calibset` | registered edrogi BPM / fixed SAMPLE DEFECT CalibSet | Calibration SAMPLE preset / 096 |

마지막 세 helper는 `SAMPLE_PANEL_ID`, 고정 validity/domain/provenance를 사용하는 `scripts/ingest_edrogi.py` 전용 plumbing이다. 등록 edrogi preset의 구조 sanity에만 사용하고 일반 사용자 dark/flat/BPM builder로 노출하지 않으며 결과 evidence는 `SAMPLE_SANITY`다.

범용 offset·gain·geometry map을 raw acquisition에서 새로 생성하는 builder는 현재 golden에 존재하지 않는다. GUI는 해당 CalibSet을 schema/hash/provenance 검증 후 import해 사용할 수 있어야 하며, 존재하지 않는 범용 builder를 C#에서 창작하지 않는다. builder 부재는 처리 알고리즘 비활성 사유가 아니라 입력 획득 경로의 제약이다.

## 6. 지표·NDT 전수 매핑

| FeatureId | Python EntryPoint | 노출 / 입력 | GUI / TC |
|---|---|---|---|
| `metric.mtf` | `metrics.mtf.compute_mtf` | ACTION / edge XFrame + ROI Params | Metrics / 154 |
| `metric.mtf-at` | `metrics.mtf.mtf_value_at` | DERIVED / MTF MetricResult + frequency | Metrics, DQE engine composition / 155~156 |
| `metric.nps` | `metrics.nps.compute_nps` | ACTION / ordered flat XFrame stack | Metrics / 154 |
| `metric.line-noise` | `metrics.nps.detect_line_noise` | ACTION / ordered flat XFrame stack | Metrics / 154 |
| `metric.dqe` | `metrics.dqe.compute_dqe` | ACTION / engine-aligned frequency+MTF+NNPS series | Metrics / 155 |
| `metric.dqe-at` | `metrics.dqe.dqe_value_at` | DERIVED / DQE MetricResult + frequency | Metrics / 156 |
| `metric.defect-stats` | `metrics.defect_stats.classify_defects` | ACTION / ordered dark+flat stacks + optional truth map | Metrics / 154 |
| `metric.lag-first-frame` | `metrics.lag.compute_first_frame_lag` | ACTION / ordered frame sequence | Lag / 106 |
| `metric.ghost-cnr` | `metrics.lag.compute_ghost_cnr` | ACTION / ghost frame + foreground/background ROI | Lag / 107 |
| `ndt.duplex-srb` | `metrics.ndt.read_duplex_srb` | ACTION / profile + `WirePair[]` | NDT / 144 |
| `ndt.snr` | `metrics.ndt.compute_snr` | ACTION / frame + ROI | NDT / 145 |
| `ndt.snrn` | `metrics.ndt.compute_snrn` | ACTION / frame + ROI + SRb | NDT / 145 |
| `ndt.accumulator` | `metrics.ndt.SNRnAccumulator.update` | SESSION / ordered shot stream | NDT / 146 |
| `ndt.thickness` | `metrics.ndt.correct_thickness` | ACTION / XFrame | NDT / 147 |
| `ndt.single-wire` | `metrics.ndt.read_single_wire_iqi` | ACTION / profile + `WireElement[]` | NDT / 148 |
| `ndt.iqi-report` | `metrics.ndt.build_iqi_report` | ACTION / `IqiShot[]` | NDT / 148 |

## 7. 조합·tier·공통 검증 전수 매핑

| FeatureId | Python EntryPoint | 노출 / 계약 | GUI / TC |
|---|---|---|---|
| `orch.pipeline` | `pipeline.orchestrator.run_pipeline` | INFRASTRUCTURE / ordered subset, CalibMap, ParamsMap | Shared / 162 |
| `orch.pipeline-full` | `pipeline.orchestrator.PipelineDefinition.full` | DERIVED / `post` 포함 사실을 보존하고 실행 가능한 등록 집합은 manifest가 제공 | Shared / 162 |
| `orch.calib-kind` | `pipeline.orchestrator.calib_kind_for_stage` | DERIVED / catalog manifest CalibKind | Shared / 161 |
| `orch.sequence` | `pipeline.sequence.run_sequence` | INFRASTRUCTURE / fresh state per run | Lag / 104, Shared / 162 |
| `orch.trigger-port` | `pipeline.sequence.FBTrigger.request`, `pipeline.sequence.FBTrigger.confirm` | SESSION / hardware port abstraction | Lag / 105 |
| `orch.noop-trigger` | `pipeline.sequence.NoOpFBTrigger.request`, `pipeline.sequence.NoOpFBTrigger.confirm` | SESSION / offline deterministic path | Lag / 105 |
| `orch.tier-decide` | `pipeline.tier.decide_tier` | ACTION / capability + `tier_policy` + optional downgrade | Shared / 163 |
| `orch.tier-select` | `pipeline.tier.select_pipeline` | DERIVED / Tier→PipelineDefinition | Shared / 163 |
| `orch.tier-run` | `pipeline.tier.run_tier` | ACTION / selected variant through run_pipeline | Shared / 163 |
| `orch.tier-time` | `pipeline.tier.time_tier` | ACTION / cold+warm timing structure, 절대 성능 판정 없음 | Shared / 163 |
| `validation.frame-diff` | `common.equivalence.diff_frames` | INFRASTRUCTURE / typed equivalence result | Shared / 165 |
| `validation.path-compare` | `common.equivalence.compare_paths` | INFRASTRUCTURE / stage path equivalence | Shared / 165 |
| `io.raw-load` | `common.io.load_raw_frame` | INFRASTRUCTURE / raw+sidecar strict load | Shared / 165 |
| `calib.schema` | `common.calibset.CalibSet.validate`, `common.calibset.CalibSet.load`, `common.calibset.CalibSet.save` | INFRASTRUCTURE / schema, hash, provenance | Shared / 165 |

## 8. 공개 지원 연산의 귀속

다음 공개 연산은 독립 사용자 알고리즘 버튼이 아니라 부모 실행의 파생 진단 또는 세션 상태다. 카탈로그에서 제거하거나 UI에서 재구현하지 않는다.

| Python EntryPoint | 부모 FeatureId | 결과 운반 |
|---|---|---|
| `modules.denoise.required_params` | `proc.denoise` | `AlgorithmCatalogManifest` required-key set |
| `modules.mse.required_params` | `proc.mse` | `AlgorithmCatalogManifest` required-key set |
| `modules.grid.analyze` | `proc.grid` | `GridAnalysis` typed diagnostics |
| `modules.grid.notch_gain_1d` | `proc.grid` | notch-response series |
| `modules.virtual_grid.estimate_scatter` | `proc.virtual-grid` | scatter estimate preview/diagnostics |
| `modules.window.build_gsdf_lut` | `proc.window` | GSDF axis/series |
| `modules.window.remap_to_pvalue` | `proc.window` | P-value preview/result metadata |
| `modules.lag.LagCorrector.serialize_state` | `proc.lag` | sequence state snapshot |
| `modules.lag.LagCorrector.load_state` | `proc.lag` | explicit restore event; hidden implicit reuse 금지 |
| `metrics.mtf.estimate_edge_angle` | `metric.mtf` | MTF diagnostics |
| `metrics.ndt.SNRnAccumulator.shot_log` | `ndt.accumulator` | ordered shot DTO list |
| `metrics.ndt.SNRnAccumulator.target_reached` | `ndt.accumulator` | target state |
| `metrics.ndt.SNRnAccumulator.target_frame_index` | `ndt.accumulator` | target transition index |
| `metrics.ndt.SNRnAccumulator.current` | `ndt.accumulator` | current aggregate DTO |
| `modules.registry.default_registry` | `orch.pipeline` | process callable registry manifest; UI 직접 호출 금지 |
| `metrics.result.MetricResult.get` | 모든 metric FeatureId | typed scalar/axis/series 조회; UI key 추측 금지 |
| `metrics.result.require_param` | 모든 metric FeatureId | Params 필수값 검증과 typed 오류 |
| `metrics.result.metric_view` | 모든 metric FeatureId | read-only metric payload view; 결과 DTO 직렬화 경계 |

이 표의 연산도 실제 golden 호출 또는 반환 운반을 자동 시험으로 검증한다. `required_params`, state snapshot/restore, GSDF/P-value, grid/scatter 진단처럼 사용자 작업 흐름에 필요한 연산은 부모 화면의 명시 sub-command/diagnostic으로 노출한다. 독립 top-level 탭이 없다는 뜻이지 호출을 생략하거나 C#에서 다시 계산해도 된다는 뜻이 아니다.

## 9. DQE engine-owned 합성 정책

`compute_dqe`는 같은 shape의 common frequency axis, MTF, NNPS를 요구한다. MTF와 NPS의 자연 출력축은 서로 다르므로 GUI가 직접 보간하면 안 된다. target 구현은 기존 골든 공개 연산만 다음 순서로 호출한다.

1. `DqeComposeRequest`는 MTF·NPS `MetricSeriesEnvelope`와 각각의 source/run/Params/input hash, pixel pitch, axis unit을 받는다.
2. engine은 두 축이 유한·엄격 증가이고 단위가 `lp/mm`, pixel pitch·domain·beam quality가 호환되는지 검증한다.
3. 고정 `AxisPolicy=NPS_BINS_WITHIN_MTF_SUPPORT_V1`에 따라 MTF 최소/최대 주파수 범위 안의 NPS bin만 선택한다. 범위 밖 bin은 보간·외삽하지 않고 제외 index를 기록한다.
4. 각 선택 NPS 주파수에서 기존 골든 `metrics.mtf.mtf_value_at(mtf_result, f)`을 호출해 MTF 값을 얻는다. C#/WPF는 `np.interp` 또는 동등 산술을 구현하지 않는다.
5. 선택된 NPS 축, 골든이 산출한 MTF, 원래 NNPS를 `metrics.dqe.compute_dqe`에 전달한다.
6. 결과는 `AxisPolicy`, 선택/제외 bin, 두 upstream run id/hash, `mtf_value_at`와 `compute_dqe` entry point를 provenance에 기록한다.

이 경로가 구현되면 `metric.dqe`의 `AlgorithmAvailability`는 `IMPLEMENTED`가 된다. 등록 슬랜티드-엣지 데이터가 없다는 사실은 실행 가능성을 낮추지 않고 실행별 `EvidenceGrade`를 제한한다. 합성 MTF/NPS 조합은 `SYNTHETIC_VERIFIED`, 사용자가 제공한 실측 입력은 승인 전 `USER_SUPPLIED_UNVERIFIED`, #33 정본 승격 후에만 `GUIDING_CANDIDATE` 또는 `GOLDEN_APPROVED`다.

## 10. 입력 데이터셋 manifest

모든 ACTION/SESSION 입력은 `xdet.input-set/1.0` manifest를 사용한다. 필수 공통 필드는 `schema_version`, `dataset_id`, `input_kind`, ordered `entries(path, sha256, sidecar_sha256)`, resolution, dtype, panel_id, domain, beam_quality, acquisition metadata, evidence grade다.

| input_kind | 추가 필드 |
|---|---|
| `single-frame` | frame role, optional ROI |
| `ordered-stack` | frame order, stack role(dark/flat/NPS/dose), dose level |
| `sequence` | timestamp/frame interval, exposure phase, trigger policy |
| `profile` | sample spacing/unit, orientation, landmark DTO(`WirePair`/`WireElement`) |
| `calibration-series` | StepResponse/DoseLevel/primary-scatter schema와 builder metadata |
| `metric-series` | axis name/unit/values hash, series name/unit/values hash, upstream run manifest |

등록 SAMPLE manifest(`data/edrogi/manifest.json`)의 `usage=sample-plumbing`은 `SAMPLE_SANITY`로만 해석한다. 사용자가 선택한 외부 실측 폴더도 동일 schema로 검증할 수 있어야 하며, 등록세트가 아니라는 이유로 실행을 막지 않고 `USER_SUPPLIED_UNVERIFIED`로 표시한다.

## 11. 중앙 TC와 자동 완결성 검사

- 그룹 TC 096부터 159까지는 각 도메인 동작을 검증한다.
- 공통 TC 160~167은 catalog completeness, manifest/DTO, pipeline, tier, DQE 합성, IO/equivalence, evidence separation, 전 기능 도달 가능성을 검증한다.
- `AlgorithmCatalogCoverageTests`는 Python AST로 세 집합을 독립 추출한다: `TARGET_OPERATION_SET=64`, `SAMPLE_HELPER_SET=3`, `COMMON_INFRASTRUCTURE_SET=6`. 각각 catalog와 차이 0이어야 하며 세 집합의 합집합인 `CATALOG_CALLABLE_SET=73`도 중복 없이 `AlgorithmCatalogManifest`와 일치해야 한다.
- 새/삭제 연산, whitelist 밖 script 노출, 집합 간 중복 EntryPoint, 중복 FeatureId, 빈 DTO/GUI/TC 매핑 중 하나라도 있으면 실패한다. 단일 숫자 67을 common infrastructure까지 포함한 전체 callable 수로 해석해서는 안 된다.
- 모든 `ACTION`과 `SESSION`은 최소 하나의 Contract test와 최소 하나의 ViewModel/UIA 시나리오를 가져야 한다. `DERIVED`는 부모 결과 DTO와 golden-direct fidelity test로 증명한다.
- `PLANNED` 또는 문서에만 존재하는 TC는 자동화 완료로 집계하지 않는다.

## 12. 비목표

- 골든 알고리즘 수치·Params·CalibKind 변경
- UI/C#의 DSP·보간·지표·판정 재구현
- 존재하지 않는 offset/gain/geometry calibration builder의 창작
- SAMPLE 또는 사용자 제공 데이터를 정본 승인 데이터로 자동 승격
- P2 C++ 이식, DL/ADR, 배포 기능
