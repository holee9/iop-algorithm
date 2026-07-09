---
id: SPEC-TIER-001
version: 0.1.1
status: draft
created: 2026-07-09
updated: 2026-07-09
author: drake.lee
priority: high
issue_number: 11
labels: [T10, tier-gating]
---

# SPEC-TIER-001 — T10 티어/동일성 프레임: 티어 판정·gating 구조 + 동일성(equivalence) diff 프레임 (구조만, 수치 P2)

XDET 영상처리 SW P1의 **마지막 작업 T10**. 티어(tier)·동일성(equivalence) 프레임 **WP12(SWR-1301~1303, FR-C012/C013)**의 **구조**를 구현한다. 핵심은 둘이다 — (1) **티어 판정·gating 구조**: 하드웨어 연산 능력(CPU 코어·AVX 지원, GPU 모델·VRAM)을 소비해 실행 티어를 판정하고 판정 결과·근거를 로그로 산출하며, 그 티어에 맞는 실행 경로(파이프라인 변형)를 선택한다. 사용자 **강제 하향은 허용**하고 **강제 상향은 거부**한다(SWR-1301). (2) **동일성 diff 프레임**: 동일 `process` 시그니처를 공유하는 두 티어/구현의 출력을 **T0가 이미 제공한 `common/equivalence.diff_frames` 훅(REQ-INFRA-CI-4)을 재사용**하여 구조적으로 비교하고, 정수 경로(offset/gain/defect/line noise = bit-동일 대상)와 부동소수점 경로(±1 LSB 대상)를 분류해 구조 판정을 반환한다(SWR-1302, XDET-TC-021). **수치 임계는 전부 P2** — 티어 판정 임계(P2 벤치마크), 정수 bit-동일/부동소수점 ±1 LSB([P]), 절대 처리시간(EV-401)은 P1에서 단정하지 않는다.

**T10은 픽셀 보정 처리 모듈이 아니라 실행 인프라·검증 프레임이다.** SWR-1301(티어 판정=실행 경로 선택)·SWR-1302(출력 비교=검증 훅)는 픽셀 출력이 없고, `pipeline/orchestrator.CANONICAL_ORDER`에 티어 스테이지가 없음을 코드로 확인했다. 따라서 T10은 T9(NDT)와 마찬가지로 **T0 오케스트레이터 표면(`CANONICAL_ORDER`·`CalibKind`·`_KIND_BY_STAGE`)을 변경하지 않는다** — 티어 gating은 `pipeline/tier.py`(신규)가 `run_pipeline`을 감싸 실행 변형을 선택하는 **additive 래퍼**(`pipeline/sequence.py` 래퍼 선례)로, 동일성 diff는 기존 `common/equivalence.py`(REQ-INFRA-CI-4 훅)를 **확장·재사용**하여 배치한다. 이는 T2~T8(전용 스테이지 부분수열-삽입) 대비 T10의 근본 아키텍처 구별점이며, T9와 같은 T0-표면-불변 계열이다(결정 1, 「결정 필요/확인 사항」 1).

- 근거: SWR-1301~1303(티어·동일성, FR-C012/C013) · SWR-000-1/-8/-11/-12(아키텍처·CI·정밀도 훅) — `docs/XDET_SWR_spec_v1.2.md`; 등급(부록 A-2): 티어 판정 임계 = **P2 벤치마크 이연**(SWR-1301 본문 "임계 TBD: P2 벤치마크"), 부동소수점 ±1 LSB = **[P]**(부록 A-2 "1302(±1 LSB)"), 파이프라인 순서/구조 관행 = **[C]**(000 계열)
- EVAL v1.1: XDET-EV-401(처리시간 — Tier 2 전체 파이프라인 ≤3/1/0.3s · Tier 1 결정론적 파이프라인 ≤5/2/1s, [B]) · XDET-EV-402(티어 간 결과 동일성 — 진단 영향 기능 결과 차: 정의된 허용오차 내 min / bit 동일 typ / 동일 max) — **전부 P2 수치 게이트**; P1은 프레임 구조만 성립
- TestSpec: XDET-TC-020(VV-012, Tier별 파이프라인 처리시간[100회 중앙값 cold/warm], GDS-표준 프레임, EV-401 min) · XDET-TC-021(VV-012, 티어 간 출력 diff[결정론 bit / 부동소수점 허용오차], GDS-표준 프레임, EV-402 min) — **P1은 구조 통과, 절대 시간·수치 임계는 P2**(CLAUDE.md T10). 현재 `tests/test_tc_skeletons.py`에 XDET-TC-020("tier gating structure (T10)")·XDET-TC-021("equivalence numeric gate: bit-identical / +/-1 LSB (P2)")가 skip skeleton으로 등록되어 있으며 본 SPEC이 이를 실동작 구조 케이스로 전환한다
- 완료 정의(DoD): **티어 gating 구조 + 동일성 diff 프레임을 합성/구조 검증으로 성립** — (a) **[구조 DoD] 티어 판정·gating**(XDET-TC-020): 합성 capability 기술자(CPU 코어·AVX·GPU·VRAM mock)에 대해 티어 판정·근거 로그·강제 하향 수용·강제 상향 거부·실행 경로 선택이 구조적으로 동작(절대 처리시간 게이트·실 하드웨어 벤치마크 없이 — P2). (b) **[구조 DoD] 동일성 diff 프레임**(XDET-TC-021): `common/equivalence.diff_frames` 재사용으로, 동일 입력 2회 산출 쌍은 구조 등가(structurally_equal=True) / 의도적 perturbation 쌍은 차이 검출(음성 대조)을 정수·부동소수점 경로 분류와 함께 보고(수치 임계 bit-동일/±1 LSB 단정 없이 — P2). XDET-TC-020/021을 pytest skeleton(skip)에서 실동작 구조 케이스로 전환. **본 SPEC의 TC-020/021 구조 통과는 Gen 1 대상 XDET-TC-000~021 전체를 완성하며 P1 완료 정의(골든 모델 형상 동결) 마일스톤을 표시한다 — P1 최종 SPEC.** 수치 동일성 게이트·절대 처리시간·하드웨어 벤치마크·DL 경로(SWR-1303)는 P2/Gen 2 이연(PARTIAL)
- 선행 계약: [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md) — **본 SPEC의 직접 전제**: `common/equivalence.diff_frames`(REQ-INFRA-CI-4 등가성 diff 훅, "동일 시그니처 골든/최적화/FPGA 구현 비교 단일 진입점", 구조만·수치 P2)·`EquivalenceDiff`(pixel_equal·masks_equal·noise_equal·max_pixel_abs_diff·structurally_equal), `pipeline/orchestrator.run_pipeline`·`PipelineDefinition`(CANONICAL_ORDER 부분수열)·`_calibration_gate`, `pipeline/sequence.py`(run_pipeline additive 래퍼 선례), XFrame(불변)·`CANONICAL_ORDER` 정수 경로 스테이지(offset/gain/defect/line_noise); [SPEC-NDT-001](../SPEC-NDT-001/spec.md) — **T0-표면-불변 계열 선례**(측정·인프라 계층은 스테이지 신설·신규 CalibKind 없이 배치)
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.1.1 (2026-07-09)** — plan-audit iteration 1 (FAIL 0.75) 결함 반영: D3(major, EC-3 이접 조항 "명시 오류 또는 정의된 보수적 기본 처리" → 명시 오류 단일 경로로 정정, 무단 임계 추정·조용한 최저 티어 대체·상위 승격 전부 금지)·D1(REQ-TIER-CONTRACT-3 acceptance 미추적 → Scenario 6·DoD 체크박스 추가). 감사에서 독립 재검증: 결정 1(pipeline/tier.py additive 래퍼, T0 표면 불변)·결정 3(tier=하드웨어 실행 경로 분류, EV 화질 등급 아님) 코드·SWR/EVAL 원문 대조로 승인(PROCEED).
- **v0.1.0 (2026-07-09)** — 초안 생성. GitHub 이슈 #11. **P1 최종 SPEC(T10 티어/동일성 프레임 WP12).** 5개 요구 그룹(GATE/EQUIV/TIMING/CONTRACT/VALIDATE) EARS 구조 확정. 핵심 범위 결정:
  1. **T10 = 실행 인프라·검증 프레임 계층, 처리 스테이지 신설 없음(T0 표면 불변)([placement — 잠재적 run-blocking if rejected])**: SWR-1301(티어 판정=경로 선택)·SWR-1302(출력 비교=검증 훅)는 픽셀 출력이 없고 `CANONICAL_ORDER`에 티어 스테이지가 없음을 코드로 확인 → 티어 gating은 `pipeline/tier.py`(신규, run_pipeline additive 래퍼) + 동일성 diff는 `common/equivalence.py`(REQ-INFRA-CI-4 훅) 확장으로 배치하고 T0 오케스트레이터 표면을 변경하지 않는다. **T9(NDT)와 같은 T0-표면-불변 계열이며 T2~T8의 전용 스테이지 부분수열-삽입 패턴과 반대.** 「결정 필요/확인 사항」 1.
  2. **동일성 diff = `common/equivalence.diff_frames` 재사용(재구현 금지)**: T0가 REQ-INFRA-CI-4로 이미 "동일 시그니처 구현 비교 단일 진입점"을 제공(구조만·수치 P2). T10은 그 위에 정수 경로/부동소수점 경로 분류 + 구조 판정 프레임을 얹고, 수치 임계(bit-동일/±1 LSB)는 P2로 이연한다. T10은 이 T0 훅의 **첫 실사용 소비자**다(LAG가 T0 StatefulModule 스텁의 첫 소비자였던 선례). 순수 비교는 `common/`(pipeline import 없음), 티어 쌍 산출은 `pipeline/tier.py`, 쌍 구성 하니스는 `tests/`. 「결정 필요/확인 사항」 2.
  3. **"티어"는 하드웨어 연산 능력 티어(CPU/AVX/GPU/VRAM)이지 달성 화질의 EV 등급 분류가 아님 — SWR 텍스트로 검증**: SWR-1301(CPU 코어·AVX·GPU·VRAM 기반 판정) + EV-401("Tier 2 전체 파이프라인" vs "Tier 1 결정론적 파이프라인")이 티어를 **실행 경로**로 정의한다. 티어는 어느 실행 경로가 도는지를 결정할 뿐 MTF/DQE 달성치를 EV min/typ/max로 매핑하지 않는다. EV min/typ/max는 별도의 지표 합격 기준이며 티어와 독립. "강제 하향 허용·강제 상향 금지"=사용자는 더 보수적인(낮은) 티어를 강제할 수 있으나 하드웨어가 지원하지 않는 상위 티어는 강제할 수 없다. 「결정 필요/확인 사항」 3.
  4. **XDET-TC-020 처리시간 하니스 = 구조만, 절대 시간 P2**: cold/warm·100회 중앙값 측정 하니스 **구조**(티어별 실행·타이밍 레코드)만 구현하고 EV-401 절대 시간 게이트(≤3s/≤5s)는 단정하지 않는다(P1 골든 모델은 의도적으로 느림 — 속도 최적화 금지). 「결정 필요/확인 사항」 4.
  5. **DL 경로(SWR-1303) = Gen 2 예약, 미구현**: ONNX Runtime·모델 해시 검증·fallback 자동 전환은 Gen 2 항목으로 P1 구현 밖(CLAUDE.md "Gen 2 항목(DL, ADR)은 구현하지 않는다"). 티어 taxonomy에 DL 티어 이름을 문서상 예약할 수 있으나 런타임은 없다. 「결정 필요/확인 사항」 5.

## Environment / Assumptions

- Python 3.11+, numpy/scipy 기반 float 골든 모델(tech.md). **속도 최적화 금지 — 정확도 단일 목표**(P2에서 최적화). 티어/동일성 프레임도 실행 경로 선택·구조 비교의 정확성이 목적이며 성능·벤치마크 목적이 아니다(절대 처리시간은 P2, EV-401).
- 대상 프레임: 3072×3072 / 3072×2560, 16-bit unsigned raw, pitch 140µm(EVAL v1.1 §0 파생 상수). 동일성 diff는 XFrame(pixel float32·mask 스택·noise·history)을 단위로 비교한다.
- **P1의 실행 구현은 단 하나다 — float 골든 모델(결정론적 CPU 경로, ≈Tier 1).** SWR-1302가 대조하는 "정수 경로 GPU/CPU 커널 쌍"·"Tier 2 GPU 가속 파이프라인"은 **P1에 구현이 없다**. 따라서 동일성 프레임은 P1에서 (a) 골든 모델 출력을 자기 자신과 비교(양성: structurally_equal) 및 (b) 의도적으로 perturbation한 사본과 비교(음성 대조: 차이 검출)로 **프레임의 구조 기계장치가 동작함**을 증명하며, 실제 bit-동일 의무·±1 LSB 허용오차 단정은 2구현이 존재하는 P2로 이연한다. 이것이 "구조만, 수치 P2"의 의미다.
- **T0 REQ-INFRA-CI-4 훅의 첫 실사용 소비자.** `common/equivalence.diff_frames(a, b) -> EquivalenceDiff`는 T0에서 "동일 `process` 시그니처를 공유하는 골든/최적화/FPGA 구현이 XDET-TC-021 계열로 비교될 수 있도록" 이미 배치되었고(구조만·수치 임계 P2 명시), 그 diff 형상(pixel_equal·masks_equal·noise_equal·max_pixel_abs_diff·structurally_equal)은 계약이다. T10은 이를 **재사용**하며 프레임 diff를 재구현하지 않는다(SWR-000-9).
- **아키텍처 배치 — 인프라 계층, T0 표면 불변.** 티어 gating부는 처리 모듈이 아니다: `process(XFrame,CalibSet,Params)->XFrame` 계약을 따르지 않고, `run_pipeline`을 감싸 실행 변형(어느 스테이지 subset·어느 registry)을 선택하는 additive 래퍼(`pipeline/tier.py`, `pipeline/sequence.py` 선례)로 실현한다. **`CANONICAL_ORDER`에 스테이지를 추가하지 않고, 신규 `CalibKind`·`_KIND_BY_STAGE` 배선을 신설하지 않는다**(결정 1). 티어는 검출기 캘리브레이션을 요구하지 않으므로 CalibSet 종류 신설도 없다.
- **레이어링.** 동일성 비교(`common/equivalence.py`)는 `common/xframe`만 의존하는 순수 비교이며 `pipeline`/`modules`/`metrics` import가 없다(common은 최하위 레이어). 티어 쌍 산출·경로 선택은 `pipeline/tier.py`(run_pipeline 소비), 쌍 구성·검증 하니스는 `tests/`(프로덕션 트리 밖 — INFRA/METRICS 선례). import-linter 계약으로 검증한다.
- **파라미터·수치 정책(HARD).** 전 수치 임계는 P1 코드에 하드코딩되지 않는다: 티어 판정 임계(어느 VRAM/코어 수 → 어느 티어) = **P2 벤치마크 이연**(SWR-1301 "임계 TBD: P2 벤치마크"), 정수 경로 bit-동일 의무·부동소수점 ±1 LSB = **[P] P2**(부록 A-2 "1302(±1 LSB)"), 절대 처리시간 EV-401(≤3s/≤5s) = **P2**([B]). P1은 프레임 구조만 성립시키고 수치 게이트는 P2 레지스터로 이연한다(CLAUDE.md T10 "수치 임계는 P2").
- **측정=판정 분리.** 티어 gating은 실행 티어 분류·근거·경로 선택을 산출할 뿐 EV min/typ/max 합격/불합격 판정을 내장하지 않는다. 티어는 하드웨어 연산 능력 분류이며 달성 화질을 EV 등급으로 매핑하지 않는다(결정 3 — T1~T9 측정=판정 분리 승계).
- **강제 하향/상향 규칙(SWR-1301).** 사용자는 검출 티어 이하의 티어를 강제(하향)할 수 있으나 상위 티어 강제는 명시 거부한다. 이는 수치 임계와 무관한 **구조 규칙**이므로 P1에서 검증 가능하다(예: 검출 티어=T1 → T2 요청 거부; T1 이하 요청 수용).

## Requirements (EARS)

### REQ-TIER-GATE — 티어 판정 · 근거 로그 · 강제 하향/상향 규칙 · 실행 경로 선택 (SWR-1301, EV-401, XDET-TC-020)

- **REQ-TIER-GATE-1 (Event-Driven)** — WHEN 하드웨어 연산 능력 기술자(CPU 코어 수·AVX 지원 플래그·GPU 모델·VRAM — 입력 구조/Params로 주입)가 주어지면, THEN 시스템은 지원 가능한 실행 티어를 판정하고 판정 결과와 **근거 로그**(어느 capability가 어느 티어를 결정했는지)를 산출해야 한다(SWR-1301). 어느 capability 값이 어느 티어를 낳는지의 **수치 임계는 P1에 하드코딩하지 않으며 P2 벤치마크로 이연**한다(주입/이연 — SWR-1301 "임계 TBD: P2 벤치마크").
- **REQ-TIER-GATE-2 (Ubiquitous)** — 티어 판정은 어느 **실행 경로(파이프라인 변형)**가 실행되는지를 결정해야 하며, 달성 화질을 EV 등급으로 분류하지 않아야 한다. 티어는 하드웨어 연산 능력 티어(EV-401 "Tier 1 결정론적 파이프라인" vs "Tier 2 전체 파이프라인")이고, EV min/typ/max 지표 합격 기준과 독립이다(결정 3, SWR-1301/EV-401).
- **REQ-TIER-GATE-3 (Event-Driven)** — WHEN 사용자가 검출 티어 이하(같거나 더 보수적인)의 티어를 강제 요청하면, THEN 시스템은 그 강제 하향을 수용하고 선택 티어로 실행 경로를 선택해야 한다(SWR-1301 "사용자 강제 하향 허용").
- **REQ-TIER-GATE-4 (Unwanted)** — IF 사용자가 검출 하드웨어 티어보다 상위 티어를 강제 요청하면, THEN 시스템은 그 요청을 거부하고 명시 오류를 발생시켜야 한다(SWR-1301 "강제 상향 금지" — 무단 상향·조용한 승격 금지; 거부 단일 경로, 비결정적 택일 없음).
- **REQ-TIER-GATE-5 (Event-Driven)** — WHEN 실행 티어가 확정되면(자동 판정 또는 강제 하향), THEN 시스템은 그 티어에 대응하는 `PipelineDefinition`·registry(실행 변형)를 선택해 `run_pipeline`에 전달해야 하며, 이 선택은 `run_pipeline` 시그니처·`CANONICAL_ORDER`·캘리브레이션 게이트를 변경하지 않는 additive 래퍼(`pipeline/tier.py`)로 수행해야 한다(결정 1, `pipeline/sequence.py` 선례).

### REQ-TIER-EQUIV — 동일성 diff 프레임 (CI-4 훅 재사용 · 정수/부동소수점 경로 분류 · 구조 판정) (SWR-1302, XDET-TC-021)

- **REQ-TIER-EQUIV-1 (Ubiquitous)** — 두 티어/구현(동일 `process` 시그니처를 공유하는 출력 쌍)의 비교는 T0 `common/equivalence.diff_frames`(REQ-INFRA-CI-4 훅)를 **재사용**하여 `EquivalenceDiff`(pixel_equal·masks_equal·noise_equal·max_pixel_abs_diff·structurally_equal)를 산출해야 하며, T10은 프레임 diff를 재구현하지 않아야 한다(SWR-000-9 중복 금지). T10은 이 T0 훅의 첫 실사용 소비자다.
- **REQ-TIER-EQUIV-2 (Event-Driven)** — WHEN 출력 쌍이 비교되면, THEN 프레임은 그 비교를 **정수 경로**(offset/gain/defect/line_noise 스테이지 산출 — bit-동일 대상) 또는 **부동소수점 경로**(그 외 스테이지 — ±1 LSB 대상)로 분류하고(SWR-1302), `diff_frames`의 구조 판정(structurally_equal·max_pixel_abs_diff)을 반환해야 한다. 분류는 어느 경로의 P2 수치 게이트(bit-동일 vs ±1 LSB)가 나중에 적용될지를 표시하는 **구조 속성**이다.
- **REQ-TIER-EQUIV-3 (State-Driven)** — WHILE 구조 검증 컨텍스트인 동안, 동일 입력을 동일 골든 모델로 두 번 산출한 출력 쌍에 대해 프레임은 `structurally_equal=True`(정수 경로 exact 등가) 및 `max_pixel_abs_diff==0`을 보고해야 한다(양성 — 프레임이 등가를 정상 인식, XDET-TC-021 구조).
- **REQ-TIER-EQUIV-4 (State-Driven)** — WHILE 구조 검증 컨텍스트인 동안, 한쪽을 의도적으로 perturbation한 출력 쌍에 대해 프레임은 차이를 검출(`structurally_equal=False`, `max_pixel_abs_diff>0`)해야 한다(음성 대조 — 프레임이 공허하게 통과하지 않음을 증명; 수치 허용오차 단정 없이, XDET-TC-021 구조).

### REQ-TIER-TIMING — 티어별 처리시간 하니스 구조 (절대 시간 P2) (SWR-1301, EV-401, XDET-TC-020)

- **REQ-TIER-TIMING-1 (Event-Driven)** — WHEN 타이밍 하니스가 한 티어의 파이프라인을 표준 프레임에 대해 실행하면, THEN 하니스는 cold 실행 후 warm 실행들을 수행하고 티어별 **타이밍 레코드**(티어·cold·warm 중앙값·실행 횟수)를 산출해야 한다(SWR-1301, XDET-TC-020 "100회 중앙값 cold/warm").
- **REQ-TIER-TIMING-2 (Ubiquitous)** — 타이밍 하니스는 구조화된 타이밍 레코드를 산출할 뿐 **P1에서 절대 처리시간 임계(EV-401 ≤3s/≤5s)를 합격/불합격으로 단정하지 않아야 한다**(P2 이연 — P1 골든 모델은 정확도 목적으로 의도적으로 느리며 속도 최적화가 금지됨). P1 게이트는 하니스 구조 성립(레코드 산출)이다(SWR-1301/EV-401, XDET-TC-020).

### REQ-TIER-CONTRACT — 인프라 계층 계약 · T0 표면 불변 · 수치 이연 · 측정=판정 분리 (SWR-000-6~12, CLAUDE.md T10)

- **REQ-TIER-CONTRACT-1 (Ubiquitous)** — T10 티어/동일성 프레임은 처리 모듈이 아니다. `process(XFrame,CalibSet,Params)->XFrame` 계약을 따르지 않고, `pipeline/orchestrator.CANONICAL_ORDER`에 스테이지를 추가하지 않으며, 신규 `CalibKind`·`_KIND_BY_STAGE`를 신설하지 않아야 한다(T0 표면 불변 — 결정 1, T9 NDT 선례, T2~T8 스테이지 삽입과 대조). 티어 gating은 `pipeline/tier.py`(신규)가 `run_pipeline`을 감싸는 additive 래퍼로서 `run_pipeline` 시그니처·`CANONICAL_ORDER`·캘리브레이션 게이트를 변경하지 않아야 한다(`pipeline/sequence.py` 선례).
- **REQ-TIER-CONTRACT-2 (Ubiquitous)** — 동일성 diff 비교(`common/equivalence.py`)는 `common/xframe`만 의존하는 순수 비교로서 `pipeline`·`modules`·`metrics` import가 없어야 하며(common 최하위 레이어), 티어 쌍 산출·경로 선택은 `pipeline/tier.py`, 쌍 구성·검증 하니스는 `tests/`(프로덕션 트리 밖)에 두어야 한다. import-linter 계약으로 레이어링을 검증한다(결정 2).
- **REQ-TIER-CONTRACT-3 (Ubiquitous)** — 모든 수치 임계(티어 판정 임계 = P2 벤치마크, 정수 경로 bit-동일·부동소수점 ±1 LSB = [P] P2, 절대 처리시간 EV-401 = P2 [B])는 P1 코드에 하드코딩되지 않아야 하며 P2 레지스터로 이연되어야 한다(CLAUDE.md 파라미터 정책·T10 "수치 임계는 P2"; 신규 파라미터는 SWR 부록 A/A-2 등재 요청).
- **REQ-TIER-CONTRACT-4 (Ubiquitous)** — 측정=판정 분리: 티어 gating은 실행 티어 분류·근거·경로 선택을 산출할 뿐 EV min/typ/max(EV-401/402) 합격/불합격 판정을 내장하지 않아야 한다. 티어는 하드웨어 연산 능력 분류이며 달성 화질을 EV 등급으로 매핑하지 않아야 한다(결정 3, T1~T9 측정=판정 분리 승계).
- **REQ-TIER-CONTRACT-5 (Ubiquitous)** — 동일성 프레임은 T0 REQ-INFRA-CI-4 훅(`common/equivalence.diff_frames`)의 diff 형상(pixel_equal·masks_equal·noise_equal·max_pixel_abs_diff)을 재사용하고 재구현하지 않아야 한다(SWR-000-9). P2 수치 동일성 게이트(bit-동일/±1 LSB)는 이 훅 위에 얹히며, T10은 그 훅의 첫 실사용 소비자로서 구조 판정만 제공한다.

### REQ-TIER-VALIDATE — TC 게이트(구조) · P1 완료 정의 capstone (XDET-TC-020/021, EV-401/402)

- **REQ-TIER-VALIDATE-1 (State-Driven)** — WHILE 구조 검증 컨텍스트인 동안, 합성 capability 기술자(mock CPU 코어·AVX·GPU·VRAM)에 대해 티어 판정·근거 로그·강제 하향 수용·강제 상향 거부·실행 경로 선택이 구조적으로 동작함을 보여야 한다(XDET-TC-020 티어 gating 구조 — 절대 처리시간 게이트·실 하드웨어 벤치마크 없이, P2 이연). XDET-TC-020을 pytest skeleton(skip)에서 실동작 구조 케이스로 전환한다.
- **REQ-TIER-VALIDATE-2 (State-Driven)** — WHILE 구조 검증 컨텍스트인 동안, 동일 입력 2회 산출 쌍은 `structurally_equal=True`(양성), 의도적 perturbation 쌍은 차이 검출(음성 대조)로 XDET-TC-021 동일성 diff 프레임이 정수/부동소수점 경로 분류와 함께 구조적으로 동작함을 보여야 한다. 수치 동일성 임계(정수 bit-동일 / 부동소수점 ±1 LSB)는 P1에서 단정하지 않는다(P2 — 2구현 대조 필요). XDET-TC-021을 pytest skeleton(skip)에서 실동작 구조 케이스로 전환한다(SWR-1302).
- **REQ-TIER-VALIDATE-3 (Ubiquitous)** — 수치 게이트(정수 bit-동일·부동소수점 ±1 LSB·절대 처리시간 EV-401)는 P1 결정론적 이진 게이트에 포함되지 않고 P2로 이연되어야 한다(PARTIAL — 2구현 대조·실 하드웨어 벤치마크 필요; SWR-1302/EV-401/402, 부록 A-2 [P] 1302).
- **REQ-TIER-VALIDATE-4 (Ubiquitous)** — 시스템은 XDET-TC-020·XDET-TC-021의 **구조 통과**로써 Gen 1 대상 XDET-TC-000~021 전체를 완성하고 **P1 완료 정의(골든 모델 형상 동결)** 마일스톤을 표시해야 한다(본 SPEC은 P1 최종 SPEC). Gen 2 항목(DL 경로 SWR-1303·ADR)은 구현하지 않아야 한다(CLAUDE.md 완료 정의).

## Exclusions (What NOT to Build)

- **처리 스테이지 신설 없음(T0 표면 불변)** — `CANONICAL_ORDER`에 티어 스테이지를 추가하지 않고, 신규 `CalibKind`·`_KIND_BY_STAGE`를 신설하지 않는다. T10은 실행 인프라·검증 프레임 계층이며 픽셀 보정 스테이지가 아니다(결정 1, T9 NDT T0-표면-불변 선례).
- **동일성 diff 유틸 재구현 없음** — 프레임 비교는 T0 `common/equivalence.diff_frames`(REQ-INFRA-CI-4 훅)를 재사용한다. T10은 diff 형상을 재구현하지 않는다(SWR-000-9).
- **수치 동일성 게이트 없음(P2)** — 정수 경로 bit-동일 의무·부동소수점 ±1 LSB([P]) 수치 단정은 P2. P1은 diff 프레임 구조와 정수/부동소수점 경로 분류만 제공하며 허용오차를 단정하지 않는다(T0 CI-4가 이미 명시한 구조/수치 분리 승계).
- **절대 처리시간 게이트 없음(P2)** — EV-401(Tier 처리시간 ≤3s/≤5s)은 P2. P1 골든 모델은 정확도 목적으로 의도적으로 느리며(속도 최적화 금지) 타이밍 하니스는 구조 레코드만 산출한다.
- **하드웨어 벤치마크·실 GPU 가속 커널 없음** — 어느 CPU/AVX/GPU/VRAM이 어느 티어인지의 실 벤치마크 임계와 GPU 가속(Tier 2) 커널 구현은 P2. P1의 실행 구현은 단 하나(결정론적 CPU float 골든 모델)이며 bit-대조할 제2 구현이 없다.
- **강제 상향 미지원** — 검출 하드웨어 티어보다 상위 티어의 강제 상향은 거부한다(SWR-1301). 구현 공백이 아니라 규칙이다.
- **DL 경로 / Gen 2 없음** — SWR-1303(ONNX Runtime·모델 해시 검증·fallback 자동 전환)은 Gen 2 예약 항목으로 P1 구현 밖(CLAUDE.md "Gen 2 항목(DL, ADR)은 구현하지 않는다"). DL 티어 런타임·fallback 전환 로직 없음.
- **속도·메모리 최적화 없음** — 티어/동일성 프레임은 실행 경로 선택·구조 비교의 정확성이 목적이며 성능 최적화는 P2.

## 결정 필요/확인 사항

아래는 SWR 본문·T0 구현과의 대조에서 남는 열린 질문과 가정 기본값이다. 1은 잠재적 run-blocking(기각 시 T0 표면 변경), 2~5는 확인 항목이다. run 착수 전 확정하고 HISTORY로 접는다.

1. **[배치 — 잠재적 run-blocking if rejected] T10 배치: 인프라 계층(T0 표면 불변).** SWR-1301(티어 판정=경로 선택)·SWR-1302(출력 비교=검증 훅)는 픽셀 출력이 없고 `CANONICAL_ORDER`에 티어 스테이지가 없음을 코드로 확인. **기본값: 티어 gating = `pipeline/tier.py`(신규, `run_pipeline` additive 래퍼 — `pipeline/sequence.py` 선례) + 동일성 diff = `common/equivalence.py`(REQ-INFRA-CI-4 훅) 확장으로 배치하고 T0 오케스트레이터 표면(`CANONICAL_ORDER`·`CalibKind`·`_KIND_BY_STAGE`)을 변경하지 않는다.** T9(NDT)와 같은 T0-표면-불변 계열. **run-blocking은 오직** 검토자가 티어 gating이 오케스트레이터 표면(예: `run_pipeline` 시그니처에 tier 인자 추가)을 바꿔야 한다고 판단할 경우에만 발생 — 기본은 additive 래퍼로 표면 불변. **권장 = additive 래퍼 + equivalence.py 확장, T0 표면 불변.**
2. **[확인] 동일성 diff = `common/equivalence.diff_frames` 재사용.** T0가 REQ-INFRA-CI-4로 "동일 시그니처 구현 비교 단일 진입점"을 이미 제공(구조만·수치 P2). **기본값: `diff_frames`를 그대로 재사용**하고 그 위에 정수/부동소수점 경로 분류 + 구조 판정만 얹는다(수치 bit-동일/±1 LSB 단정 P2). 순수 비교는 `common/`(pipeline import 없음), 티어 쌍 산출은 `pipeline/tier.py`, 쌍 구성 하니스는 `tests/`. **확인 필요**: 경로 분류 헬퍼를 `common/equivalence.py`에 둘지(권장 — 훅 홈) `pipeline/tier.py`에 둘지 — 순수 비교는 common, 파이프라인 실행이 필요한 티어 쌍 산출은 pipeline으로 분리. **권장 = diff_frames 재사용 + common 확장(경로 분류) + pipeline/tier.py(쌍 산출).**
3. **[확인 — 검증됨] "티어"의 분류 대상: 하드웨어 연산 능력, EV 등급 아님.** SWR-1301(CPU 코어·AVX·GPU·VRAM) + EV-401("Tier 1 결정론적 파이프라인" vs "Tier 2 전체 파이프라인")을 SWR 텍스트로 검증 — **티어는 어느 실행 경로가 도는지를 결정하는 연산 능력 티어이며, 달성 화질(MTF/DQE)을 EV min/typ/max로 매핑하지 않는다.** EV min/typ/max는 별도의 지표 합격 기준이고 티어와 독립. "강제 하향 허용·강제 상향 금지"=사용자는 더 낮은(보수적) 티어를 강제할 수 있으나 하드웨어 미지원 상위 티어는 강제 불가(구조 규칙, 수치 무관, P1 검증 가능). **권장 = 티어=연산 능력 티어 + 경로 선택; EV 등급 매핑 아님(REQ-TIER-GATE-2·CONTRACT-4).**
4. **[확인] XDET-TC-020 처리시간 하니스 = 구조만, 절대 시간 P2.** TestSpec XDET-TC-020(Tier별 처리시간, 100회 중앙값 cold/warm, EV-401 min) vs CLAUDE.md T10("절대 시간은 P2"). **기본값: cold/warm·중앙값 타이밍 하니스 구조(티어별 실행·타이밍 레코드)만 구현하고 EV-401 절대 시간 게이트(≤3s/≤5s)는 단정하지 않는다.** P1 골든 모델은 의도적으로 느림(속도 최적화 금지)이므로 절대 시간은 P1에서 무의미. 현재 skeleton도 TC-020을 "tier gating structure (T10)"로 재프레이밍함. **권장 = 타이밍 하니스 구조 성립 + 절대 시간 P2 이연(REQ-TIER-TIMING-2).**
5. **[확인] DL 경로(SWR-1303) = Gen 2 예약, 미구현.** ONNX Runtime·모델 해시 검증·fallback 자동 전환(런타임 오류·티어 미달 시)은 Gen 2 항목. **기본값: DL 경로 런타임을 구현하지 않는다**(CLAUDE.md "Gen 2 항목(DL, ADR)은 구현하지 않는다"). 티어 taxonomy에 DL 티어 이름을 문서상 예약할 수 있으나(향후 Gen 2 훅 위치 표시) ONNX·모델 해시·fallback 로직은 없다. **확인 필요**: DL 티어 이름을 enum에 예약(placeholder)할지 완전 배제할지 — 예약은 향후 Gen 2 위치 표시에 유용하나 미구현 명시 필수. **권장 = DL 경로 미구현, taxonomy 예약 이름만(선택), Exclusions 명시.**
