---
id: SPEC-GUIDING-001
version: 0.1.0
status: draft
created: 2026-07-11
updated: 2026-07-11
author: drake.lee
priority: high
issue_number: 33
---

# SPEC-GUIDING-001 — 정본 지침(guiding) 취득세트 요구사항 (P1 수치 golden 검증 blocker 해제)

XDET 영상처리 SW P1의 **취득 요구(acquisition-requirements) SPEC**. SPEC-REALDATA-001(#29) 플러밍 검증에서 `images/에드로지16BIT/` **샘플** 세트를 엔진에 통과시킨 결과, 코드 경로는 실측 형상(3072²)에서 정상 구동하나 **P1 수치 골든 검증(EV 기준)은 이 샘플로 사실상 검증 불가**함이 문서 대조로 확정되었다(전 측정 항목 MISSING/PARTIAL, DQE 3입력 온전 공급 0개). 본 SPEC은 정본 "지침(guiding)" 취득세트가 **무엇을 어떤 조건으로** 취득해야 P1 DoD(EV-101~106/201~205/301~303, XDET-TC-001~019 수치 판정)를 unblock하는지 딥리서치 근거(이슈 #33) 기반으로 EARS로 명세한다. **본 SPEC은 소프트웨어 구현이 아니다** — 코드·파이프라인 스테이지·CalibKind·`process()` 시그니처를 추가하지 않으며, 취득해야 할 물리 데이터의 요구·조건·매수·추적성만 정의한다.

- 근거: GitHub 이슈 #33(딥리서치 원본: 목적·커버리지 갭 매트릭스·DQE 3입력 특수성·기준 셋업) · [OBSERVE] GHOST #32(lag 인터리브/포화 구조 제약) · `docs/XDET_measurement_protocol_v1.0.md`(선질·MTF·NPS·DQE 측정 사양) · `docs/XDET_image_acquisition_sets_v1.1.md`(취득세트 정의) · `docs/XDET_measurement_item_list_v1.0.md`(측정 항목) · `docs/XDET_EVAL_criteria_v1.1.md`(EV min/typ/max) · `docs/XDET_TestSpec_v1.0.md`(XDET-TC 정의) · `docs/XDET_RTM_v1.1.md`(요구·추적)
- 완료 정의(DoD): (1) A티어 기준 셋업(RQA5 + 교정 Ka + XN) 요구가 확정·문서화되고, (2) 최고 레버리지 2종(flat 선량 계단 · 슬랜티드 엣지)이 취득되면 MTF·NPS·DQE·gain·선형성·노이즈모델 수치 아암이 활성화되며, (3) MISSING/PARTIAL 항목이 순차 취득으로 EV-101~106/201~205/301~303 판정 가능화되고, (4) 정본 세트가 SPEC-REALDATA-001 매니페스트 규약(`usage="guiding"`)으로 등록되며, (5) 각 취득이 어떤 TC/EV를 unblock하는지 RTM 경유로 추적된다. 수치 확정·튜닝은 정본 세트 도착 후 **별도 SPEC** 소관.
- 선행/연관 SPEC: [SPEC-REALDATA-001](../SPEC-REALDATA-001/spec.md)(#29, 샘플 세트 격리 — 본 SPEC이 그 대체 정본 세트의 취득 요구를 정의) · [SPEC-DQEDOC-001](../SPEC-DQEDOC-001/spec.md)(#38, DQE=MTF²/(q·Ka·NNPS) IEC 형태 — DQE 3입력 근거)
- 구현 계획(취득 계획): [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.1.0 (2026-07-11)** — 초안 생성. GitHub 이슈 #33(딥리서치). 6개 요구 그룹(BASELINE/LEVERAGE/DQE/LAG/COVERAGE/TRACE) EARS 구조 확정, 총 36개 EARS 요구. 저작 시 확정 사항: (a) 본 SPEC은 **T-스테이지가 아니며 소프트웨어 산출물이 없다** — 물리 취득 요구·조건·매수·추적성만 정의하고, 취득세트가 어떤 XDET-TC/EV를 unblock하는지 매핑한다. (b) SPEC-REALDATA-001 QUARANTINE(샘플 세트 수치 작업 영구 제외)을 **연장** — 본 SPEC이 정의하는 정본 지침 세트만이 수치 작업의 근거가 될 수 있다. (c) TC/EV 매핑은 이슈 #33 커버리지 갭 매트릭스를 그대로 형식화하며 TestSpec/EVAL/RTM을 이름으로 교차참조한다. (d) lag 취득 구조 제약은 [OBSERVE] #32(노출/잔상 인터리브 + 포화)를 그대로 반영. status: draft (수치 확정 작업 착수 전까지 유지).

## Environment / Assumptions

- 본 SPEC은 **T-스테이지·소프트웨어 구현이 아니다.** `CANONICAL_ORDER` 스테이지·`process(XFrame,CalibSet,Params)->XFrame` 시그니처·신규 `CalibKind`·`_KIND_BY_STAGE`·신규 모듈이 전혀 없다. 산출물은 **물리 취득세트의 요구·조건·매수·추적성 명세**뿐이며, 검증은 도착한 후보 지침 세트를 매니페스트 체크리스트에 대조하는 관측(SUPPLIED/MISSING)이다.
- 본 SPEC은 **SPEC-REALDATA-001 QUARANTINE을 연장**한다 — `images/에드로지16BIT/` 샘플 세트는 수치 작업에서 영구 제외(비정본, 플러밍 전용)이며, 본 SPEC이 정의하는 정본 "지침(guiding)" 취득세트만이 수치 작업의 근거가 될 수 있다. 정본 세트는 `usage="guiding"`로 등록되어 샘플 세트(`usage="sample-plumbing"`)와 구분된다(SPEC-REALDATA-001 매니페스트 규약).
- **정본 지침 세트는 P1 수치 골든 BLOCKER 해제의 전제조건**이다. 세트 도착 전까지 골든 모델 수치 정확도 검증은 **합성 팬텀 경로로만 유효**하다(CLAUDE.md T1 원칙: 실측 도착 전 합성 데이터로 엔진 자체 검증). 현 P1 상태의 정직한 재정의 = 구현 완료 + 플러밍 검증 완료, 그러나 **수치 정확도 검증은 정본 세트 도착 전까지 blocked**.
- **A티어 기준 셋업(REQ-GUIDING-BASELINE)은 다른 모든 취득의 선행 필수 전제**다 — RQA5 빔질·교정 Ka 실측·XN 확정이 확립되지 않으면 어떤 항목도 수치 판정을 활성화할 수 없다.
- lag 취득 구조는 [OBSERVE] #32의 관측 사실(GHOST 계열은 직접노출/잔상 인터리브 + 포화)을 반드시 반영해야 한다 — 미래 IRF(지수합 M=3~4) 피팅은 계열을 노출/잔상 쌍으로 분해하고 포화 프레임을 진폭 추정에서 제외해야 하므로, 취득 자체가 이 구조를 지원해야 한다.
- DQE 형태는 SPEC-DQEDOC-001에서 정정된 IEC 62220-1 형태 `DQE(f) = MTF²(f) / (q · Ka · NNPS(f))`(무차원)를 전제로 한다 — q는 IEC 표값 조달 가능, Ka는 표값이 없어 교정 이온챔버 실측이 필수.
- 참조 문서(이름으로 교차참조): `docs/XDET_measurement_protocol_v1.0.md`(측정 사양) · `docs/XDET_image_acquisition_sets_v1.1.md`(취득세트) · `docs/XDET_measurement_item_list_v1.0.md`(측정 항목) · `docs/XDET_EVAL_criteria_v1.1.md`(EV 기준) · `docs/XDET_TestSpec_v1.0.md`(XDET-TC) · `docs/XDET_RTM_v1.1.md`(추적).

### 샘플 세트가 프로토콜과 어긋난 지점 (정본 취득 시 반복 금지)

이슈 #33이 문서 대조로 확정한, 샘플 세트가 측정프로토콜과 어긋난 지점 — 정본 취득 시 반복하면 안 된다.

1. **acrylic_step DN/선량 축 불정합** — 45kV/100mA/2.5mAs 정기법 고정인데 판 1~5장에 "선량 8.5→0.85µGy(10×)" 라벨이나 중심 DN은 약 7%만 하락. 정기법이면 관출력 불변이므로 선형성 ground truth로 사용 불가 → REQ-GUIDING-LEVERAGE-1은 **관출력 변조 flat 선량 계단 + 각 단계 선량 실측치**를 요구한다(REQ-GUIDING-LEVERAGE-4가 라벨-only 취득을 거부).
2. **ghost 포화 + 단일노출** — SWR-401 명시 금지 조건. 클리핑이 지수감쇠 곡선을 파괴해 IRF 불가(#32) → REQ-GUIDING-LAG-2가 거부.
3. **NPS 3매 vs ≥16매** — FFT 앙상블 부족으로 저주파 NPS 편향 → REQ-GUIDING-DQE-2가 선량점당 ≥16매 요구.
4. **CalSet +bias 증가(+84→+308)** — 레벨 의존 gain/offset 잔차 관측 → 정본 flat 선량 계단으로 재확인(REQ-GUIDING-LEVERAGE-1).
5. **min_dose 단일점** — α,σ는 다점 선량계단 회귀 필요 → REQ-GUIDING-COVERAGE-4가 다점 회귀 입력 요구.
6. **벤더 `_result.raw`** — 다른 알고리즘·다른 출력 스케일(max≈10944 vs 65535) → 골든/티어 diff 기준 부적격(SPEC-REALDATA-001 REQ-REALDATA-CONTRACT-3 준수, 정본 세트도 동일).

## Requirements (EARS)

### REQ-GUIDING-BASELINE — A티어 기준 셋업 (선행 필수 전제) (측정프로토콜 §선질, EVAL §0, XDET-TC-001~019 공통 전제)

- **REQ-GUIDING-BASELINE-1 (Ubiquitous)** — 정본 지침 취득세트는 RQA5 빔질에서 취득되어야 한다: 관전압 70~74kV + 부가필터 **Al 21mm(type-1100, 순도 99.0%)**, **SID ≥ 1.5m**, 조사야 16×16cm, **grid 미장착**(측정프로토콜 §선질/§1).
- **REQ-GUIDING-BASELINE-2 (Event-Driven)** — WHEN RQA5 빔질을 확립하면, THEN 관전압은 **HVL 실측**으로 확정되어야 한다 — 부가필터·HVL이 RQA5 규격에 부합함을 실측으로 입증한다.
- **REQ-GUIDING-BASELINE-3 (Ubiquitous)** — 검출기면 air kerma(Ka)는 **교정 이온챔버로 실측**되어야 하며(후방산란 제외), DQE 절대 산출(REQ-GUIDING-DQE)의 입력으로 기록되어야 한다.
- **REQ-GUIDING-BASELINE-4 (Event-Driven)** — WHEN 취득 선량을 설정하면, THEN 각 취득은 **3점 선량 XN/2 · XN · 2XN**(XN≈8.73µGy, 자사 정격으로 확정)으로 구성되어야 한다.
- **REQ-GUIDING-BASELINE-5 (Event-Driven)** — WHEN offset/gain 보정 효과를 검증하려면, THEN 해당 취득은 offset/gain 보정 **전·후 각각**으로 취득되어야 한다.
- **REQ-GUIDING-BASELINE-6 (Unwanted)** — IF 부가필터로 초고순도 Al(예: 순도 99.999%)를 사용하면, THEN 이를 거부해야 한다 — 저주파 mottle을 유발하므로 type-1100 순도 99.0%를 요구한다.
- **REQ-GUIDING-BASELINE-7 (Unwanted)** — IF 명목 kV 값만으로 빔질을 확정(HVL 실측 생략)하려 하면, THEN 이를 거부해야 한다 — 빔질 확정은 HVL 실측을 요구한다(REQ-GUIDING-BASELINE-2).

### REQ-GUIDING-LEVERAGE — 최고 레버리지 2종 (먼저 취득 시 다수 아암 동시 활성화) (SWR-202/701, EV-101/102, XDET-TC-001/002/011)

- **REQ-GUIDING-LEVERAGE-1 (Event-Driven)** — WHEN gain 다점·NPS·DQE 분모·선형성·노이즈모델 수치 아암을 동시 활성화하려면, THEN 지침 세트는 **flat-field 선량 계단**(1/8·1/4·1/2·1·2·4·8× 중 **6~8단계, 단계당 ≥10매 + 각 단계 선량 실측치**)을 공급해야 한다(SWR-202 gain K≥3 · SWR-701 노이즈모델 · EV-101 · XDET-TC-001/011).
- **REQ-GUIDING-LEVERAGE-2 (Event-Driven)** — WHEN MTF·SRb·DQE 분자 수치 아암을 활성화하려면, THEN 지침 세트는 **슬랜티드 엣지**(W 2mm 또는 납/스틸/구리 후판, 검출기 밀착, **수평·수직, 1.5~3° 미세경사**, 방향·선량당 ≥5매)를 공급해야 한다(측정프로토콜 §MTF · EV-102 · XDET-TC-002).
- **REQ-GUIDING-LEVERAGE-3 (Unwanted)** — IF 엣지 취득이 45° 배치 또는 알루미늄 엣지로 구성되면, THEN 이를 거부해야 한다 — 측정프로토콜 §MTF는 1.5~3° 미세경사 + 고감쇠 엣지를 요구한다.
- **REQ-GUIDING-LEVERAGE-4 (Unwanted)** — IF flat 선량 계단이 각 단계 **선량 실측치 없이** 라벨(정격)만으로 구성되면, THEN 이를 거부해야 한다 — gain 선형성·DQE 분모·노이즈모델 회귀에 실측 선량이 필수이다(샘플 acrylic_step DN/선량 축 불정합 반복 금지).

### REQ-GUIDING-DQE — DQE 3입력 특수성 (측정프로토콜 §DQE, IEC 62220-1, EV-101, XDET-TC-001)

- **REQ-GUIDING-DQE-1 (Event-Driven)** — WHEN DQE(f)를 산출하려면, THEN 지침 세트는 세 입력을 **모두** 공급해야 한다: MTF(f)(슬랜티드 엣지, REQ-GUIDING-LEVERAGE-2), NPS(f)(flat ≥16매 앙상블 × 3 선량점, REQ-GUIDING-LEVERAGE-1 기반), **교정 Ka**(검출기면 실측, REQ-GUIDING-BASELINE-3) — DQE = MTF²/(q·Ka·NNPS)(IEC 62220-1, SPEC-DQEDOC-001 정정 형태).
- **REQ-GUIDING-DQE-2 (Ubiquitous)** — NPS 입력은 선량점당 **≥16매 flat 앙상블**이어야 한다 — 3매는 FFT 앙상블 부족으로 저주파 NPS 편향을 유발한다.
- **REQ-GUIDING-DQE-3 (State-Driven)** — WHILE q는 IEC 표값으로 조달 가능하지만 Ka는 표값이 없는 동안, Ka는 **교정 이온챔버 실측**으로만 공급되어야 한다 — 절대 선량 미확정 시 DQE 절대값 산출이 불가하다.
- **REQ-GUIDING-DQE-4 (Unwanted)** — IF DQE 3입력 중 하나라도(MTF 분자 · ≥16매 NPS · 교정 Ka) 결여되면, THEN DQE 수치 판정을 활성화된 것으로 간주해서는 안 된다 — 현 샘플 상태는 온전 공급 0개이다.

### REQ-GUIDING-LAG — lag/ghost 취득 구조 제약 (SWR-401~404, [OBSERVE] #32, EV-104, XDET-TC-004/005)

- **REQ-GUIDING-LAG-1 (Event-Driven)** — WHEN first-frame lag·IRF 피팅 수치 아암을 활성화하려면, THEN 지침 세트는 **비포화 다중노출 step-response**(포화의 **2~90% 범위** 복수 노출, 프레임 간격 기록, ≥5회)를 공급해야 한다(SWR-401 · EV-104 · XDET-TC-004).
- **REQ-GUIDING-LAG-2 (Unwanted)** — IF lag 취득이 **포화(65535 clip) 프레임** 또는 **단일노출**로 구성되면, THEN 이를 거부해야 한다 — SWR-401 명시 금지 조건이며, 클리핑이 지수감쇠 곡선을 파괴해 IRF 진폭 추정이 불가하다([OBSERVE] #32).
- **REQ-GUIDING-LAG-3 (Ubiquitous)** — lag 계열은 **노출/잔상 쌍(pair)으로 분해 가능**하도록 배선·기록되어야 한다 — 직접노출 프레임을 자극(stimulus), 후속 잔상 프레임을 응답(response)으로 명확히 구분하여([OBSERVE] #32의 인터리브 구조 사실) step-response 입력을 구성할 수 있어야 한다.
- **REQ-GUIDING-LAG-4 (Event-Driven)** — WHEN Ghost 시간계단 수치 아암(EV-104, XDET-TC-005)을 활성화하려면, THEN 지침 세트는 **납판 반차폐 강노출 후 균일 조사 직후/1분/5분** 세트를 공급해야 한다.
- **REQ-GUIDING-LAG-5 (State-Driven)** — WHILE 계열에 포화 프레임이 존재하는 동안(예: 의도적 강노출 자극 프레임), 그 포화 자극과 비포화 응답(잔상) 프레임은 취득 기록에서 **구분·표시**되어야 한다 — IRF 진폭 추정이 비포화 응답 프레임에서 수행될 수 있도록([OBSERVE] #32).

### REQ-GUIDING-COVERAGE — 잔여 MISSING/PARTIAL 항목의 정본 취득 (커버리지 갭 매트릭스 → 양성 요구) (EV-101~106/201~205/301~303, XDET-TC-003/006~010/012/013/015~019)

- **REQ-GUIDING-COVERAGE-1 (Event-Driven)** — WHEN offset 보정 입력(EV-101)을 활성화하려면, THEN dark 프레임을 **온도 3구간 × 시점 4회 × 시점당 ≥20매**로 취득해야 한다.
- **REQ-GUIDING-COVERAGE-2 (Event-Driven)** — WHEN 결함 화소 E2597 7종 분류 검증(EV-103, XDET-TC-003)을 활성화하려면, THEN **dark ≥50매 + flat ≥50매 raw 스택**을 공급해야 한다(dead/over-under/non-uniform 등 7종 분류).
- **REQ-GUIDING-COVERAGE-3 (Event-Driven)** — WHEN 라인노이즈 검출·보정(EV-105, XDET-TC-006)을 활성화하려면, THEN **전용 저선량 세트**(XN/8~XN/4, **≥20매**)를 공급해야 한다.
- **REQ-GUIDING-COVERAGE-4 (Event-Driven)** — WHEN 분산-평균 다점 회귀로 노이즈모델(α,σ)을 확정(SWR-701, XDET-TC-011)하려면, THEN 다점 선량계단(REQ-GUIDING-LEVERAGE-1의 flat 선량 계단)을 공급해야 한다 — 단일 저선량점으로는 회귀가 불가하다.
- **REQ-GUIDING-COVERAGE-5 (Event-Driven)** — WHEN NDT SNRn·SRb(20% dip)·IQI 판정(EV-301, XDET-TC-018)을 활성화하려면, THEN **duplex wire + 단선 IQI + 용접시편**을 **kV·노출 3점 × 5매 + 적산용 연속 프레임**으로 공급해야 한다.
- **REQ-GUIDING-COVERAGE-6 (Event-Driven)** — WHEN 대조도-두께 지표(CSa/SMTR)(EV-303, XDET-TC-019)를 활성화하려면, THEN **E2597 6단 step wedge(강/알루미늄) + 두께 경사 시편**을 공급해야 한다.
- **REQ-GUIDING-COVERAGE-7 (Event-Driven)** — WHEN grid 억제 검증(EV-203, XDET-TC-015/016)을 활성화하려면, THEN grid 장착 취득을 **밀도 3부류(f_grid < 3.57 / ≈ / > lp/mm, aliased 필수)**로, 정렬·미세경사, **grid당 ≥5매** 공급해야 한다.
- **REQ-GUIDING-COVERAGE-8 (Event-Driven)** — WHEN scatter/virtual grid 검증(EV-202, XDET-TC-017)을 활성화하려면, THEN **아크릴/물 두께 계단**을 **grid 유/무 쌍**으로 공급해야 한다.
- **REQ-GUIDING-COVERAGE-9 (Event-Driven)** — WHEN 구조물 오보정(EV-105, XDET-TC-007)·포화 경계(EV-106, XDET-TC-008)·기하 잔차(EV-106, XDET-TC-009)를 활성화하려면, THEN **금속 막대·판 3배치 × 5매**(구조물), **경계 구도 3 × 5매**(포화), **격자 팬텀 3위치 × 3매 + 실측 치수**(기하)를 공급해야 한다.
- **REQ-GUIDING-COVERAGE-10 (Event-Driven)** — WHEN 자동윈도우·IQA·CDRAD 판정(EV-205, XDET-TC-010/012/013)을 활성화하려면, THEN **부위별 다구도(≥10) 임상 모사 + CDRAD**를 **표준 + 저선량 계단**으로 공급해야 한다.
- **REQ-GUIDING-COVERAGE-11 (Unwanted)** — IF 어떤 항목이라도 요구 매수·조건 미달(예: NPS < 16매, flat 계단 < 10매/단계, offset dark < 20매/시점, grid 밀도 3부류 미충족, aliased 부류 누락)로 공급되면, THEN 해당 항목의 수치 아암을 활성화된 것으로 간주해서는 안 된다.

### REQ-GUIDING-TRACE — 추적성 · 격리 · 등록 (RTM, SPEC-REALDATA-001 매니페스트 규약)

- **REQ-GUIDING-TRACE-1 (Ubiquitous)** — 각 취득 요구는 그것이 unblock하는 TC/EV(XDET-TC-001~019, EV-101~106/201~205/301~303)에 **RTM 경유로 매핑**되어야 한다.
- **REQ-GUIDING-TRACE-2 (Ubiquitous)** — 정본 지침 세트는 SPEC-REALDATA-001 매니페스트 규약에 따라 **`usage="guiding"`**로 등록되어야 하며, 샘플 세트(`usage="sample-plumbing"`)와 구분되어야 한다.
- **REQ-GUIDING-TRACE-3 (State-Driven)** — WHILE 정본 지침 세트가 도착하기 전인 동안, 골든 모델 수치 검증은 **합성 팬텀 경로로만 유효**하며(수치 골든 BLOCKER 유지), 샘플 세트 기반 실측 아암은 sanity 전용이어야 한다(SPEC-REALDATA-001 QUARANTINE).
- **REQ-GUIDING-TRACE-4 (Event-Driven)** — WHEN 정본 지침 세트가 도착·등록되면, THEN 그것이 unblock하는 각 TC/EV 수치 판정의 BLOCKER 해제 조건이 충족된 것으로 기록되어야 한다 — 수치 확정·튜닝은 별도 SPEC 소관이다.
- **REQ-GUIDING-TRACE-5 (Unwanted)** — IF 본 SPEC 범위 내에서 수치 확정·EV 임계 조정·파라미터([B]/[T]/[P]) 튜닝을 수행하려 하면, THEN 이를 거부해야 한다 — 본 SPEC은 취득 요구 정의만 담당하며, 수치 작업은 지침 세트 도착 후 별도 SPEC에서만 수행한다.

## Exclusions (What NOT to Build)

- **소프트웨어 산출물 없음** — 코드·모듈·`process(XFrame,CalibSet,Params)->XFrame` 시그니처·파이프라인 스테이지(`CANONICAL_ORDER`)·신규 `CalibKind`·`_KIND_BY_STAGE`를 추가하지 않는다. 본 SPEC은 물리 취득 요구 명세이지 구현 WP가 아니다.
- **샘플 세트로 수치 작업 없음(격리 연장, HARD)** — `images/에드로지16BIT/` 샘플 세트로 [B]/[T]/[P] 파라미터 유도·피팅·튜닝, 골든/정본/기대 수치 레퍼런스, EV 임계·허용오차·보정 상수 설정, 알고리즘/모듈 수치 거동 변경을 하지 않는다(SPEC-REALDATA-001 REQ-REALDATA-QUARANTINE 준수).
- **수치 확정·튜닝 없음(본 SPEC 범위 밖)** — 정본 지침 세트로 실제 MTF/NPS/DQE/IRF/α,σ 수치를 확정하거나 파라미터를 튜닝하는 작업은 세트 도착 후 **별도 SPEC**에서만 수행한다. 본 SPEC은 "무엇을 어떤 조건으로 취득해야 하는가"만 정의한다.
- **날조 데이터 없음** — 취득세트는 실제 물리 취득으로만 공급되어야 하며, 합성/날조 프레임을 정본 지침 세트로 등록하지 않는다(합성 팬텀은 세트 도착 전 검증 경로일 뿐 정본이 아니다).
- **EV 판정 임계 변경 없음** — EVAL v1.1 EV min/typ/max 판정 수치를 건드리지 않는다. 본 SPEC은 그 판정을 **가능화**할 취득 요구를 정의할 뿐 임계 자체를 정의·조정하지 않는다(측정=판정 분리).
- **벤더 `_result` 사용 없음** — 정본 세트도 벤더 후처리 `_result` 프레임을 골든/티어 diff 기준으로 사용하지 않는다(다른 알고리즘·스케일, SPEC-REALDATA-001 REQ-REALDATA-CONTRACT-3).
- **물리 취득 실행 자체는 본 SPEC의 코드 작업이 아님** — 실제 촬영·선량 측정·시편 제작은 실험/하드웨어 활동이다. 본 SPEC은 그 활동의 요구·조건·매수·검증 체크리스트를 명세한다.

## 결정 필요/확인 사항

저작 시 대부분 확정되었으며, 실측[B] 대기 항목이 아니므로 후속 작업을 차단하지 않는다.

1. **[확정 — RESOLVED]** 무-코드 범위 — 본 SPEC은 취득 요구/조건/매수/추적성 명세이며 소프트웨어 산출물이 없다. 검증은 도착한 후보 지침 세트를 매니페스트 체크리스트에 대조하는 관측(SUPPLIED/MISSING)으로 수행한다. **rationale**: 이슈 #33의 목적은 "무엇을 어떤 조건으로 취득해야 unblock되는가"의 근거 기반 명세이며, 수치 작업은 명시적으로 별도 SPEC 소관이다.
2. **[확인 필요]** 매니페스트 완결성 검사 방식 — 정본 세트 도착 시 각 요구의 매수·조건 충족을 검증하는 방법. **가정 기본값**: 문서화된 매니페스트 체크리스트(acceptance.md)에 대한 **수동/문서 대조**(무-코드, 이슈 #33 무-코드 제약 준수). **확인 대상**: 향후 `usage="guiding"` 엔트리의 매수·조건만 대조하는 **비수치 구조 완결성 체커**(카운트·조건만, 파라미터 유도·수치 피팅 없음 — QUARANTINE 안전)를 별도 툴링 SPEC으로 추가할지 사용자 선호. 기본은 **무-코드 문서 체크리스트**.
3. **[확인 필요]** 우선순위 취득 순서 — 이슈 #33의 A→B→C→D 우선순위(A티어 전제 → 최고 레버리지 2종 → B/C/D 확장)를 그대로 채택. **확인 대상**: 실험 자원 제약에 따라 B/C/D 내 항목 순서를 조정할지(레버리지 2종·A티어는 고정). 기본은 이슈 #33 순서.
