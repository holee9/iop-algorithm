---
id: SPEC-XGUI-MASTER-TEST-PLAN
version: 0.5.1
status: planned
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
updated: 2026-07-13
---

# SPEC-XGUI-MASTER — GUI 실동작 시험 계획

## 1. 목적

Python 알고리즘의 수치 시험을 복제하는 것이 아니라 WPF가 저장소의 모든 대상 공개 알고리즘을 정확한 golden EntryPoint로 호출·표시·거부·저장·재현하는지를 검증한다. 기존 Gen 1 TC는 알고리즘 수치 정답을, XGUI `XDET-TC-096~167`은 GUI·seam·전수 추적성을 담당한다.

## 2. 시험 계층

| 계층 | 검증 대상 | 실행 환경 |
|---|---|---|
| Catalog 정적 감사 | Python 공개 작업↔catalog↔manifest↔Contract handler↔GUI command↔TC 집합 동일성 | Python/CI |
| 문서 정적 감사 | 4-file 세트, EARS/GWT, 링크, 버전, TC 중복·누락, 구식 규범 | Python/PowerShell |
| 기준선 게이트 | G0 12조건, 사용자 승인 기록, 승인 전 구현 변경 0 | 문서 감사 / `DOC-XGUI-GATE-001` |
| Contract unit | 9 family DTO, typed value, domain/evidence/error, canonical hash, schema 직렬화 | `dotnet test` |
| PythonNet integration | 실제 golden 호출, Params/CalibSet, DQE composition, tier/state, 오류·fidelity | `dotnet test` + uv venv |
| ViewModel | command reachability, 상태, `run_id`/cancel/late-result 억제, evidence 표시 | headless `dotnet test` |
| WPF headless/UIA | control wiring, AutomationId, 입력→실행→비교→저장·재열기 | Windows CI/interactive desktop |
| Python 회귀 | golden·기존 Python GUI 무회귀 | `uv run pytest`, `uv run lint-imports` |

## 3. 두 상태 축

- `AlgorithmAvailability`: `IMPLEMENTED`, `NOT_IMPLEMENTED`, `PREREQUISITE_MISSING`, `UNSUPPORTED`
- `EvidenceGrade`: `SYNTHETIC_VERIFIED`, `SAMPLE_SANITY`, `USER_SUPPLIED_UNVERIFIED`, `GUIDING_CANDIDATE`, `GOLDEN_APPROVED`

시험은 두 값을 fixture와 결과 manifest에 따로 기록한다. strict schema를 통과한 사용자 입력은 등록 데이터 부재와 독립적으로 실행하며 승인 전 evidence만 제한한다.

## 4. 중앙 TC 매핑

| 범위 | 소유자 | 최소 검증 범위 |
|---|---|---|
| 096~103 | Calibration | apply 3종, 모든 builder/import, fidelity, artifact/evidence |
| 104~111 | Lag | sequence, snapshot/restore/reset, first-frame/ghost/IRF |
| 112~119 | Line/Sat/Geo | 세 action 개별·조합, mask, 오류·저장 |
| 120~127 | Denoise | dynamic Params, BM3D/NLM, noise/NPS/SNR, user input |
| 128~135 | Enhancement | MSE, window, GSDF LUT, P-value remap, domain/export |
| 136~143 | Grid/VGrid | analyze/notch/process, estimate/process, kernel build/fit |
| 144~151 | NDT | 7 action, accumulator session, target/shot log, report |
| 152~159 | Metrics | MTF/NPS/line-noise/DQE/defect, scalar-at, report |
| 160~167 | Shared | catalog, 9 families, pipeline/sequence, tier, DQE, IO/evidence, 모든 GUI action reachability |

모든 번호는 `PLANNED`로 시작한다. 실제 test name과 증거가 중앙 TestSpec에 등록되기 전에는 통과 수로 집계하지 않는다.

## 5. 전수 추적성 시험

`AlgorithmCatalogCoverageTests`는 다음 집합 차이를 모두 0으로 강제한다.

1. `modules` 22 + `metrics` 30 + `pipeline` 12에서 추출한 `TARGET_OPERATION_SET=64` − catalog target EntryPoint.
2. whitelist `scripts.ingest_edrogi`의 `SAMPLE_HELPER_SET=3` − catalog SAMPLE EntryPoint.
3. `common.equivalence` 2 + raw load 1 + `CalibSet.validate/load/save` 3의 `COMMON_INFRASTRUCTURE_SET=6` − catalog infrastructure EntryPoint.
4. 세 집합 합집합 73 − `AlgorithmCatalogManifest` callable; 집합 간 중복도 0.
5. catalog의 ACTION/SESSION − Contract manifest/handler.
6. manifest FeatureId − WPF command/AutomationId.
7. ACTION/SESSION FeatureId − 중앙 TC 096~167의 coverage 표.
8. selector 기반 `required_params`/Params source key − runtime ParamSchema.
9. 모든 EARS requirement ID − `traceability-matrix.md`의 acceptance/TC/evidence 행.

SUPPORTING/INFRASTRUCTURE로 제외한 public symbol도 catalog에 제외 사유를 기록한다. 새 public operation이 추가되면 GUI 또는 명시적 분류 없이는 정적 시험이 실패해야 한다.

## 6. 핵심 통합 시험

- Pipeline: canonical ordered subset, CalibMap/ParamsMap, intermediates, invalid order/누락 gate.
- Sequence/state: 동일 LagCorrector 재사용, fresh/reset, serialize→load 후 다음 결과 동일성.
- Calibration: builder 결과 validate/hash/shape/semantic 검사 후 apply 가능.
- DQE: strictly increasing `lp/mm`, 호환 provenance, support 내 NPS bin만 선택, bin마다 `mtf_value_at`, 이후 `compute_dqe`; 외삽·endpoint clamp·UI 산술 0.
- Tier: `decide_tier`, `select_pipeline`, `run_tier`, `time_tier`; 강제 upgrade 거부, downgrade 허용, structural timing만 보고.
- NDT: 일곱 action과 accumulator update/current/target/shot log의 상태 전이.
- IO: frame raw는 도메인별 uint16 encoding, mask는 `uint8`, sidecar/run manifest hash, C-20, artifact round-trip과 run reproducibility 분리.
- Evidence: SAMPLE은 sanity만, strict 사용자 입력은 실행 가능, 승인 절차 없이 `GOLDEN_APPROVED` 승격 0.
- Error: source의 17개 공개 예외형이 catalog typed error 표와 일치하고 원본 type/stage/field/message 손실·silent fallback이 0.

## 7. 공통 must-pass

1. engine 호출 횟수·순서·qualified EntryPoint가 요청과 일치한다.
2. UI 표시 배열·스칼라·진단이 engine DTO와 동일하고 UI/adapter DSP가 없다.
3. 누락·비호환 입력은 typed error로 거부되고 silent default/substitution이 없다.
4. 모든 실행은 `run_id`를 가지며 cancel 후 late result가 최신 상태를 덮지 않는다.
5. `data/` 쓰기는 0이고 사용자 폴더 저장·재열기가 성립한다.
6. Python golden과 `apps/gui/` diff가 없다.
7. manifest가 EntryPoint, family, input/Params/CalibSet/output hash, availability, evidence를 보존한다.
8. catalog의 모든 ACTION/SESSION은 GUI에서 입력→실행→결과/오류 관찰 경로를 가진다.
9. `dotnet build apps/xdet-console/Xdet.sln --no-restore`는 오류 0·`NU1701`을 포함한 TFM/패키지 호환성 경고 0이며, 실제 WPF UIA smoke가 앱 시작·탭 action·그래프 렌더를 통과한다.

## 8. 수치·성능 oracle

| 시험 | 비교 대상 | 합격 기준 |
|---|---|---|
| transport fidelity | GUI seam result vs 같은 입력의 direct golden result | float32 frame/metric과 uint8 mask bit-identical, shape/dtype/unit 동일 |
| canonical identity | Params/CalibSet/input/result | canonical hash 문자열 동일 |
| raw-DN artifact | 저장 bytes vs 기대 uint16 little-endian | byte-identical |
| normalized artifact | 원값 vs uint16 재열기 | 절대오차 `<=0.5/65535` |
| determinism | 동일 실행 3회 | result/hash bit-identical |
| W/L | 3072², 100회 | p95 `<=100 ms`, 최대 `<=200 ms`, full-array copy 0 |
| cold start | 새 프로세스 5회 | 각 `<=10 s` |
| memory/cache | active layers + 50-frame 왕복 | peak `<=2 GiB`, full LRU 8, thumbnail LRU 256, 2회차 RSS 증가 `<=64 MiB` |
| responsiveness | 50 ms heartbeat, cancel 20회 | 최대 gap `<=200 ms`, Canceled `<=250 ms`, late commit 0 |
| repeated runs | 대표 family 각 20회 | RSS 기울기 `<=1 MiB/run`, handle/thread 단조 증가 0 |

알고리즘 품질 임계는 GUI에서 새로 만들지 않고 기존 Python 시험, SWR, 측정 프로토콜, 승인 fixture oracle을 호출한 결과로만 판정한다. SAMPLE은 sanity, SYNTHETIC은 합성 oracle, USER_SUPPLIED는 실행·재현성만 주장한다.

## 9. 출력 증거

- TC ID, 자동화 test name, `run_id`, FeatureId, EntryPoint, family
- input kind/evidence/SHA-256, canonical Params/CalibSet hash
- stage sequence 또는 session/tier/DQE 정책과 engine call trace
- 결과 domain/shape/dtype/availability/evidence/warnings
- fidelity delta 또는 typed error, 저장 파일/hash, round-trip/reproducibility 판정
- UIA screenshot(시각 시나리오에 한함)
- 성능 반복별 raw sample, p95/최대/peak/기울기, 측정 환경
- G0 승인 버전·승인 일시·승인 범위

## 10. 실행 명령

```powershell
uv run pytest -q
uv run lint-imports
dotnet test apps/xdet-console/Xdet.sln --no-restore --nologo --verbosity minimal
```

UIA smoke는 interactive Windows 세션에서 별도 실행하고 headless 결과와 분리한다.
