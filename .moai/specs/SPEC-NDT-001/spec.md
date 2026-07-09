---
id: SPEC-NDT-001
version: 0.1.1
status: draft
created: 2026-07-09
updated: 2026-07-09
author: drake.lee
priority: high
issue_number: 10
labels: [T9, WP10, NDT]
---

# SPEC-NDT-001 — T9 WP10 NDT: 실시간 SNRn 적산(Welford) + IQI 자동 판독 + 두께 보정

XDET 영상처리 SW P1의 열 번째 작업 T9. NDT(비파괴검사) 검사 성적 산출 능력 **WP10(SWR-1201~1204, FR-N001~N003)**을 구현한다. 핵심은 세 가지다 — (1) **실시간 SNRn 적산**: 프레임 스트리밍 평균을 **Welford 온라인 알고리즘**(실행 카운트·평균·M2 증분 갱신)으로 누적해 전체 스택을 메모리에 보유하지 않고 프레임 1매씩 실행 SNR을 추정하고, SNRn = SNR × 88.6[µm]/SRb_image로 정규화하며, 목표 SNRn 도달 시 취득 종료 신호와 shot별 SNRn·SRb 자동 로그(ISO 17636-2 기록 요구)를 산출한다(SWR-1201). (2) **IQI 자동 판독·리포트**: duplex-wire SRb 판독(SWR-1202)은 **T1(SPEC-METRICS-001) `metrics/ndt.read_duplex_srb`에 이미 구현되어 있어 재사용**하고, 단선(single-wire) IQI 자동 검출·최소 가시 wire 판정 + **Class A/B 합부 자동 출력**(검사 성적 양식)을 신규 구현한다(SWR-1204). (3) **두께 보정**: 대구경 저주파 프로파일(형태학적 열림 또는 대형 Gaussian, 스케일 TBD-[T])을 감산해 두께 유래 저주파 구배를 평탄화하되 결함 대역(고역)을 보존한다(SWR-1203).

**T9는 픽셀 보정 처리 모듈이 아니라 측정·리포트 능력이다.** SWR-1201(적산=스트리밍 측정)·SWR-1204(리포트)·SWR-1202(판독)는 픽셀 출력이 없고, `pipeline/orchestrator.CANONICAL_ORDER`에 NDT 스테이지가 없음을 코드로 확인했다. 따라서 T9는 T1 지표 계층을 확장하는 방식(`metrics/ndt.py` + Welford 공용 컴포넌트)으로 배치하고, T0 오케스트레이터 표면(`CANONICAL_ORDER`·`CalibKind`·`_KIND_BY_STAGE`)을 **변경하지 않는다**. 이는 T2~T8(전용 스테이지 신설) 대비 T9의 근본 아키텍처 구별점이다(결정 1, 「결정 필요/확인 사항」 1). 두께 보정(SWR-1203)만 픽셀을 변환하나 NDT 측정 섹션에 속하고 DoD(XDET-TC-019)가 "보정이 SRb를 열화시키지 않는가"라는 측정 관점이므로 measurement 계층 로컬 연산(측정용 평탄화 사본)으로 둔다.

- 근거: SWR-1201~1204(NDT, FR-N001~N003) · SWR-000-6~9(아키텍처, 특히 SWR-000-9 공용 컴포넌트 ④ 강건 통계 · ② 히스토그램/조사야 "NDT 리포트" 소비자 명시) — `docs/XDET_SWR_spec_v1.2.md`; 등급(부록 A-2): SWR-1201 SNRn 88.6µm = **[S]**, SWR-1202 20% dip = **[S]**, SWR-1203 두께 보정 스케일 개념 = **[C]**
- EVAL v1.1: XDET-EV-301(SNRn 처리 후 Class A 충족 min / ≥130 typ · Duplex wire IQI 요구 wire 판독 min) · XDET-EV-303(SMTR 고객 스펙 충족 min · CSa ≤2% min, ASTM E2597) · XDET-EV-102 min(알고리즘 후 SRb 열화 ≤10% · MTF@Nyquist 유지율 ≥90%) — 두께 보정 SRb 보호 가드레일
- TestSpec: XDET-TC-018(VV-011, SNRn/SRb 자동 산출 + IQI 자동 판독 정확도, GDS-NDT 시편[BAM5류 용접 시편], EV-301 min) · XDET-TC-019(VV-011, 두께보정 후 CSa/SMTR + SRb 보호, GDS-step wedge, EV-303 · EV-102 min)
- 완료 정의(DoD): **합성 팬텀으로 SNRn/SRb/IQI 자동 판독 정확도 + 두께 보정 SRb 보호를 선검증** — 실측 GDS 도착 전, (a) **[하드 DoD] SNRn/SRb/IQI 정확도**(XDET-TC-018): 기지 SNRn·SRb·최소 가시 wire를 담은 합성 NDT 입력에서 실시간 적산 SNRn·duplex SRb·단선 IQI 최소 가시 wire·Class A/B 합부가 기지값을 허용오차([T]) 내로 재현. (b) **[하드 DoD] Welford 스트리밍 정확도**: Welford 온라인 실행 평균/분산이 배치 산출(`common/robust_stats.temporal_mean_std`)과 허용오차([T]) 내로 수치 등가. (c) **[하드 DoD] 두께 보정 SRb 보호**(XDET-TC-019): 기지 두께 구배 + 주입 고역 결함을 담은 합성 step-wedge에서 두께 보정 후 SRb 열화 ≤ EV-102 min(≤10%) · MTF@Nyquist 유지율 ≥ EV-102 min(≥90%)을 T1 `metrics/mtf`(tests/ 소비)로 결정론적 이진 판정 + CSa(달성 대비감도) proxy 산출. XDET-TC-018/019를 pytest skeleton(skip)에서 실동작 케이스로 전환. SMTR 완전 특성화·관찰자(EV-303 고객 스펙·EV-204)는 인허가 이연(PARTIAL)
- 선행 계약: [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md) — XFrame(불변) 입력·읽기 전용 소비 계약, 마스크 스택 비트플래그(SATURATION=2/INTERPOLATION=4), `common/` 공용 컴포넌트(SWR-000-9), import-linter 레이어링(`metrics → common` 단방향, `modules/`·`pipeline/` import 금지), `CANONICAL_ORDER`; [SPEC-METRICS-001](../SPEC-METRICS-001/spec.md) — **T1 지표 엔진의 직접 전제**: `metrics/ndt.read_duplex_srb`(SWR-1202 duplex SRb, 20% dip)·`compute_snr`/`compute_snrn`(SNRn=SNR×88.6/SRb 공식)·`metrics/mtf`(SRb 보호 검증)·`common/robust_stats.temporal_mean_std`(Welford 등가 배치 레퍼런스)·`MetricResult`/`MetricReadError`/`require_param`(반환 구조·명시 실패·필수 파라미터 접근) 재사용. T1 Exclusions가 SWR-1201 실시간 적산·종료 신호와 CSa/SMTR·두께 보정을 **명시적으로 "T9(WP10 NDT)"로 이연**함
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.1.1 (2026-07-09)** — plan-audit iteration 1 (FAIL 0.55, D1 critical) 반영: D1(VALIDATE-3 EARS 비정형 서술 → shall절 재구성)·D2(VALIDATE-1 acceptance 미추적 → Scenario 4 태그 추가)·D4(THICK-1 이접 기법절 → Params `thickness_method` 선택으로 재구성, 기법 상세는 plan.md 이관)·D5(T1 인용 부정확 → 정확한 원문으로 정정). Ambiguity 1(두께 보정 출력 성격) 사용자 확인 완료 — **내부 측정 전용**(하류 표시 프레임 아님) 확정, 결정 1을 [확정 — RESOLVED]로 승격.
- **v0.1.0 (2026-07-09)** — 초안 생성. GitHub 이슈 #10. 5개 요구 그룹(ACCUM/THICK/IQI/CONTRACT/VALIDATE) EARS 구조 확정. 핵심 범위 결정:
  1. **T9 = 측정·리포트 계층(metrics/), 처리 스테이지 신설 없음([placement — 잠재적 run-blocking if rejected])**: SWR-1201(적산=측정)·SWR-1204(리포트)·SWR-1202(판독)는 픽셀 출력이 없고 `CANONICAL_ORDER`에 NDT 스테이지가 없음을 코드로 확인 → T9는 `metrics/ndt.py` 확장(적산·IQI 리포트) + `common/robust_stats.py`(Welford) 확장으로 배치하고 T0 오케스트레이터 표면을 변경하지 않는다. **T2~T8의 전용 스테이지 부분수열-삽입 패턴과 반대**로, T9는 T0 표면 불변이 기본이다. 두께 보정(SWR-1203)만 픽셀을 변환하나 NDT 측정 섹션 소속 + TC-019 DoD가 SRb 열화 측정 관점 + T1이 "두께보정 지표"로 이연했으므로 metrics-로컬 연산(측정용 평탄화 사본)으로 둔다. 「결정 필요/확인 사항」 1.
  2. **Welford 온라인 누적 → 공용 컴포넌트 ④ 강건 통계(`common/robust_stats.py`)**: SWR-000-9 중복 금지 + `temporal_mean_std`(배치 시간축 통계)가 이미 그 모듈에 있는 선례(비강건 시간축 통계의 home) → 온라인 평균·분산 누적기를 `common/robust_stats.py`에 1회 정의하고 `metrics/ndt`가 소비. T9는 이 스텁의 첫 소비자. 「결정 필요/확인 사항」 2.
  3. **골든 모델의 스트리밍 의미**: "스트리밍"=프레임 1매씩 증분 누적(Welford)으로 배치와 동일한 실행 평균/분산을 전체 스택 미보유로 산출; metrics-측 상태 보유 누적기(파이프라인 `StatefulModule` 아님, SWR-000-7 무관)로 실현하고 tests/(또는 NDT 리포트 드라이버)에서 외부 구동; "실시간 취득 종료 신호"=반환 결정값(목표 도달 프레임 인덱스)이며 하드웨어 취득 제어가 아님. lag(T4)의 프레임-시퀀스 연산과 유사하나 NDT 적산은 측정(metrics/, 오케스트레이터/`pipeline/sequence.py` 미경유)이고 lag는 보정(modules/, `pipeline/sequence.py` 경유)이라는 점에서 구별. 「결정 필요/확인 사항」 3.
  4. **duplex SRb(SWR-1202) 재사용 + 단선 IQI(SWR-1204) 신규**: duplex-wire SRb는 T1 `read_duplex_srb`에 이미 구현되어 재사용(재구현 금지, SWR-000-9); 단선 IQI 최소 가시 wire 판정 + Class A/B 리포트는 신규. Class A/B 임계는 ISO 17636-2 표준·고객 규격 Params([S]/[P]). 「결정 필요/확인 사항」 5.
  5. **CSa/SMTR 범위(EV-303)**: TC-019 결정론적 하드 게이트 = SRb 보호(EV-102 min, T1 `metrics/mtf`) + 고역 결함 대역 보존; CSa는 step-wedge 기지 대비 측정 가능 proxy(min resolvable contrast); SMTR "고객 스펙 충족" 완전 ASTM E2597 특성화 = 재질·고객 의존 → PARTIAL(인허가 이연, POST-001/GRID-001 PARTIAL 선례). 「결정 필요/확인 사항」 4.

## Environment / Assumptions

- Python 3.11+, numpy/scipy 기반 float 골든 모델(tech.md). **속도 최적화 금지 — 정확도 단일 목표**(P2에서 최적화). Welford 온라인 누적도 정확도(배치 등가) 목적이며 성능 목적이 아니다.
- 대상 프레임: 3072×3072 / 3072×2560, 16-bit unsigned raw, pitch 140µm, Nyquist f_N = 3.57 lp/mm(EVAL v1.1 §0 파생 상수).
- **T1(SPEC-METRICS-001)과의 경계 — 본 SPEC의 핵심 전제.** T1은 NDT 지표 중 **정적(단일 프레임/스택) readout**만 제공했다: `read_duplex_srb`(duplex 20% dip → SRb, SWR-1202), `compute_snr`/`compute_snrn`(SNRn=SNR×88.6/SRb 공식, SWR-1201 수식부). T1 Exclusions가 명시 이연한 항목이 정확히 T9 범위다 — (i) SWR-1201의 **Welford 프레임 스트리밍 적산 · 실시간 SNRn · 목표 도달 취득 종료 신호 · shot별 자동 로그**(T1 line 119: "T9(WP10 NDT 모듈)로 이연"), (ii) **CSa/SMTR · 두께 보정 지표**(EV-303/XDET-TC-019, T1 line 118: "태스크 명시 7개 지표 밖"), (iii) 단선 IQI **Class A/B 리포트**(SWR-1204). T9는 SWR-1202 SRb 판독과 SNRn 정규화 공식은 **T1을 재사용**하고, 그 위에 스트리밍 적산·두께 보정·IQI 리포트를 얹는다.
- **실측 GDS(GDS-NDT 용접 시편 · GDS-step wedge) 도착 전 — 합성 팬텀으로 엔진을 선검증한다.** 기지 SNRn(주입 평균·분산·프레임 수)·기지 SRb(기지 dip 위치)·기지 최소 가시 wire·기지 두께 구배 + 주입 고역 결함을 담은 합성 입력을 생성하고, 산출이 기지값을 명시 허용오차([T]) 내로 재현하는지로 정확도를 확인한다(T1 "합성 검증 컨텍스트" 용어 계승 — 합성 팬텀 fixture 시험 실행을 가리키며, T0 검증 모드[validation_mode, float64 병행 버퍼]와는 별개 개념).
- **아키텍처 배치 — metrics 계층, T0 표면 불변.** T9 산출부는 처리 모듈이 아니다: `process(XFrame,CalibSet,Params)->XFrame` 계약을 따르지 않고, XFrame(단일/스택/시퀀스)을 읽기 전용으로 소비해 NDT 지표·리포트 구조를 반환한다. 의존 방향 `metrics → common` 단방향(import-linter). **`CANONICAL_ORDER`에 스테이지를 추가하지 않고, 신규 `CalibKind`·`_KIND_BY_STAGE` 배선을 신설하지 않는다**(결정 1). T9는 검출기 캘리브레이션을 요구하지 않으므로 CalibSet 종류 신설도 없다(대조: T5 NOISE·T8 SCATTER는 신규 kind 신설).
- **스트리밍 상태는 metrics 내부 상태이지 파이프라인 모듈 상태가 아니다.** Welford 누적기는 실행 카운트·평균·M2를 보유하나, 이는 metrics 계층의 상태 보유 측정 도구이며 SWR-000-7의 "명시 선언 처리 모듈(lag 등) 내부 상태 + 컨테이너 직렬화" 계약(StatefulModule serialize/load)과 무관하다. 누적기는 오케스트레이터·`pipeline/sequence.py`를 거치지 않는다.
- **공용 컴포넌트 첫 소비자(Welford).** `common/robust_stats.py`는 현재 배치 `temporal_mean_std`(전체 스택 mean/std)만 보유하고 온라인(증분) 누적이 없다. T9는 온라인 평균·분산 누적(Welford)의 첫 실 정의를 유발하나, 구현 코드는 `common/robust_stats.py`에 두고 `metrics/`에 중복하지 않는다(SWR-000-9, POST pyramid·GRID Welch-PSD 첫 소비자 확장 선례).
- **파라미터 정책(HARD).** 전 임계·튜닝·표준 상수는 Params로 외부화(하드코딩 금지): 88.6µm SNRn 정규화 = **[S]**(T1 `P_SRB_NORM_UM` 재사용), 20% dip = **[S]**(T1 `P_DIP_THRESHOLD` 재사용, 부록 A-2는 20% dip을 [S]로 등재 — T1 주석의 [P] 표기는 본 SPEC에서 [S]로 정정하며 값은 ISO 규정 고정), 두께 보정 스케일(형태학적 열림 반경 / Gaussian σ) = **TBD-[T]**(SWR-1203 명시), SNRn 취득 종료 목표·Class A/B SNRn 최소치·요구 wire 번호 = ISO 17636-2 표준·고객 규격 **[S]/[P]**, Welford 등가 허용오차·SRb 보호 허용오차·CSa proxy 허용오차·단선 wire 가시성 임계 = **[T]**. 신규 파라미터는 SWR 부록 A(TBD)/부록 A-2(등급) 등재 요청.
- **측정=판정 분리.** EV 합격/불합격 판정 수치(EVAL v1.1 EV-301/303/102)는 엔진 외부 주입. 엔진은 지표·리포트 값을 산출할 뿐 EV 게이트 임계를 내장하지 않는다. Class A/B 임계·취득 종료 목표는 표준/고객 규격 Params로서 **리포트 산출에 소비**하되(SWR-1204/1201이 명령하는 출력), EV-301 시험 합격선은 외부에 둔다.

## Requirements (EARS)

### REQ-NDT-ACCUM — Welford 스트리밍 적산 · 실시간 SNRn · 취득 종료 신호 · shot 로그 (SWR-1201, EV-301, XDET-TC-018)

- **REQ-NDT-ACCUM-1 (Ubiquitous)** — 실시간 SNR 추정은 프레임 스트리밍 평균의 **Welford 온라인 누적**(실행 카운트·평균·M2 증분 갱신)으로 산출되어야 하며, 전체 프레임 스택을 메모리에 보유하지 않고 프레임을 1매씩 순차 소비해 실행 평균·분산을 갱신해야 한다(SWR-1201 적산). 누적기는 metrics 계층의 상태 보유 측정 도구이며 `process(XFrame,CalibSet,Params)->XFrame` 처리 모듈이 아니고, 오케스트레이터·`pipeline/sequence.py`를 거치지 않는다(SWR-000-7 파이프라인 모듈 상태와 무관).
- **REQ-NDT-ACCUM-2 (Event-Driven)** — WHEN 각 신규 프레임이 누적기에 투입되면, THEN 시스템은 사용자 지정 ROI(또는 자동 검출 균일 영역)의 실행 평균·표준편차를 갱신하고, 그 시점의 실시간 SNR과 SNRn = SNR × 88.6[µm] / SRb_image를 산출해야 한다(SWR-1201; 88.6µm는 [S] 상수로 Params 소비, T1 `compute_snrn` 공식 재사용). SRb_image는 duplex-wire 판독(REQ-NDT-IQI-1, T1 `read_duplex_srb` 재사용)에서 소비한다.
- **REQ-NDT-ACCUM-3 (Event-Driven)** — WHEN 실행 SNRn이 목표 SNRn(ISO 17636-2 Class/고객 규격, Params 주입)에 도달하면, THEN 시스템은 취득 종료 신호(목표 도달 결정 + 도달 프레임 인덱스)를 산출해야 한다. 이 신호는 골든 모델에서 반환 결정값이며 하드웨어 취득 제어 신호가 아니다. 목표 SNRn은 Params로 외부화하며(하드코딩 금지), EV-301 시험 합격선과는 구별된다(측정=판정 분리).
- **REQ-NDT-ACCUM-4 (Event-Driven)** — WHEN 각 shot의 적산이 갱신되면, THEN 시스템은 ISO 17636-2 기록 요구에 따라 shot별 SNRn·SRb를 자동 로그 항목(shot 인덱스·SNRn·SRb·프레임 수)으로 산출해야 한다(SWR-1201 "shot별 SNRn·SRb 자동 로그").
- **REQ-NDT-ACCUM-5 (State-Driven)** — WHILE 합성 검증 컨텍스트인 동안, 기지 프레임 시퀀스(주입 평균·분산·프레임 수)에 대해 Welford 온라인 실행 평균·분산이 배치 산출(`common/robust_stats.temporal_mean_std`)과 허용오차([T]) 내로 수치 등가함을 보여야 한다(골든 모델 스트리밍 정확도 게이트).
- **REQ-NDT-ACCUM-6 (Unwanted)** — IF 균일 영역 ROI가 프레임 경계를 벗어나거나 유효 균일 화소가 부족하거나 실행 표준편차가 0이면, THEN 시스템은 산출을 거부하고 명시 오류를 발생시켜야 한다(무단 SNR 산출 금지 — T1 `compute_snr` zero-noise 명시 실패 선례 계승).

### REQ-NDT-THICK — 두께 보정 (저주파 프로파일 감산 · 고역 결함 대역 보존) (SWR-1203, EV-303/EV-102, XDET-TC-019)

- **REQ-NDT-THICK-1 (Event-Driven)** — WHEN 두께 변이 시편(예: step wedge) 프레임이 주어지면, THEN 시스템은 대구경 저주파 프로파일(스케일 [T] — Params 주입)을 추정·감산해 두께 유래 저주파 구배를 평탄화한 프레임을 산출해야 한다(SWR-1203; 추정 기법은 형태학적 열림 또는 대형 Gaussian 중 Params `thickness_method`로 선택 — 기법 상세는 plan.md HOW). 두께 보정은 NDT 측정용 평탄화 연산으로서 metrics 계층에서 수행하며, 입력 XFrame을 변경하지 않고 평탄화 결과를 반환한다.
- **REQ-NDT-THICK-2 (Ubiquitous)** — 두께 보정은 감산 프로파일을 저주파 성분에 한정하고 결함 대역(고역)을 보존해야 한다(SWR-1203 "결함 대역 보존"). 고역 결함 신호·SRb 열화 여부는 REQ-NDT-VALIDATE-2(EV-102 min)로 검증한다.
- **REQ-NDT-THICK-3 (Unwanted)** — IF 입력에 유효한 저주파 두께 구배가 없거나(평탄 입력) 추정 스케일이 프레임 크기를 초과하면, THEN 시스템은 감산을 수행하지 않고 수치 무변화로 통과시키며 경고를 발생시켜야 한다(무단 고역 왜곡 금지 — 조건 불충족 시 결함 대역 손상 방지).

### REQ-NDT-IQI — Duplex SRb 재사용 + 단선 IQI 자동 판독 + Class A/B 리포트 (SWR-1202 재사용 + SWR-1204, EV-301, XDET-TC-018)

- **REQ-NDT-IQI-1 (Ubiquitous)** — SRb_image는 T1 duplex-wire 20% dip 판독(`metrics/ndt.read_duplex_srb`, SWR-1202 / REQ-METRICS-NDT-1)을 **재사용**하여 소비해야 하며, T9는 이를 재구현하지 않아야 한다(SWR-000-9 중복 금지). 20% dip 미검출 시 판독 실패(무단 SRb 추정 금지)는 T1 계약(REQ-METRICS-NDT-4)을 그대로 승계한다.
- **REQ-NDT-IQI-2 (Event-Driven)** — WHEN 단선(single-wire, ISO 19232 wire-type) IQI 프로파일이 주어지면, THEN 시스템은 wire 요소를 자동 검출하고 최소 가시 wire(minimum visible wire)를 판정해야 한다(SWR-1204). 가시성 판정 임계는 Params로 외부화한다([T]/[P]).
- **REQ-NDT-IQI-3 (Event-Driven)** — WHEN 실시간 적산 SNRn(REQ-NDT-ACCUM), duplex SRb(REQ-NDT-IQI-1), 최소 가시 wire(REQ-NDT-IQI-2)가 산출되면, THEN 시스템은 ISO 17636-2 Class A/B 요구(SNRn 최소치 + 요구 wire 판독, Params 주입 [S]/[P])와 대조해 Class A/B 합부를 자동 판정하고 검사 성적 리포트(shot별 SNRn·SRb·최소 가시 wire·Class 합부)를 산출해야 한다(SWR-1204 IQI 리포트). Class 임계는 표준/고객 규격 Params로 소비하되, EV-301 시험 합격선은 엔진 외부에 둔다(측정=판정 분리).
- **REQ-NDT-IQI-4 (State-Driven)** — WHILE 합성 검증 컨텍스트인 동안, 기지 최소 가시 wire·기지 SNRn·기지 SRb를 담은 합성 IQI/균일 입력에 대해, 산출 최소 가시 wire·Class A/B 합부가 기지값을 재현해야 한다(XDET-TC-018 IQI 자동 판독 정확도, EV-301 min).

### REQ-NDT-CONTRACT — metrics 계층 계약 · T0 표면 불변 · 파라미터/판정 외부화 · 공용 컴포넌트 (SWR-000-6~9, CLAUDE.md T9)

- **REQ-NDT-CONTRACT-1 (Ubiquitous)** — T9 NDT 산출부는 처리 모듈이 아니다. `process(XFrame,CalibSet,Params)->XFrame` 계약을 따르지 않고, XFrame(단일/스택/시퀀스)을 읽기 전용으로 소비해 NDT 지표·리포트 구조를 반환하는 순수 측정 계층이며, 의존 방향은 `metrics → common` 단방향이어야 한다(`modules/`·`pipeline/` import 금지 — T1 REQ-METRICS-CORE-1/3 승계).
- **REQ-NDT-CONTRACT-2 (Ubiquitous)** — T9는 고정 파이프라인 순서(`pipeline/orchestrator.CANONICAL_ORDER`)에 스테이지를 추가하지 않고, 신규 `CalibKind`·`_KIND_BY_STAGE` 배선을 신설하지 않아야 한다. NDT는 측정·리포트 능력이며 픽셀 보정 스테이지가 아니므로 T0 오케스트레이터 표면을 변경하지 않는다(결정 1 — T2~T8 전용 스테이지 부분수열-삽입 패턴과의 구별점).
- **REQ-NDT-CONTRACT-3 (Ubiquitous)** — 모든 임계·튜닝·표준 상수(88.6µm [S], 20% dip [S], 두께 보정 스케일 [T], SNRn 목표·Class A/B 임계 [S]/[P], Welford 등가·SRb 보호·CSa proxy·wire 가시성 허용오차 [T])는 Params로 주입되어야 하며 엔진 코드에 하드코딩되어서는 안 된다(T1 REQ-METRICS-CORE-4 승계, CLAUDE.md 파라미터 정책).
- **REQ-NDT-CONTRACT-4 (Ubiquitous)** — EV 합격/불합격 판정 수치(EVAL v1.1 EV-301/303/102)는 엔진 외부에서 주입되어야 하며, 엔진은 지표·리포트 값을 산출할 뿐 EV 게이트 임계를 내장하지 않아야 한다(측정=판정 분리, T1 REQ-METRICS-CORE-5 승계).
- **REQ-NDT-CONTRACT-5 (Ubiquitous)** — Welford 온라인 누적(온라인 평균·분산)은 공용 컴포넌트 ④ 강건 통계(`common/robust_stats.py`)에 1회 정의되고 참조로만 사용되어야 한다(SWR-000-9). T9는 이 스텁의 첫 소비자로서 온라인 누적의 첫 실 정의를 유발하나, 구현 코드는 `common/`에 두고 `metrics/`에 중복하지 않아야 한다(`temporal_mean_std`가 이미 시간축 통계의 home인 선례).

### REQ-NDT-VALIDATE — 합성 검증 · TC 게이트 (XDET-TC-018/019, EV-301/303/102)

- **REQ-NDT-VALIDATE-1 (State-Driven)** — WHILE 합성 검증 컨텍스트인 동안, 실측 GDS-NDT 시편(BAM5류 용접 시편) 도착 전, 기지 SNRn·SRb·최소 가시 wire를 담은 합성 NDT 입력에 대해 SNRn/SRb 자동 산출 + IQI 자동 판독 정확도가 기지값을 허용오차([T]) 내로 재현함을 보여야 한다(XDET-TC-018, EV-301 min: SNRn Class A 충족 · duplex wire IQI 요구 wire 판독). XDET-TC-018을 pytest skeleton(skip)에서 실동작 케이스로 전환한다.
- **REQ-NDT-VALIDATE-2 (State-Driven)** — WHILE 합성 검증 컨텍스트인 동안, 기지 두께 구배 + 주입 고역 결함 신호를 담은 합성 step-wedge에 대해, 두께 보정 후 **[하드 DoD] SRb 보호** — 보정 후 SRb 열화가 EV-102 min(≤10%) 이하이고 MTF@Nyquist(3.57 lp/mm) 유지율이 EV-102 min(≥90%) 이상임을 T1 `metrics/mtf` 엔진(tests/에서 소비)으로 결정론적 이진 판정하고, **CSa proxy** — step-wedge 기지 대비로 달성 대비감도(min resolvable contrast)를 측정해 EV-303 min(CSa ≤2%) 대비 값을 산출함을 보여야 한다(XDET-TC-019, EV-303 · EV-102 min). XDET-TC-019를 pytest skeleton에서 실동작 케이스로 전환한다.
- **REQ-NDT-VALIDATE-3 (Ubiquitous)** — 시스템은 SMTR(대상 재질 두께 범위, EV-303 "고객 스펙 충족")의 완전한 ASTM E2597 특성화 없이도 SRb 보호(EV-102 min) + CSa proxy만으로 XDET-TC-019의 결정론적 게이트가 판정 가능**해야 한다**(완전 SMTR 특성화·관찰자 판독[EV-204]은 재질·고객 규격 의존이므로 실측/인허가 트랙으로 이연 — PARTIAL, POST-001·GRID-001 PARTIAL 선례).

## Exclusions (What NOT to Build)

- **처리 스테이지 신설 없음(T0 표면 불변)** — `CANONICAL_ORDER`에 NDT 스테이지를 추가하지 않고, 신규 `CalibKind`·`_KIND_BY_STAGE`를 신설하지 않는다. T9는 측정·리포트 계층이며 픽셀 보정 스테이지가 아니다(결정 1). T2~T8의 전용 스테이지 부분수열-삽입과 대조된다.
- **duplex-wire SRb 재구현 없음** — SWR-1202 duplex SRb(20% dip)는 T1 `metrics/ndt.read_duplex_srb`를 재사용한다. T9는 재구현하지 않는다(SWR-000-9).
- **SNRn 정규화 공식 재구현 없음** — SNRn = SNR × 88.6/SRb 공식(SWR-1201 수식부)은 T1 `compute_snrn`을 재사용한다. T9는 그 위에 Welford 스트리밍 적산·종료 신호·로그만 얹는다.
- **실측 데이터 취득·판독 없음** — GDS-NDT 용접 시편·GDS-step wedge 실측 판독은 2단계 실측 도착 후. 본 T9는 합성 팬텀(기지값 주입)만으로 엔진을 검증한다.
- **완전 SMTR 특성화·관찰자 연구 없음** — EV-303 SMTR "고객 스펙 충족" 완전 ASTM E2597 특성화와 EV-204 관찰자 판독은 재질·고객 의존 → 인허가 이연(PARTIAL). T9는 SRb 보호(EV-102) + CSa proxy만 결정론적 게이트로 삼는다.
- **ADR / Gen 2 없음** — EV-302(ADR: Recall/False call)·DL 기반 자동 결함 인식은 P1 범위 밖(CLAUDE.md "Gen 2 항목(DL, ADR)은 구현하지 않는다"). TC-018/019는 EV-302를 참조하지 않는다.
- **실제 취득 하드웨어 종료 제어 없음** — SWR-1201 취득 종료 "신호"는 목표 도달 반환 결정값이며, 실제 검출기 취득 중단 제어(펌웨어/하드웨어)는 범위 밖.
- **EV 게이트 임계 내장 없음** — EV-301/303/102 min/typ/max 판정 수치는 EVAL 기준서/Params 참조 주입. 엔진은 값·리포트만 산출한다.
- **속도 최적화 없음** — Welford 온라인 누적은 배치 등가(정확도) 목적이며, 메모리·속도 최적화는 P2.

## 결정 필요/확인 사항

아래는 SWR 본문·T1 구현과의 대조에서 남는 열린 질문과 가정 기본값이다. 1은 잠재적 run-blocking(기각 시 T0 표면 변경), 2~5는 확인 항목이다. run 착수 전 확정하고 HISTORY로 접는다.

1. **[확정 — RESOLVED] T9 배치: metrics 계층(T0 표면 불변).** SWR-1201(적산=측정)·SWR-1204(리포트)·SWR-1202(판독)는 픽셀 출력이 없고 `CANONICAL_ORDER`에 NDT 스테이지가 없음을 코드로 확인. 두께 보정(SWR-1203)의 출력 성격은 사용자 확정 사항이었다 — FRD XDET-FR-N002 "weld seam 고역 강조" 문구가 하류 표시용 딜리버러블 가능성을 시사했으나, **사용자 결정: 두께 보정 결과는 SRb/CSa 판정용 내부 측정 사본 전용이며 파이프라인 출력 프레임으로 하류에 흘러가지 않는다.** "고역 강조"는 결함 대역을 손상하지 않는 보존 제약으로 해석한다(REQ-NDT-THICK-2). 따라서 T9는 `metrics/ndt.py` 확장 + `common/robust_stats.py`(Welford) 확장으로 배치하고 T0 오케스트레이터 표면(`CANONICAL_ORDER`·`CalibKind`·`_KIND_BY_STAGE`)을 변경하지 않는다. 향후 하류 딜리버러블이 요구되면 별도 후속 이슈(T10+)로 전용 스테이지를 신설한다.
2. **[확인] Welford 배치: `common/robust_stats.py`(기본) vs `metrics/ndt.py` 로컬.** SWR-000-9 중복 금지 + `temporal_mean_std`(배치 시간축 통계)가 이미 `common/robust_stats.py`에 있는 선례 → **기본값: 온라인 평균·분산 누적기를 `common/robust_stats.py`에 추가**. Welford는 강건(median/MAD)이 아닌 정확 평균/분산이나, `temporal_mean_std`도 비강건이므로 해당 모듈은 실질 "공용 통계"의 home이다. 등가 게이트: Welford-online ≡ `temporal_mean_std`-batch(REQ-NDT-ACCUM-5). **권장 = common/robust_stats.py**(첫 소비자 확장, POST pyramid·GRID fft_psd 선례).
3. **[확인] 골든 모델 스트리밍 의미 · 구동.** **기본값**: "스트리밍"=프레임 1매씩 증분 누적으로 배치 동일 실행 평균/분산을 전체 스택 미보유로 산출; metrics-측 상태 보유 누적기(파이프라인 `StatefulModule` 아님)로 실현하고 tests/(또는 NDT 리포트 드라이버)에서 외부 구동; "취득 종료 신호"=반환 결정값(도달 프레임 인덱스). 누적 프레임은 파이프라인 출력 프레임일 수 있으나 누적 자체는 metrics 연산이다. lag(T4)의 프레임-시퀀스 연산과 유사하나 NDT 적산은 측정(metrics/, `pipeline/sequence.py` 미경유), lag는 보정(modules/, `pipeline/sequence.py` 경유)이라는 점에서 구별. **권장 = metrics-로컬 누적기 + tests/ 구동, `pipeline/sequence.py` 결합 불요.**
4. **[확인] CSa/SMTR 범위(EV-303, TC-019).** 현재 `metrics/`에 SMTR/CSa 엔진 부재를 확인. **기본값**: TC-019 결정론적 하드 게이트 = SRb 보호(EV-102 min, T1 `metrics/mtf`) + 고역 결함 대역 보존; CSa는 step-wedge 기지 대비 측정 가능 proxy(min resolvable contrast from CNR); SMTR "고객 스펙 충족" + 완전 ASTM E2597 특성화 = 재질·고객 의존 → PARTIAL(인허가 이연). **확인 필요**: 완전 SMTR/CSa 엔진 신설이 요구되면 범위 확대. **권장 = SRb 보호 하드 게이트 + CSa proxy 측정 + SMTR PARTIAL.**
5. **[확인] IQI 판독 분할.** duplex-wire SRb(SWR-1202)는 T1 `read_duplex_srb`에 이미 구현 → **재사용(재구현 금지)**; 단선 IQI(SWR-1204, 최소 가시 wire + Class A/B 리포트)는 신규. Class A/B 임계는 ISO 17636-2 표준·고객 규격 Params([S]/[P]). 신규 파라미터(두께 스케일 [T], SNRn 목표·Class 임계 [S]/[P], 각종 허용오차 [T], wire 가시성 임계 [T]/[P])는 SWR 부록 A/A-2 등재 요청. **권장 = SWR-1202 재사용 + SWR-1204 신규.**
