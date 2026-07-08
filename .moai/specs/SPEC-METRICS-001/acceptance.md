# SPEC-METRICS-001 — 인수 기준 (Acceptance Criteria)

DoD: **합성 팬텀 입력으로 기지값 재현** — 실측 도착 전, 기지값 주입 합성 데이터로 각 지표 산출이 그 기지값을 지표별 허용오차([T] 파라미터) 내로 재현. 모든 기준은 관측 가능(테스트 출력 · 산출 값 · 경고/거부 발생)해야 한다. EV 판정 수치는 엔진 외부 주입(참조), 재현 허용오차 자체는 [T] 파라미터로 외부화한다.

## Given-When-Then 시나리오

### Scenario 1 — 엔진 계약: 순수 소비 · 메타 첨부 (REQ-METRICS-CORE)
- **Given** 유효한 입력 XFrame(불변)과 Params/CalibSet(주입 상수)가 주어져 있다.
- **When** 임의 지표 산출 함수가 실행된다.
- **Then** 입력 XFrame(pixel · mask · noise · history)은 변경되지 않고, 함수는 지표 결과 구조를 반환하며, 결과에는 산출 조건 메타(선질 · 선량 수준 · 온도 · 필터 · 보정 상태 · ROI · params_hash · calibset_id)가 결정론적으로 첨부되어 있다. EV min/typ/max 임계는 결과에 내장되지 않는다(외부 주입).

### Scenario 2 — MTF edge method 기지값 재현 (REQ-METRICS-MTF)
- **Given** `tests/metrics/phantoms/`가 해석적 기지 MTF를 갖는 이상 slanted edge(경사 1.5~3°, 서브픽셀 위치)와 그 기지 MTF(f)를 반환한다.
- **When** 엔진이 자동 edge 각도 추정 → oversampled ESF → LSF(미분+창함수) → FFT → presampled MTF를 산출한다.
- **Then** 산출 presampled MTF(f)가 기지값을 허용오차 내로 재현하며(특히 MTF@Nyquist 3.57 lp/mm), 각도 추정은 인력 개입 없이 수행된다.

### Scenario 3 — NPS/NNPS 및 DQE 기지값 재현 (REQ-METRICS-NPS)
- **Given** 주입 분산의 백색 잡음(평탄 NPS) 또는 주입 상관 커널의 유색 잡음(해석적 NPS 형상) 균일 프레임 다수 매와, 기지 q · Ka, 그리고 DQE 조성을 위한 기지 MTF(해석적)가 주어져 있다.
- **When** 엔진이 중앙 256×256 ROI 다중(반중첩) 추출 → 트렌드 제거 → 2D FFT 앙상블 평균 → 1D 축추출로 NPS를 산출하고, NNPS 정규화 및 DQE(f) = MTF²·q·Ka/NPS를 산출한다.
- **Then** NPS(f) 크기·형상, NNPS, DQE(f)(peak · 1 lp/mm · 2 lp/mm)가 각 기지값을 허용오차 내로 재현한다.

### Scenario 4 — 3선량 NPS/DQE 산출 (REQ-METRICS-NPS-4)
- **Given** 3개 선량 수준(XN/2, XN, 2XN)의 균일 세트가 주어져 있다.
- **When** 엔진이 선량 수준별 산출을 수행한다.
- **Then** 선량별 NPS/NNPS/DQE가 각각 산출되고, 각 결과에 해당 선량 수준 메타가 첨부된다.

### Scenario 5 — First-frame lag 기지값 재현 (REQ-METRICS-LAG)
- **Given** 지수합 IRF(M=3~4, 주입 계수)로 컨볼루션한 합성 프레임 시퀀스와 해석적 first-frame lag %가 주어져 있다.
- **When** 엔진이 노출 종료 후 첫 잔상 프레임 신호를 직전 노출 신호 대비 백분율로 산출한다.
- **Then** 산출 first-frame lag %가 기지값을 허용오차 내로 재현한다.

### Scenario 6 — Bad-pixel E2597 7종 분류 재현 (REQ-METRICS-DEFECT)
- **Given** 기지 좌표·E2597 종류(dead / over-under-range / noisy / lag / non-uniform 등)를 주입한 합성 dark/flat 스택이 주어져 있다.
- **When** 엔진이 6× median [S] 기준과 [P] 임계(Params 주입)로 7종 분류 맵·분율을 산출한다.
- **Then** 분류 맵이 기지 결함 좌표·종류를 재현하고, 종류별 분율과 검출 누락률이 산출된다(EV-103 검출 누락 기준 대비 값 제공).

### Scenario 7 — SNRn + duplex-wire SRb 재현 (REQ-METRICS-NDT)
- **Given** 기지 dip 위치의 합성 duplex-wire 프로파일(20% dip)과 기지 SNR 균일 영역(주입 평균·표준편차)이 주어져 있다.
- **When** 엔진이 duplex 20% dip으로 SRb_image를 판독하고 SNRn = SNR × 88.6/SRb를 산출한다.
- **Then** 산출 SRb_image, SNR, SNRn이 각 기지값을 허용오차 내로 재현한다.

### Scenario 8 — Ghost 잔상 CNR 산출 (REQ-METRICS-LAG-5, 필수)
- **Given** 고대비 패턴 후 균일 조사 ghost 시퀀스와, 주입된 기지 잔상(ghost residual) 및 해석적 기지 CNR이 주어져 있다.
- **When** 엔진이 잔상 CNR을 산출한다.
- **Then** 산출 잔상 CNR이 기지값을 허용오차([T] 파라미터) 내로 재현한다(EV-104 ghost 판정 산출부, XDET-TC-005).

## Optional 요구 조건부 인수 기준 (WHERE 해당 입력이 제공되면)

### Scenario 9 — 방향별 MTF (REQ-METRICS-MTF-5, Optional)
- **Given** 수평·수직 2방향 slanted edge 입력.
- **When** WHERE 해당 입력이 제공되면, 엔진이 방향별 MTF를 각각 산출한다.
- **Then** 수평·수직 방향별 presampled MTF(f)가 각각 산출되고 결과 메타에 방향이 표기된다. 입력 미제공 시 본 기준은 적용되지 않는다.

### Scenario 10 — 라인노이즈 스펙트럼 정량 (REQ-METRICS-NPS-8, Optional)
- **Given** 라인노이즈 스펙트럼 정량 요청과 균일 프레임 입력.
- **When** WHERE 해당 입력이 제공되면, 엔진이 행/열 방향 1D NPS의 저주파 이상 피크 성분을 추출한다.
- **Then** 행/열 저주파 이상 피크 성분(EV-105 보조)이 산출된다. 미요청·미제공 시 본 기준은 적용되지 않는다.

## Edge Cases (부정/경계 케이스)

### EC-1 — MTF edge 각도 이상 (REQ-METRICS-MTF-3)
- **Given** (a) edge 각도가 허용 범위(1.5~3°) 밖(0°/90° 근처 포함)으로 추정되는 입력과, (b) 허용 범위 내이나 경계 근접(범위 내 마진 [T] 이내)으로 추정되는 입력, 두 종류.
- **When** 엔진이 각도 추정·유효성 검사를 실행한다.
- **Then** 범위 밖 입력(a)은 거부하고 명시 오류를 발생시키며, 경계 근접 입력(b)은 산출하되 경고를 표시한다(결정론적 분기 — 비결정적 택일 없음, 무단 산출 금지).

### EC-2 — NPS ROI 프레임 경계 · 균일영역 부족 (REQ-METRICS-NPS-6)
- **Given** 256×256 ROI가 프레임 경계를 벗어나거나 유효 균일 영역이 부족한 입력.
- **When** 엔진이 ROI 추출 전 유효성 검사를 실행한다.
- **Then** 해당 ROI를 거부하고 경고한다.

### EC-3 — DQE 분모 0-나눗셈 (REQ-METRICS-NPS-7)
- **Given** 특정 주파수에서 NPS(f)가 0에 근접하는 입력.
- **When** 엔진이 DQE(f) = MTF²·q·Ka/NPS를 산출한다.
- **Then** 해당 주파수의 DQE를 무효로 표시하고 0-나눗셈을 발생시키지 않는다.

### EC-4 — 전영역 dead / 스택 매수 미달 (REQ-METRICS-DEFECT-5)
- **Given** 결함 통계용 dark/flat 스택 매수가 최소치 미만이거나 ROI 전체가 dead 픽셀인 입력.
- **When** 엔진이 통계 산출 전 최소 조건을 검사한다.
- **Then** 산출을 거부하고 경고한다(부정확 통계 무단 산출 금지).

### EC-5 — Duplex 20% dip 미검출 (REQ-METRICS-NDT-4)
- **Given** duplex-wire 프로파일에서 20% dip이 검출되지 않는 입력(no dip found).
- **When** 엔진이 SRb 판독을 시도한다.
- **Then** 판독 실패를 명시적으로 반환한다(무단 SRb 추정·기본값 대체 금지).

### EC-6 — Lag 포화 전제 위반 (REQ-METRICS-LAG-4)
- **Given** 시퀀스가 포화 근접 노출 전제(신호 수준 · 프레임레이트 메타)를 만족하지 않는 입력.
- **When** 엔진이 시퀀스 전제 조건을 검사한다.
- **Then** 경고를 발생시킨다(전제 미충족 산출값의 신뢰도 표시).

### EC-7 — 부작용/의존 위반 (REQ-METRICS-CORE-2, -3)
- **Given** 입력 XFrame 변경을 시도하거나 `modules/`·`pipeline/`을 import하는 위반 코드가 있다.
- **When** XFrame 불변 검사(읽기 전용 버퍼)와 import-linter 정적 검사가 실행된다.
- **Then** 입력 변경은 read-only 버퍼로 차단·검출되고, 의존 위반은 import-linter로 열거되어 FAIL 한다.
- **참고** 전역 상태·파일 우회 금지는 자동 검출 대상이 아닌 설계 규칙으로 코드 리뷰 게이트에서 다룬다(REQ-METRICS-CORE-2 자동 검출 범위 밖 — 본 EC의 검증 범위는 XFrame 읽기 전용 + import-linter로 한정).

## 품질 게이트 / Definition of Done

- [ ] `metrics/` 패키지 배치(result · mtf · nps · dqe · lag · defect_stats · ndt), `metrics → common` 단방향 import-linter 계약 통과
- [ ] `MetricResult` 컨테이너: 값 + 산출 조건 메타(선질·선량·온도·필터·보정상태·ROI·params_hash·calibset_id) 결정론적 첨부(CORE-6)
- [ ] `common/` 첫 실 구현(fft_psd·robust_stats·histogram_fov) — metrics 소비 요건 최소 구현, metrics/에 중복 없음(CORE-8)
- [ ] 전 상수(q·Ka·XN·88.6µm·허용오차·결함 임계) Params/CalibSet 외부화 — 하드코딩 0건(CORE-4)
- [ ] EV min/typ/max 판정 수치 엔진 미내장 — 외부 주입 확인(CORE-5)
- [ ] MTF: 자동 각도추정 + 기지 MTF 재현(Scenario 2), 각도 이상 거부(EC-1)
- [ ] NPS/NNPS/DQE: 256×256 ROI 앙상블 기지값 재현(Scenario 3), 3선량 산출(Scenario 4), ROI 경계·0-나눗셈 거부(EC-2·EC-3)
- [ ] first-frame lag: 기지 IRF 재현(Scenario 5), ghost 잔상 CNR 재현(Scenario 8, 필수), 포화 전제 위반 경고(EC-6)
- [ ] bad-pixel: E2597 7종 분류 재현·누락률(Scenario 6), 스택 미달/전영역 dead 거부(EC-4)
- [ ] SNRn+duplex: 20% dip → SRb, SNRn 재현(Scenario 7), dip 미검출 명시 실패(EC-5)
- [ ] CORE 계약: XFrame 불변 소비·부작용 금지·의존 방향(Scenario 1, EC-7)
- [ ] 합성 팬텀 fixture(`tests/metrics/phantoms/`) 기지값 반환 + 지표별 허용오차([T]) 재현 판정
- [ ] XDET-TC-001~005 · XDET-TC-018 pytest 등록·통과 (판정 엔진 산출부)
- [ ] **합성 팬텀 전 지표 기지값 재현 PASS** — DoD
