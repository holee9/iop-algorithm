---
id: SPEC-XGUI-MASTER-TRACEABILITY
version: 0.5.1
status: planned
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-13
updated: 2026-07-13
author: drake.lee
priority: high
issue_number: 58
---

# SPEC-XGUI 요구사항-인수-시험 추적 매트릭스

## 1. 표기와 완결 규칙

`REQ-PREFIX-{1..N}`은 해당 범위의 모든 개별 EARS 요구사항을 뜻한다. 각 행은 요구사항, 권위 acceptance, 중앙 TC, 구현 후 제출할 증거를 연결한다. 범위 안에 한 ID라도 없거나, 행에 없는 요구 ID가 발견되거나, TC가 중복되면 G0와 구현 완료를 모두 실패 처리한다.

공통 증거 묶음은 `run_id`, FeatureId, qualified EntryPoint, input/Params/CalibSet hash, result/error DTO, domain/shape/dtype, availability, evidence grade, warning, artifact hash를 포함한다.

## 2. MASTER

| 요구사항 | 인수 시나리오 | 중앙 TC | 필수 증거 |
|---|---|---|---|
| `REQ-XGUI-MASTER-ARCH-{1..4}` | MASTER AC 1, 3, 12 | 160, 161, 167 | WPF 단일 대상, 의존 방향, public-operation 집합 차이 0 |
| `REQ-XGUI-MASTER-SHELL-{1..4}` | MASTER AC 2, 11, 15 | 165, 167 | input-set 검증, ordered hashes, 동적 입력 폼 |
| `REQ-XGUI-MASTER-TABS-{1..3}` | MASTER AC 2, 12 | 167 | 8개 탭과 독립 상태, 전체 command/AutomationId |
| `REQ-XGUI-MASTER-SEAM-{1..8}` | MASTER AC 3, 4, 7, 12, 14 | 161~164, 167 | 9-family DTO, 실제 EntryPoint trace, typed error |
| `REQ-XGUI-MASTER-JOB-{1..6}` | MASTER AC 9 | 162, 167 | 상태 전이, 직렬 호출, 취소 응답, late-result 억제 |
| `REQ-XGUI-MASTER-VIEW-{1..3}` | MASTER AC 2, 3 | 162, 167 | before/after/diff/mask/history와 DTO 배열 동일성 |
| `REQ-XGUI-MASTER-PARAM-{1..4}` | MASTER AC 11, 12 | 160, 161, 167 | manifest schema, selector별 required Params |
| `REQ-XGUI-MASTER-EXPORT-{1..7}` | MASTER AC 5 | 165 | artifact/run-manifest, C-20, round-trip/reproducibility 분리 |
| `REQ-XGUI-MASTER-CAP-{1..4}` | MASTER AC 6, 10, 15 | 166 | availability/evidence 분리와 무단 승격 0 |
| `REQ-XGUI-MASTER-TRACE-{1..3}` | MASTER AC 8 | 160~167 | TC 레지스트리와 자동화 이름 1:1 |
| `REQ-XGUI-MASTER-DQE-{1..4}` | MASTER AC 7, 13 | 164 | support-bin 정책, 실제 두 골든 호출, no extrapolation |
| `REQ-XGUI-MASTER-GATE-{1..6}` | MASTER AC 16 | DOC-XGUI-GATE-001 | 승인 표, 기준선 버전, G0 체크 결과 |

## 3. XSEAM

| 요구사항 | 권위 acceptance | 중앙 TC | 필수 증거 |
|---|---|---|---|
| `REQ-XSEAM-CONTRACT-{6..14}` | XSEAM AC 1, 9, 10 | 161, 166 | 닫힌 DTO, manifest/handler 집합, typed error |
| `REQ-XSEAM-COMPOSE-{1..6}` | XSEAM AC 2~6 | 162 | 단일/부분/전체 실행, intermediates, 거부 보존 |
| `REQ-XSEAM-DQE-{1..5}` | XSEAM AC 7 | 164 | axis 적합성, bin 선택/제외, provenance |
| `REQ-XSEAM-TIER-{1..4}` | XSEAM AC 8 | 163 | decide/select/run/time과 강제 upgrade 거부 |
| `REQ-XSEAM-SESSION-{1..3}` | XSEAM AC 9 | 104~111, 144~151 | fresh Lag state, snapshot/restore, NDT shot log |
| `REQ-XSEAM-COVERAGE-{1..2}` | XSEAM AC 10 | 160, 161, 167 | 여섯 집합의 누락·중복·orphan 0 |

## 4. 그룹별 요구사항

| 그룹 | 요구사항 전개 | 권위 acceptance / 중앙 TC | 필수 증거 |
|---|---|---|---|
| Calibration | `TARGET-{1}`, `BUILD-{1..5}`, `APPLY-{1..4}`, `VIEW-{1..3}`, `SAVE-{1..2}`, `GUARD-{1}`, `REQ-XCAL-COVERAGE-{1..5}` | `SPEC-XGUI-CALIB/acceptance.md`, 096~103 | builder/import→validate→apply, payload/hash/diagnostics, uint8 mask, artifact |
| Lag | `TARGET-{1}`, `INPUT-{1..4}`, `VIEW-{1..6}`, `IRF-{1..4}`, `APPLY-{1..5}`, `METRIC-{1..3}`, `EXPORT-{1..3}`, `DATA-{1..3}`, `REQ-XLAG-STATE-{1..5}` | `SPEC-XGUI-LAG/acceptance.md`, 104~111 | ordered sequence, fitted/populated IRF, fresh state, snapshot/restore, lag metrics |
| Line/Sat/Geo | `TARGET-{1}`, `INPUT-{1..4}`, `PARAMS-{1..3}`, `VIEW-{1..4}`, `RUN-{1..4}`, `DATA-{1..2}`, `GUARD-{1..3}`, `COVERAGE-{1..2}` under prefix `REQ-XGUI-LSG` | `SPEC-XGUI-LINESATGEO/acceptance.md`, 112~119 | 세 action 개별/조합, actual diagnostics, vector/mask, typed reject |
| Denoise | `TARGET-{1}`, `INPUT-{1..3}`, `PARAM-{1..3}`, `APPLY-{1..3}`, `VIEW-{1..3}`, `IO-{1..2}`, `GUARD-{1..4}`, `REQ-XDENOISE-COVERAGE-{1..4}` | `SPEC-XGUI-DENOISE/acceptance.md`, 120~127 | selector schema, populated NOISE, BM3D/NLM, direct-golden fidelity, noise metrics |
| Enhancement | `TARGET-{1}`, `INPUT-{1..3}`, `PARAM-{1..3}`, `VIEW-{1..5}`, `RUN-{1..4}`, `DATA-{1..3}`, `GUARD-{1}`, `REQ-XENH-COVERAGE-{1..4}` | `SPEC-XGUI-ENHANCE/acceptance.md`, 128~135 | MSE/window, GSDF LUT/P-value 운반, display domain, export encoding |
| Grid/VGrid | `TARGET-{1}`, `INPUT-{1..3}`, `BUILD-{1..2}`, `APPLY-{1..3}`, `VIEW-{1..3}`, `EXPORT-{1..2}`, `GUARD-{1..4}`, `REQ-XGRID-COVERAGE-{1..5}` | `SPEC-XGUI-GRID/acceptance.md`, 136~143 | analyze/notch/process, estimate/process, scatter build/fit, spectra/provenance |
| NDT | `TARGET-{1}`, `INPUT-{1..5}`, `ACCUM-{1..4}`, `IQI-{1..4}`, `THICK-{1..3}`, `EXPORT-{1..2}`, `GUARD-{1..4}`, `REQ-XNDT-COVERAGE-{1..5}` | `SPEC-XGUI-NDT/acceptance.md`, 144~151 | 7 action, accumulator state/target/shot log, IQI/thickness, report |
| Metrics | `TARGET-{1}`, `INPUT-{1..3}`, `PARAM-{1..3}`, `COMPUTE-{1..4}`, `VIEW-{1..4}`, `DATA-{1..4}`, `EXPORT-{1..2}`, `GUARD-{1..2}`, `REQ-XMETRIC-COVERAGE-{1..3}` | `SPEC-XGUI-METRICS/acceptance.md`, 152~159 | MTF/NPS/line-noise/defect/DQE/scalar-at, axis/unit, report |

각 그룹 표의 축약 prefix는 해당 행에 명시된 SPEC의 실제 완전한 ID로 전개한다. 예를 들어 Calibration `BUILD-{1..5}`는 `REQ-XGUI-CALIB-BUILD-1`부터 `-5`까지다.

## 5. operation 완결성

| 집합 | 구현 전 권위 | 구현 후 비교 대상 | 합격 조건 |
|---|---|---|---|
| Python 공개 대상 | source AST(`modules` 22 + `metrics` 30 + `pipeline` 12) | catalog `TARGET_OPERATION_SET` | 64/64, 차이 0 |
| SAMPLE helper | 명시 whitelist `scripts.ingest_edrogi` 3개 | catalog `SAMPLE_HELPER_SET` | 3/3, 차이 0 |
| common infrastructure | source AST(`equivalence` 2 + raw load 1 + CalibSet validate/load/save 3) | catalog `COMMON_INFRASTRUCTURE_SET` | 6/6, 차이 0 |
| catalog qualified callable 합집합 | 위 세 집합 | catalog EntryPoint + manifest callable | 73/73, 집합 간 중복 0, 차이 0 |
| catalog ACTION/SESSION | `algorithm-catalog.md` | `AlgorithmCatalogManifest` | 차이 0 |
| manifest | Contract | handler registry | 차이 0 |
| handler | WPF | command/AutomationId | 차이 0 |
| command | 중앙 시험 | XDET-TC coverage | 차이 0 |
| selector Params | golden introspection | runtime ParamSchema | key/type/required/default-source 차이 0 |

DERIVED/INFRASTRUCTURE는 독립 버튼을 강제하지 않지만 부모 result DTO와 provenance에서 실제 값이 관찰 가능해야 한다.

## 6. 추적 완료 판정

문서 완료는 모든 EARS ID가 이 매트릭스에 전개되고, 모든 중앙 TC가 정확히 한 권위 acceptance에 배정되며, 모든 ACTION/SESSION이 실제 GUI 도달 경로를 갖도록 계획됐을 때만 가능하다. 구현 완료는 같은 집합을 실제 코드와 자동화 증거에 대해 다시 비교해 차이 0을 얻어야 한다.
