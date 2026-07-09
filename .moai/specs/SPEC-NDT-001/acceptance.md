# SPEC-NDT-001 — 인수 기준 (Acceptance Criteria)

DoD: **합성 팬텀으로 SNRn/SRb/IQI 자동 판독 정확도(XDET-TC-018) + 두께 보정 SRb 보호(XDET-TC-019)를 선검증** — 실측 GDS 도착 전, 기지값 주입 합성 데이터로 각 산출이 기지값을 허용오차([T] 파라미터) 내로 재현. 모든 기준은 관측 가능(테스트 출력·산출 값·경고/거부 발생)해야 한다. EV 판정 수치(EV-301/303/102)는 엔진 외부 주입(참조), Class A/B·취득 종료 목표는 표준/고객 규격 Params. T9는 T0 표면(`CANONICAL_ORDER`)을 변경하지 않는다.

## Given-When-Then 시나리오

### Scenario 1 — 엔진 계약: metrics 계층 소비 · T0 표면 불변 · 판정 분리 (REQ-NDT-CONTRACT)
- **Given** 유효한 입력 XFrame(불변) 또는 XFrame 시퀀스와 Params(주입 상수: 88.6µm·20% dip·두께 스케일·SNRn 목표·Class 임계·허용오차)가 주어져 있다.
- **When** 임의 NDT 산출 함수(적산·두께 보정·IQI 리포트)가 실행된다.
- **Then** 입력 XFrame(pixel·mask·noise·history)은 변경되지 않고, 함수는 지표·리포트 결과 구조를 반환하며, `pipeline/orchestrator.CANONICAL_ORDER`에는 NDT 스테이지가 추가되지 않고 신규 `CalibKind`·`_KIND_BY_STAGE` 배선이 없으며, `metrics → common` 단방향 import-linter 계약이 통과한다(`modules/`·`pipeline/` import 0건). EV min/typ/max 판정 임계는 결과에 내장되지 않는다(외부 주입).

### Scenario 2 — Welford 온라인 누적 ≡ 배치 등가 (REQ-NDT-ACCUM-1, -5)
- **Given** `tests/metrics/phantoms/`가 주입 평균·분산의 균일 프레임 시퀀스(프레임 수 N)와 그 배치 기지 평균/분산을 반환한다.
- **When** `common/robust_stats`의 Welford 온라인 누적기가 프레임을 1매씩 순차 소비해 실행 평균·분산을 갱신한다(전체 스택 미보유).
- **Then** 최종 실행 평균·분산이 배치 산출(`common/robust_stats.temporal_mean_std`)과 허용오차([T]) 내로 수치 등가하며, Welford 구현은 `common/robust_stats.py`에 1회 배치되고 `metrics/`에 중복되지 않는다(SWR-000-9, 결정 2).

### Scenario 3 — 실시간 SNRn 적산 · 취득 종료 신호 · shot 자동 로그 (REQ-NDT-ACCUM-2, -3, -4)
- **Given** 기지 SNR 균일 영역(주입 평균·표준편차)의 프레임 시퀀스와 기지 SRb(duplex 재사용), 88.6µm[S]·목표 SNRn(Params 주입)이 주어져 있다.
- **When** 누적기가 각 신규 프레임 투입마다 실행 SNR·SNRn = SNR × 88.6/SRb(T1 `compute_snrn` 재사용)를 갱신한다.
- **Then** (a) 프레임별 실시간 SNRn이 기지 진행값을 허용오차([T]) 내로 재현하고, (b) 실행 SNRn이 목표에 도달하는 프레임에서 취득 종료 신호(도달 결정 + 프레임 인덱스)가 산출되며, (c) shot별 SNRn·SRb 자동 로그 항목(shot 인덱스·SNRn·SRb·프레임 수)이 산출된다(SWR-1201, XDET-TC-018 SNRn 산출부). 취득 종료 목표는 Params이며 EV-301 시험 합격선과 구별된다.

### Scenario 4 — duplex SRb 재사용 + 단선 IQI 최소 가시 wire + Class A/B 리포트 (REQ-NDT-IQI-1, -2, -3, -4, VALIDATE-1)
- **Given** 기지 dip 위치의 합성 duplex-wire 프로파일(20% dip), 기지 최소 가시 wire를 담은 단선(single-wire) IQI 프로파일, 기지 SNRn, ISO 17636-2 Class A/B 요구(SNRn 최소치·요구 wire 번호, Params 주입)가 주어져 있다.
- **When** 엔진이 duplex SRb를 T1 `read_duplex_srb`로 재사용 판독하고, 단선 wire 요소를 자동 검출해 최소 가시 wire를 판정하며, Class A/B 합부 리포트를 산출한다.
- **Then** 산출 SRb_image·최소 가시 wire·Class A/B 합부·검사 성적 리포트(shot별 SNRn·SRb·최소 가시 wire·Class 합부)가 기지값을 허용오차([T]) 내로 재현한다(XDET-TC-018, EV-301 min: SNRn Class A 충족 · duplex wire IQI 요구 wire 판독). Class 임계는 리포트 산출용 Params로 소비되고 EV-301 시험 합격선은 엔진 외부에 있다.

### Scenario 5 — 두께 보정: 저주파 감산 + 고역/SRb 보존 + CSa proxy (REQ-NDT-THICK-1, -2, REQ-NDT-VALIDATE-2)
- **Given** 기지 저주파 두께 구배(step wedge) + 주입 고역 결함 신호를 담은 합성 프레임과 두께 보정 스케일([T], Params 주입), EV-102 min(SRb 열화 ≤10% · MTF@Nyquist 유지율 ≥90%)·EV-303 min(CSa ≤2%)이 외부 주입되어 있다.
- **When** 엔진이 대구경 저주파 프로파일(형태학적 열림 또는 대형 Gaussian)을 감산해 두께 구배를 평탄화하고(입력 XFrame 불변, 평탄화 사본 반환), 두께 보정 후 SRb·MTF@Nyquist·CSa proxy를 T1 `metrics/mtf`(tests/ 소비)로 측정한다.
- **Then** (a) [하드 DoD] 저주파 구배가 제거되고 주입 고역 결함 신호 진폭이 허용오차([T]) 내로 보존되며, 보정 후 SRb 열화 ≤ EV-102 min(≤10%)·MTF@Nyquist 유지율 ≥ EV-102 min(≥90%)을 결정론적 이진 판정하고, (b) CSa(달성 대비감도) proxy가 step-wedge 기지 대비로 산출되어 EV-303 min(CSa ≤2%) 대비 값을 제공한다(XDET-TC-019, EV-303·EV-102 min).

## Edge Cases (부정/경계 케이스)

### EC-1 — 적산 ROI 경계 · zero-noise 거부 (REQ-NDT-ACCUM-6)
- **Given** 균일 영역 ROI가 프레임 경계를 벗어나거나 유효 균일 화소가 부족하거나 실행 표준편차가 0에 수렴하는 입력.
- **When** 누적기가 ROI 유효성·실행 표준편차를 검사한다.
- **Then** 산출을 거부하고 명시 오류(`MetricReadError`)를 발생시킨다(무단 SNR 산출 금지 — T1 `compute_snr` zero-noise 선례).

### EC-2 — 두께 구배 부재 · 스케일 초과 무변화 통과 (REQ-NDT-THICK-3)
- **Given** 유효한 저주파 두께 구배가 없는 평탄 입력, 또는 추정 스케일이 프레임 크기를 초과하는 입력.
- **When** 엔진이 두께 보정 전 구배 유효성·스케일을 검사한다.
- **Then** 감산을 수행하지 않고 수치 무변화로 통과시키며 경고를 발생시킨다(무단 고역 왜곡·결함 대역 손상 금지 — 결정론적 통과, 비결정적 택일 없음).

### EC-3 — duplex 20% dip 미검출 명시 실패 (REQ-NDT-IQI-1)
- **Given** duplex-wire 프로파일에서 20% dip이 검출되지 않는 입력(no dip found).
- **When** 엔진이 T1 `read_duplex_srb`로 SRb 판독을 시도한다.
- **Then** 판독 실패를 명시적으로 반환한다(무단 SRb 추정·기본값 대체 금지 — T1 REQ-METRICS-NDT-4 계약 승계).

## PARTIAL (인허가/실측 이연 — 결정론적 게이트 아님)

### SMTR 완전 특성화 · 관찰자 판독 (REQ-NDT-VALIDATE-3)
- SMTR(대상 재질 두께 범위, EV-303 "고객 스펙 충족")의 완전한 ASTM E2597 특성화와 관찰자 판독(EV-204)은 재질·고객 규격 의존이므로 실측/인허가 트랙으로 이연한다. T9의 결정론적 게이트는 SRb 보호(EV-102 min) + CSa proxy이며, 본 항목은 합격/불합격 이진 게이트에 포함되지 않는다(POST-001·GRID-001 PARTIAL 선례).

## 품질 게이트 / Definition of Done

- [ ] T0 표면 불변: `CANONICAL_ORDER`에 NDT 스테이지 미추가 · 신규 `CalibKind`/`_KIND_BY_STAGE` 0건(결정 1, REQ-NDT-CONTRACT-2, Scenario 1)
- [ ] `metrics → common` 단방향 import-linter 계약 통과, `modules/`·`pipeline/` import 0건 · XFrame 불변 소비(CONTRACT-1, Scenario 1)
- [ ] Welford 온라인 누적 `common/robust_stats.py` 1회 배치 · `metrics/` 중복 없음 · 배치 `temporal_mean_std` 등가([T])(CONTRACT-5·ACCUM-1·ACCUM-5, Scenario 2)
- [ ] 실시간 SNRn 적산: 프레임별 SNRn 재현 + 목표 도달 취득 종료 신호(프레임 인덱스) + shot별 SNRn·SRb 자동 로그(ACCUM-2·3·4, Scenario 3)
- [ ] duplex SRb 재사용(read_duplex_srb) + 단선 IQI 최소 가시 wire + Class A/B 리포트 기지값 재현(IQI-1·2·3·4, Scenario 4, EV-301 min)
- [ ] 두께 보정: 저주파 감산 + 고역 결함 보존 + [하드 DoD] SRb 열화 ≤ EV-102 min(≤10%)·MTF@Nyquist 유지율 ≥ EV-102 min(≥90%) 결정론적 이진(T1 metrics/mtf) + CSa proxy(THICK-1·2·VALIDATE-2, Scenario 5, EV-303·EV-102 min)
- [ ] 전 상수(88.6µm[S]·20% dip[S]·두께 스케일[T]·SNRn 목표/Class[S]/[P]·허용오차[T]) Params 외부화 — 하드코딩 0건(CONTRACT-3)
- [ ] EV min/typ/max 판정 수치 엔진 미내장 — 외부 주입 확인(CONTRACT-4)
- [ ] 경계/부정 케이스: 적산 ROI/zero-noise 거부(EC-1), 두께 구배 부재/스케일 초과 무변화 통과+경고(EC-2), duplex dip 미검출 명시 실패(EC-3)
- [ ] 합성 팬텀 fixture(`tests/metrics/phantoms/`) 기지값 반환 + 허용오차([T]) 재현 판정
- [ ] XDET-TC-018 · XDET-TC-019 pytest skeleton(skip) → 실동작 케이스 전환·통과
- [ ] SMTR 완전 특성화·관찰자(EV-303 고객 스펙·EV-204) PARTIAL 이연 문서화(VALIDATE-3)
- [ ] **합성 팬텀 SNRn/SRb/IQI 정확도 + 두께 보정 SRb 보호 재현 PASS** — DoD
