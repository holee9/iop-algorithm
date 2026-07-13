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
labels: [xgui, csharp-ui, gui-redesign, acceptance, master]
---

# SPEC-XGUI-MASTER — 마스터 인수 기준

## Scenarios (Given-When-Then)

### Scenario 1 — C# 단일 구현 대상

- **Given** 저장소에 기존 Python GUI와 C# 콘솔 앱이 함께 있을 때,
- **When** XGUI 기능을 구현하면,
- **Then** 신규 UI·ViewModel·DTO·어댑터·시험은 `apps/xdet-console/`에 존재하고 `apps/gui/` 및 Python 골든은 변경되지 않아야 한다.

### Scenario 2 — 8개 목적별 탭과 공통 셸

- **Given** C# 앱이 시작되고 입력 폴더가 선택되었을 때,
- **When** 사용자가 각 그룹 탭을 순회하면,
- **Then** 8개 탭이 존재하고 공통 폴더 브라우저·비교·Params·export를 재사용하면서 탭별 입력·상태를 독립 보존해야 한다.

### Scenario 3 — 개별 실행과 조합 실행

- **Given** 유효한 Frame/CalibSet/Params가 준비되었을 때,
- **When** 개별 또는 정렬된 조합을 실행하면,
- **Then** 처리 그룹은 generic `RunPipeline`, Lag는 sequence 전용 seam, NDT/Metrics는 metric 전용 seam을 통해 `IXdetEngine`이 골든을 호출하고 결과·중간 프레임·진단을 반환하며 UI는 이를 재계산 없이 표시해야 한다. WPF와 adapter 실행 경로에 Python GUI helper 호출이 없어야 한다.

### Scenario 4 — 거부 의미 보존

- **Given** 비-부분수열, 누락 CalibSet, domain/panel/shape 불일치가 있을 때,
- **When** 사용자가 실행하면,
- **Then** 앱은 오류를 해당 탭에 표시하고 어떤 기본값도 합성하지 않으며 출력 파일을 만들지 않아야 한다.

### Scenario 5 — 저장·재열기와 마스크

- **Given** 프레임 결과와 마스크가 존재할 때,
- **When** 사용자가 저장하면,
- **Then** 사용자 폴더에 result raw/sidecar/mask가 생성되고 `data/` 경로는 거부되며, sidecar에 `xdet.run-manifest/1.0` 필수 필드와 hash가 기록되어야 한다. 재열기 픽셀·마스크의 `artifact round-trip`과 같은 input/Params/CalibSet 재구동의 `run reproducibility`를 서로 다른 판정으로 표시해야 한다.

### Scenario 6 — QUARANTINE

- **Given** SAMPLE-EDROGI 입력을 실행했을 때,
- **When** 결과 화면과 리포트를 보면,
- **Then** SAMPLE-QUARANTINE 배지가 표시되고 sanity 외 EV·튜닝·피팅 완료 주장이 없어야 한다.

### Scenario 7 — DQE 실제 실행

- **Given** strictly increasing `lp/mm` 축, 호환 pixel pitch/domain/beam-quality provenance를 가진 MTF·NPS series가 있을 때,
- **When** 사용자가 Metrics/DQE를 실행하면,
- **Then** engine은 `NPS_BINS_WITHIN_MTF_SUPPORT_V1`로 support 내 NPS bin만 선택하고 각 bin에서 `metrics.mtf.mtf_value_at`을 호출한 뒤 `metrics.dqe.compute_dqe`를 호출해야 한다. UI 보간·외삽·endpoint clamp는 0건이고 선택/제외 bin과 두 EntryPoint가 manifest에 남아야 한다.

### Scenario 8 — 중앙 추적

- **Given** 8개 하위 SPEC과 acceptance가 있을 때,
- **When** TC ID를 수집하면,
- **Then** GUI-E2E ID는 마스터 096~167 블록에서 중복되지 않고 모든 하위 요구가 하나 이상의 관측 가능한 시나리오에 연결되며, 구현된 ID는 `docs/XDET_TestSpec_v1.0.md`와 자동화 테스트 이름에 1:1 등록되어야 한다.

### Scenario 9 — 실행 상태·취소·늦은 결과 억제

- **Given** 한 탭에서 장시간 Python 골든 실행이 시작되어 `run_id=A`가 Running이고,
- **When** 사용자가 A를 취소한 뒤 같은 탭에서 `run_id=B`를 요청하면,
- **Then** UI는 A를 즉시 Canceled로 표시하고 응답성을 유지하며, A가 나중에 반환해도 탭 결과·저장 대상·B의 상태를 덮지 않아야 한다. 엔진이 실제 백분율을 제공하지 않으면 phase와 경과 시간만 표시해야 한다.

### Scenario 10 — 실행 가능성과 증거 등급의 정직한 표시

- **Given** 구현된 기능에 합성, SAMPLE, 외부 사용자 실측, 정본 데이터가 각각 공급될 때,
- **When** 사용자가 각 기능과 리포트를 확인하면,
- **Then** 알고리즘은 `IMPLEMENTED`로 표시하되 실행 결과는 각각 `SYNTHETIC_VERIFIED`, `SAMPLE_SANITY`, `USER_SUPPLIED_UNVERIFIED`, `GOLDEN_APPROVED`로 구분되고, 낮은 증거 등급을 정본 검증 완료로 과대표현하지 않아야 한다.

### Scenario 11 — manifest 기반 동적 입력 폼

- **Given** denoise method 또는 MSE selector처럼 선택값에 따라 필수 Params가 달라지는 기능이 있고,
- **When** 사용자가 selector를 변경하면,
- **Then** `IXdetEngine.AlgorithmCatalogManifest`가 골든 `required_params(params)` 결과로 필수 키를 갱신하고 UI가 type/unit/constraint/default source와 함께 폼을 다시 렌더해야 한다. 문서 metadata와 골든 키가 다르면 실행을 차단하고 mismatch를 표시해야 한다.

### Scenario 12 — 공개 알고리즘 전수 도달 가능성

- **Given** `algorithm-catalog.md`의 ACTION·SESSION·DERIVED·INFRASTRUCTURE 목록과 현재 Python 공개 façade가 있을 때,
- **When** `AlgorithmCatalogCoverageTests`와 GUI action registry를 검사하면,
- **Then** 모든 대상 EntryPoint가 고유 FeatureId, family DTO, GUI owner, TC를 가져야 하고 분류되지 않은 공개 연산·orphan control·호출 불가능 ACTION/SESSION이 0건이어야 한다.

### Scenario 13 — DQE 부적합 입력 거부

- **Given** MTF/NPS 축이 비유한·비증가·단위 불일치이거나 pixel pitch/domain/beam-quality provenance가 호환되지 않거나 support가 겹치지 않을 때,
- **When** 사용자가 DQE 합성을 실행하면,
- **Then** engine은 원인을 구분하는 typed error로 실행을 거부하고 `compute_dqe`를 호출하지 않아야 하며 UI/adapter가 축을 정렬·보정하거나 값을 만들어서는 안 된다.

### Scenario 14 — tier 판단·실행·timing

- **Given** capability, injected `tier_policy`, tier별 PipelineDefinition이 있을 때,
- **When** 사용자가 자동 판단, 허용된 downgrade, 실행 또는 timing을 요청하면,
- **Then** `decide_tier/select_pipeline/run_tier/time_tier` 결과와 rationale가 표시되고, capability 부재·강제 upgrade·variant 부재는 명시 오류가 되어야 하며 absolute-time 합격 판정은 생성하지 않아야 한다.

### Scenario 15 — 사용자 제공 실측 입력

- **Given** 등록 데이터에는 없는 알고리즘용 실측 파일이 `xdet.input-set/1.0`과 required CalibSet/Params를 만족할 때,
- **When** 사용자가 해당 입력을 선택해 실행하면,
- **Then** 등록세트 부재만으로 실행을 막지 않고 알고리즘을 호출하되 결과·report·manifest를 `USER_SUPPLIED_UNVERIFIED`로 표시해야 한다.

### Scenario 16 — 문서 승인과 구현 착수 게이트 (DOC-XGUI-GATE-001)

- **Given** v0.5.1 규범 문서가 내부 교차검토를 통과했지만 사용자 승인 기록이 아직 없을 때,
- **When** 구현 착수 가능 상태를 판정하면,
- **Then** `approval_state=pending_user`, `implementation_authorized=false`를 유지하고 M1 이후 변경을 거부해야 한다.
- **Given** G0 열두 조건이 통과하고 사용자가 기준선 버전과 범위를 명시적으로 승인했을 때,
- **When** 승인 기록을 반영하면,
- **Then** 승인 버전·일시·범위를 기록하고 모든 규범 문서 상태를 동기화한 뒤에만 M1 진입이 가능해야 한다.
- **Given** 승인 뒤 규범 변경이 발생했을 때,
- **When** 변경 영향이 알고리즘 범위·DTO·Params/CalibSet·순서·수치 기준·TC·저장 포맷 중 하나에 닿으면,
- **Then** 기존 승인을 만료시키고 버전 상승, 영향 분석, 전체 교차검증, 사용자 재승인을 요구해야 한다.

## 요구사항-시나리오 추적

| 요구사항 | 시나리오 |
|---|---|
| `REQ-XGUI-MASTER-ARCH-{1..4}` | 1, 3, 12 |
| `REQ-XGUI-MASTER-SHELL-{1..4}` | 2, 11, 15 |
| `REQ-XGUI-MASTER-TABS-{1..3}` | 2, 12 |
| `REQ-XGUI-MASTER-SEAM-{1..8}` | 3, 4, 7, 12, 14 |
| `REQ-XGUI-MASTER-JOB-{1..6}` | 9 |
| `REQ-XGUI-MASTER-VIEW-{1..3}` | 2, 3 |
| `REQ-XGUI-MASTER-PARAM-{1..4}` | 11, 12 |
| `REQ-XGUI-MASTER-EXPORT-{1..7}` | 5 |
| `REQ-XGUI-MASTER-CAP-{1..4}` | 6, 10, 15 |
| `REQ-XGUI-MASTER-TRACE-{1..3}` | 8, 12 |
| `REQ-XGUI-MASTER-DQE-{1..4}` | 7, 13 |
| `REQ-XGUI-MASTER-GATE-{1..6}` | 16 |

완전한 TC·증거 연결은 [traceability-matrix.md](traceability-matrix.md)를 따른다.

## Definition of Done — 문서 기준선

- [ ] MASTER에 `spec.md`, `plan.md`, `acceptance.md`, `research.md`, `test-plan.md`, `eval-methodology.md`, `foundation.md`, `baseline-control.md`, `traceability-matrix.md`가 존재한다.
- [ ] `algorithm-catalog.md`가 모든 대상 공개 연산을 노출 등급·FeatureId·EntryPoint·family DTO·GUI·TC로 분류한다.
- [ ] 8개 하위 디렉터리에 `spec.md`, `plan.md`, `acceptance.md`, `research.md`가 존재한다.
- [ ] 모든 하위 plan의 구현 대상은 `apps/xdet-console/`이며 `apps/gui/`는 참조 전용이다.
- [ ] TC 096~167 중앙 블록에 중복이 없고 공통 160~167 의미가 TestSpec과 catalog에 일치한다.
- [ ] 활성 spec/acceptance에 Python GUI helper가 실행 진입점으로 남지 않고, `제안 TC`·옛 TC·상충 sidecar 예시가 없다.
- [ ] 비차단 UX 선택은 확정 규약으로 닫히고, DQE는 engine-owned `NPS_BINS_WITHIN_MTF_SUPPORT_V1` 실행 계약으로 기록된다.
- [ ] 모든 링크가 존재하고 구현자를 갈라놓는 미완료·미결정 표지가 남지 않는다. 감사 기록은 `.moai/reports/`에 분리되고 활성 규범으로 사용되지 않는다.
- [ ] master/foundation/XSEAM의 seam·job·run manifest·capability 계약이 하위 문서와 일치한다.
- [ ] `AlgorithmAvailability`와 `EvidenceGrade`가 분리되고 구현 상태와 데이터 증거를 합친 폐기 enum이 활성 규범에 남지 않는다.
- [ ] GUI 정량 평가 기준에 미정 임계·미완료 표지가 없고 측정 환경·반복 횟수·통계·합격 방향이 정의돼 있다. Params provenance 등급 `[T]`는 외부 Params/config 권위로만 남는다.
- [ ] 모든 EARS 요구 ID가 `traceability-matrix.md`에서 인수기준·TC·증거로 전개된다.
- [ ] G0 내부 조건 1~11이 통과하고 사용자 승인 전 상태가 `pending_user/false`로 정직하게 표시된다.
- [ ] 사용자 명시 승인과 기준선 동결 전에는 구현 기준선 체크리스트를 실행하지 않는다.

## Definition of Done — 구현 기준선

- [ ] `test-plan.md`의 문서·Contract·adapter·ViewModel·UIA 계층 시험이 통과한다.
- [ ] `eval-methodology.md`의 HARD must-pass가 모두 통과한다.
- [ ] Python 전체 회귀와 import-linter가 무회귀다.
- [ ] C# build/test가 오류 없이 통과하고 호환성 경고가 해소된다.
- [ ] `run_id`/phase/soft cancel/late-result suppression과 엔진 단일 큐 시험이 통과한다.
- [ ] sidecar/report schema·canonical hash·artifact round-trip·run reproducibility 시험이 통과한다.
- [ ] 구현된 GUI TC가 `docs/XDET_TestSpec_v1.0.md`와 자동화 이름에 1:1 등록된다.
- [ ] DQE, tier, calibration builder, lag state, NDT accumulator, 공개 supporting operation이 golden-direct fidelity/상태 시험과 GUI 도달성 시험을 가진다.
- [ ] strict user-supplied input-set으로 모든 ACTION/SESSION family를 실행할 수 있고 evidence grade가 run manifest에 보존된다.
- [ ] 골든 및 기존 Python GUI git diff가 없다.
