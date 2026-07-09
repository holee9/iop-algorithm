# SPEC-TIER-001 — 인수 기준 (Acceptance Criteria)

DoD: **티어 gating 구조(XDET-TC-020) + 동일성 diff 프레임(XDET-TC-021)을 구조 검증으로 성립** — 수치 임계 없이 프레임 기계장치가 동작. 모든 기준은 관측 가능(테스트 출력·산출 구조·오류/경고 발생·structurally_equal 판정)해야 한다. **수치 임계는 전부 P2**(티어 판정 임계·정수 bit-동일/부동소수점 ±1 LSB·절대 처리시간 EV-401/402). EV 판정 수치는 엔진 외부(참조). T10은 T0 표면(`CANONICAL_ORDER`·`CalibKind`·`_KIND_BY_STAGE`)을 변경하지 않는다. **본 SPEC의 TC-020/021 구조 통과는 Gen 1 XDET-TC-000~021 전체를 완성하고 P1 완료 정의(골든 모델 형상 동결) 마일스톤을 표시한다 — P1 최종 SPEC.**

## Given-When-Then 시나리오

### Scenario 1 — 엔진 계약: 인프라 계층 배치 · T0 표면 불변 · 판정 분리 (REQ-TIER-CONTRACT)
- **Given** 유효한 capability 기술자·XFrame(불변) 쌍·Params가 주어져 있고, T0 `common/equivalence.diff_frames`(REQ-INFRA-CI-4 훅)·`pipeline/orchestrator.run_pipeline`이 존재한다.
- **When** 티어 gating(`pipeline/tier.py`) 또는 동일성 diff(`common/equivalence.py`) 함수가 실행된다.
- **Then** `pipeline/orchestrator.CANONICAL_ORDER`에 티어 스테이지가 추가되지 않고 신규 `CalibKind`·`_KIND_BY_STAGE` 배선이 없으며, `pipeline/tier.py`는 `run_pipeline` 시그니처·캘리브레이션 게이트를 변경하지 않는 additive 래퍼이고(`pipeline/sequence.py` 선례), `common/equivalence.py`는 `common/xframe`만 의존하는 순수 비교(pipeline/modules/metrics import 0건)이며, import-linter 레이어링 계약이 통과한다. 티어 gating은 실행 티어 분류·경로 선택만 산출하고 EV min/typ/max(EV-401/402) 판정을 내장하지 않는다(측정=판정 분리).

### Scenario 2 — 티어 판정 · 근거 로그 · 실행 경로 선택 (REQ-TIER-GATE-1, -2, -5)
- **Given** `tests/pipeline/`가 mock capability 기술자(CPU 코어 수·AVX 플래그·GPU 모델·VRAM 조합)를 반환한다.
- **When** `decide_tier(capability)`가 실행되고, 확정 티어로 `select_pipeline(tier)`가 실행 경로를 선택한다.
- **Then** (a) 지원 실행 티어와 **근거 로그**(어느 capability가 어느 티어를 결정했는지)가 산출되고, (b) 확정 티어에 대응하는 `PipelineDefinition`·registry가 선택되어 `run_pipeline`에 전달되며(표면 불변), (c) 티어는 실행 경로(EV-401 "Tier 1 결정론적 파이프라인" vs "Tier 2 전체 파이프라인")를 결정할 뿐 달성 화질을 EV 등급으로 분류하지 않는다(결정 3). capability→티어의 **수치 임계는 산출 구조에 하드코딩되지 않는다**(P2 벤치마크, REQ-TIER-GATE-1).

### Scenario 3 — 강제 하향 수용 · 강제 상향 거부 (REQ-TIER-GATE-3, -4)
- **Given** 검출 티어와 사용자 요청 티어(검출 티어 이하 / 검출 티어 초과) 쌍이 주어져 있다.
- **When** 사용자 강제 티어 요청이 gating에 투입된다.
- **Then** (a) 요청 티어 ≤ 검출 티어이면 강제 하향을 수용하고 선택 티어로 경로를 선택하며(SWR-1301 "강제 하향 허용"), (b) 요청 티어 > 검출 티어이면 명시 오류를 발생시켜 거부한다(SWR-1301 "강제 상향 금지" — 단일 경로, 조용한 승격·비결정적 택일 없음). 이 규칙은 수치 임계와 무관한 구조 규칙으로 P1에서 검증된다.

### Scenario 4 — 동일성 diff 프레임: CI-4 훅 재사용 · 양성 등가 · 경로 분류 (REQ-TIER-EQUIV-1, -2, -3)
- **Given** 동일 입력 XFrame을 동일 골든 모델(동일 `process` 시그니처)로 두 번 산출한 출력 쌍과, 정수 경로(offset/gain/defect/line_noise) / 부동소수점 경로 스테이지 셋 정보가 주어져 있다.
- **When** 프레임이 T0 `common/equivalence.diff_frames`를 재사용해 출력 쌍을 비교하고 경로를 분류한다.
- **Then** (a) `EquivalenceDiff`(pixel_equal·masks_equal·noise_equal·max_pixel_abs_diff·structurally_equal)가 diff_frames 재사용으로 산출되고(재구현 0건, SWR-000-9), (b) 동일 산출 쌍에 대해 `structurally_equal=True` 및 `max_pixel_abs_diff==0`을 보고하며(양성), (c) 비교가 정수 경로(bit-동일 대상) 또는 부동소수점 경로(±1 LSB 대상)로 분류된다(P2 게이트 타입 표시). **수치 허용오차(bit-동일/±1 LSB)는 단정하지 않는다**(P2).

### Scenario 5 — 동일성 diff 프레임: perturbation 음성 대조 (REQ-TIER-EQUIV-4)
- **Given** 동일 입력에서 산출한 뒤 한쪽 출력의 pixel(또는 mask)을 의도적으로 perturbation한 XFrame 쌍이 주어져 있다.
- **When** 프레임이 `diff_frames`로 두 출력을 비교한다.
- **Then** 프레임이 차이를 검출한다 — `structurally_equal=False` 및 `max_pixel_abs_diff>0`(음성 대조). 이는 프레임이 공허하게 통과하지 않음(등가 판정이 유의미함)을 증명하며, 수치 허용오차 단정 없이 구조적으로 성립한다(XDET-TC-021 구조).

### Scenario 6 — 티어별 처리시간 하니스 구조 (REQ-TIER-TIMING-1, -2, CONTRACT-3)
- **Given** Tier 1(결정론적) 실행 경로와 표준 프레임이 주어져 있다.
- **When** 타이밍 하니스가 cold 실행 후 warm 실행들을 수행한다.
- **Then** (a) 티어별 **타이밍 레코드**(티어·cold·warm 중앙값·실행 횟수)가 산출되고(XDET-TC-020 "100회 중앙값 cold/warm" 구조), (b) **절대 처리시간 임계(EV-401 ≤3s/≤5s)를 합격/불합격으로 단정하지 않는다**(P2 이연 — P1 골든 모델은 정확도 목적으로 의도적으로 느림, 속도 최적화 금지). P1 게이트는 하니스 구조 성립(레코드 산출)이다.

## Edge Cases (부정/경계 케이스)

### EC-1 — 강제 상향 요청 명시 거부 (REQ-TIER-GATE-4)
- **Given** 검출 티어보다 상위 티어를 강제 요청하는 입력(예: 검출=Tier 1, 요청=Tier 2).
- **When** gating이 요청 티어와 검출 티어를 비교한다.
- **Then** 명시 오류를 발생시켜 거부한다(무단 상향·조용한 승격·기본값 대체 금지 — 단일 결정론 경로, 비결정적 택일 없음).

### EC-2 — perturbation 쌍 공허-통과-아님 (REQ-TIER-EQUIV-4)
- **Given** 한쪽만 perturbation한 출력 쌍(pixel 또는 mask 상이).
- **When** 프레임이 `diff_frames`로 비교한다.
- **Then** `structurally_equal=False`·`max_pixel_abs_diff>0`으로 차이를 검출한다(프레임이 항상 통과하지 않음을 보장 — 양성 Scenario 4의 필수 대조군).

### EC-3 — 무효/결여 capability 기술자 명시 처리 (REQ-TIER-GATE-1)
- **Given** 필수 필드(CPU 코어·AVX·GPU·VRAM)가 결여되었거나 무효한 capability 기술자.
- **When** `decide_tier`가 기술자를 소비한다.
- **Then** 시스템은 명시 오류(`TierDecisionError` 또는 동등)를 발생시켜야 한다 — 무단 임계 추정·조용한 최저 티어 대체·상위 티어 승격을 전부 금지한다(단일 결정론 경로, REQ-TIER-GATE-1/4 강제 상향 금지 정신 승계).

## PARTIAL (P2 / Gen 2 이연 — 결정론적 게이트 아님)

### 수치 동일성 게이트 · 절대 처리시간 (REQ-TIER-VALIDATE-3)
- 정수 경로 bit-동일 의무·부동소수점 ±1 LSB([P]) 수치 게이트(EV-402)와 절대 처리시간 게이트(EV-401 ≤3s/≤5s)는 P1 결정론적 이진 게이트에 포함되지 않는다. 2구현(정수/GPU 커널) 대조와 실 하드웨어 벤치마크가 필요하므로 P2로 이연한다. P1은 diff 프레임 구조·경로 분류·타이밍 하니스 구조만 성립시킨다.

### 하드웨어 벤치마크 · GPU 가속 · DL 경로 (REQ-TIER-VALIDATE-3, 결정 5)
- 어느 CPU/AVX/GPU/VRAM이 어느 티어인지의 실 벤치마크 임계, Tier 2 GPU 가속 커널 구현, DL 경로(SWR-1303 ONNX Runtime·모델 해시·fallback 자동 전환)는 P2/Gen 2 이연이다(CLAUDE.md "Gen 2 항목(DL, ADR)은 구현하지 않는다"). P1의 실행 구현은 결정론적 CPU float 골든 모델 하나이며 bit-대조할 제2 구현이 없다.

## 품질 게이트 / Definition of Done

- [ ] T0 표면 불변: `CANONICAL_ORDER`에 티어 스테이지 미추가 · 신규 `CalibKind`/`_KIND_BY_STAGE` 0건(결정 1, REQ-TIER-CONTRACT-1, Scenario 1)
- [ ] `pipeline/tier.py`는 `run_pipeline` 시그니처·캘리브레이션 게이트 무변경 additive 래퍼(`pipeline/sequence.py` 선례, CONTRACT-1, Scenario 1)
- [ ] 레이어링: `common/equivalence.py` 순수(pipeline/modules/metrics import 0건) · `pipeline/tier.py`는 orchestrator만 소비 — import-linter 통과(CONTRACT-2, Scenario 1)
- [ ] 동일성 diff = T0 `common/equivalence.diff_frames` 재사용 · 프레임 diff 재구현 0건(SWR-000-9, CONTRACT-5·EQUIV-1, Scenario 4)
- [ ] 티어 판정: capability→티어 + 근거 로그 산출 · 임계 하드코딩 0건(P2 이연) + 실행 경로 선택(run_pipeline 위임)(GATE-1·2·5, Scenario 2)
- [ ] 강제 하향 수용 · 강제 상향 명시 거부(단일 결정론 경로)(GATE-3·4, Scenario 3, EC-1)
- [ ] 동일성 diff 양성: 동일 산출 쌍 `structurally_equal=True`·`max_pixel_abs_diff==0` + 정수/부동소수점 경로 분류(EQUIV-2·3, Scenario 4)
- [ ] 동일성 diff 음성 대조: perturbation 쌍 `structurally_equal=False`·`max_pixel_abs_diff>0`(공허 통과 아님)(EQUIV-4, Scenario 5, EC-2)
- [ ] 타이밍 하니스: cold/warm 중앙값 타이밍 레코드 산출 · 절대 시간 게이트 없음(P2)(TIMING-1·2, Scenario 6)
- [ ] 측정=판정 분리: EV min/typ/max(EV-401/402) 판정 수치 엔진 미내장 — 외부 참조(CONTRACT-4, Scenario 1)
- [ ] 수치 임계(티어 판정·bit-동일/±1 LSB·절대 처리시간) P1 코드 하드코딩 0건 — 전부 P2 레지스터 이연(CONTRACT-3, Scenario 6·EC-3)
- [ ] 수치 게이트(정수 bit-동일·부동소수점 ±1 LSB·절대 처리시간) P1 미포함 · P2 PARTIAL 이연 문서화(VALIDATE-3)
- [ ] DL 경로(SWR-1303)·GPU 가속·하드웨어 벤치마크 Gen 2/P2 미구현 명시(결정 5, Exclusions)
- [ ] 무효/결여 capability 기술자 명시 처리 — 무단 상위 티어 승격 금지(EC-3)
- [ ] XDET-TC-020 · XDET-TC-021 pytest skeleton(skip) → 실동작 **구조** 케이스 전환·통과(VALIDATE-1·2)
- [ ] **[capstone] Gen 1 XDET-TC-000~021 전체 CI 통과 확인 → P1 완료 정의(골든 모델 형상 동결) 마일스톤 표시**(VALIDATE-4, P1 최종 SPEC)
- [ ] **티어 gating 구조 + 동일성 diff 프레임 구조 성립 PASS(수치 임계 없이)** — DoD
