---
id: SPEC-XGUI-MASTER-EVAL
version: 0.5.1
status: planned
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
updated: 2026-07-13
---

# SPEC-XGUI-MASTER — GUI 구현 평가 방법서

## 1. 판정 원칙

HARD must-pass를 먼저 판정하고 모두 통과한 구현만 품질 점수를 계산한다. 사용성이 좋아도 알고리즘 누락, 수치 권위 위반, 증거 과장, 데이터 보호 위반을 상쇄할 수 없다.

## 2. HARD must-pass

- Exhaustive coverage: catalog 대상 ACTION/SESSION − manifest/handler/GUI command/TC 집합 차이 0
- Family coverage: 9개 DTO family 모두 Contract·adapter·시험 경로 존재
- Requirement coverage: 모든 EARS ID가 인수기준·TC·실제 자동화 증거로 연결되고 orphan 0
- C-09: UI/adapter DSP·지표·판정·DQE 보간 계산 0
- C-11: WPF→typed seam→Python engine 단방향, Python `apps.gui` helper 직접 의존 0
- C-20: `data/` 쓰기 0, 사용자 폴더만
- SWR-000-2: `CANONICAL_ORDER` 부분수열만
- SWR-000-5: CalibSet/Params 무단 기본 대체 0
- Golden frozen: `common/`, `modules/`, `metrics/`, `pipeline/`, `apps/gui/` 의도치 않은 변경 0
- Fidelity: 순수 transport/동일 호출의 관측 delta 0
- Error fidelity: 17개 Python 공개 예외형이 typed error code로 손실 없이 분류되고 silent fallback·성공 오표시 0
- Job safety: run_id·직렬 engine queue·soft cancel·late-result commit 0
- Provenance: frame/mask round-trip과 run reproducibility를 분리하고 manifest 필수 hash 누락 0
- State honesty: `AlgorithmAvailability`와 `EvidenceGrade` 혼합·불일치 0
- User input: strict schema를 만족한 입력을 등록 fixture 부재만으로 차단 0
- Evidence honesty: SAMPLE/합성/사용자 입력을 승인 정본으로 무단 승격 0
- DQE: `mtf_value_at`→`compute_dqe` engine 실행, support 밖 bin 제외, 외삽/clamp/UI 계산 0
- Tier: 네 공개 tier 작업 reachability, 강제 upgrade 수락 0
- TC evidence: `PLANNED` TC를 자동화 통과 수로 보고 0
- Build/runtime health: `.NET 9 WPF` 전체 solution build 오류 0, `NU1701`을 포함한 TFM/패키지 호환성 경고 0, 실제 UIA smoke의 앱 시작·action·그래프 렌더 실패 0

하나라도 실패하면 전체 판정은 FAIL이다.

## 3. 품질 점수(100)

| 차원 | 배점 | 평가 내용 |
|---|---:|---|
| 기능 완결성 | 30 | operation 도달성 10, 8개 목적 탭 8, 개별/조합/session 실행 6, 저장·재열기 6 |
| golden 충실도 | 25 | EntryPoint/입력 계약 8, transport fidelity 7, 수치 fidelity 6, state·DQE·tier 4 |
| 오류·안전성 | 20 | typed 오류 6, 취소·late result 5, evidence 정직성 5, C-20·경로 보호 4 |
| 사용성 | 10 | 탐색 2, 상태 가시성 2, 비교·probe 3, 그룹별 진단·도움말 3 |
| 시험·추적성 | 15 | catalog/manifest 집합 5, REQ/TC 추적 4, 계층 자동화 4, 증거 재현성 2 |

- PASS: HARD 전부 통과 + 85점 이상
- CONDITIONAL PASS: HARD 전부 통과 + 75~84점, 잔여가 비수치·비안전 minor
- FAIL: HARD 실패 또는 75점 미만

## 4. 그룹별 관찰 포인트

- Calibration: Build/Import/Apply 분리, 모든 builder, 실제 CalibSet, 누적 `uint8` mask
- Lag: fresh/session/snapshot/restore, first-frame/ghost/IRF
- Line/Sat/Geo: no-reference/reference, 포화 무복원, 실제 반환 diag만 표시
- Denoise: method별 required Params, BM3D/NLM, NOISE gate, noise/NPS/SNR 위임
- Enhancement: raw-DN와 `[0,1]` domain, MSE/window/GSDF/P-value
- Grid: analyze/notch/process, virtual scatter, 두 kernel builder, provenance
- NDT: 7 action, accumulator/shot log/target, 측정과 판정 분리
- Metrics: MTF/NPS/line-noise/defect/DQE와 scalar-at 작업, 입력 형태·축 provenance
- Shared: generic pipeline/sequence, tier, input set, artifact/manifest, catalog 전수성

## 5. 수치 충실도와 판정 허용오차

GUI 품질 평가는 알고리즘의 새 임계를 만들지 않는다. 동일 입력을 GUI seam과 Python 골든에 각각 전달해 아래 transport 차이만 판정한다.

| 대상 | 합격 기준 | 비고 |
|---|---|---|
| `uint8` mask·정수 label·enum | shape/dtype/value byte-identical | 플래그 손실·bool 변환 금지 |
| engine `float32` frame | shape/dtype와 모든 IEEE-754 bit 동일 | 같은 골든 호출 결과의 순수 transport 비교 |
| metric axis/series/scalar | dtype·shape·unit 동일, 값 bit-identical | UI가 재계산·보간하지 않으므로 오차 허용 불필요 |
| canonical Params/CalibSet/input hash | 문자열 완전 동일 | 키 정렬과 수치 직렬화 규약 포함 |
| raw-DN artifact | 기대 `uint16` 배열과 byte-identical | little-endian |
| display-normalized artifact | 재열기 값의 절대오차 `<= 0.5/65535` | `round(clip(x,0,1)*65535)` 양자화만 허용 |
| JSON 부동소수 | round-trip 후 원래 IEEE 값 동일 | round-trip 형식 직렬화 사용 |
| 반복 실행 | 3회 결과와 hash 모두 동일 | C-16 결정론 |

알고리즘 자체의 성능·정확도 임계는 SWR, 측정 프로토콜, 기존 Python 시험 또는 승인된 fixture oracle만 권위로 사용한다. SAMPLE은 유한·비퇴화·구조 성립만, SYNTHETIC은 해당 합성 oracle만, USER_SUPPLIED는 실행·재현 가능성만 판정한다. 이 세 등급에서 임상·제품 판정이나 `GOLDEN_APPROVED` 승격을 만들면 HARD 실패다.

## 6. 성능·자원

측정은 Windows x64 Release 빌드, 3072×3072 float32 기준 프레임, 화면 배율 100%, 디버거·프로파일러 미부착 조건에서 수행한다. CPU·RAM·GPU·OS·Python/.NET 버전을 결과에 기록하며, 기준 미달을 더 빠른 장비로 재측정해 숨기지 않는다.

| 항목 | 절차 | 합격 기준 |
|---|---|---|
| W/L 갱신 | 100회 연속 조작, 입력 이벤트→새 프레임 표시 | p95 `<=100 ms`, 최대 `<=200 ms`, 조작당 전체 float 배열 복사 0 |
| zoom/pan/probe | 각 100회, 알고리즘 비실행 상태 | 이벤트 루프 최대 공백 `<=200 ms`, 원본 probe 값 정확 |
| cold start | 새 프로세스 5회, 캐시 상태와 측정 시각 기록 | 각 실행의 상호작용 가능 시점 `<=10 s` |
| 상주 메모리 | before/after/diff + uint8 mask 3장 + 그래프 표시 | peak RSS `<=2 GiB` |
| 탐색 캐시 | 3072² decoded frame 50개를 앞뒤로 순회 | full-frame LRU `K=8`, thumbnail LRU `K=256`, 두 번째 순회 뒤 RSS 증가 `<=64 MiB` |
| 장시간 실행 | Python 호출 중 50 ms heartbeat 기록 | heartbeat 최대 공백 `<=200 ms`, UI thread Python 호출 0 |
| 취소 | 실행 중 취소 20회 | Canceled 표시 `<=250 ms`, 늦은 결과 commit 0, 다음 run 진입 가능 |
| 반복 안정성 | 대표 9-family 실행을 각 20회 | 미회수 RSS 증가 기울기 `<=1 MiB/run`, handle/thread 단조 증가 0 |

`pipeline.tier.time_tier`는 cold/warm/runs/median 구조를 기록하지만 P1 제품 합격의 절대 알고리즘 속도 임계로 사용하지 않는다. 위 표는 GUI 응답성과 자원 상한만 평가한다.

## 7. 그룹별 평가 증거

| 그룹 | 정상 경로 증거 | 음성·경계 증거 |
|---|---|---|
| Calibration | build/import→validate→apply direct-golden equality | 빈 payload, kind/shape/panel/domain 불일치 거부 |
| Lag | ordered sequence, fresh/session/snapshot/restore, IRF/metric | 빈 IRF, 순서 오류, state 오염, SAMPLE 수치 오용 거부 |
| Line/Sat/Geo | 세 action 개별/조합, diag/vector/mask equality | 필수 Params/참조 결여, 무복원 위반 거부 |
| Denoise | selector schema, BM3D/NLM, populated NOISE, noise 지표 | 퇴화 NOISE, 임의 기본 모델, UI DSP 거부 |
| Enhancement | MSE/window, GSDF LUT/P-value DTO, domain encoding | 노이즈 결여, 역순 조합, UI LUT 재계산 거부 |
| Grid/VGrid | analyze/notch/process, estimate/process, 두 builder | 미검출·퇴화 kernel·축 불일치·silent fallback 거부 |
| NDT | 7 action, accumulator/target/shot log, report | 거부 shot state 불변, 단위/ROI/입력 형태 오류 |
| Metrics | MTF/NPS/line-noise/defect/DQE/scalar-at | 축·단위·support·입력 종류 불일치와 외삽 거부 |
| Shared | pipeline/sequence/tier, manifest, artifact, evidence | orphan operation, typed error 손실, C-20, late result |

## 8. 최종 증거 묶음

- catalog 집합 비교와 Python/C# 전체 시험 결과
- import-linter, UIA screenshot·자동화 로그
- golden call trace, fidelity·오류 음성 대조, DQE/tier/state 증거
- frame/mask 저장·재열기 hash, run manifest/reproducibility 결과
- availability/evidence/user-input 표시 증거
- golden·`apps/gui/` 무변경 diff
- TC/REQ/FeatureId 추적 매트릭스와 중앙 TestSpec 자동화 상태
- 성능 표의 raw 측정값, 반복별 표본, p95/최대/peak/기울기 계산과 측정 환경
- G0 승인 기록과 승인된 기준선 버전
