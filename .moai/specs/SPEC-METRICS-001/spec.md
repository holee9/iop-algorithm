---
id: SPEC-METRICS-001
version: 0.1.1
status: draft
created: 2026-07-09
updated: 2026-07-09
author: drake.lee
priority: high
issue_number: 2
---

# SPEC-METRICS-001 — T1 지표 산출 엔진 (metrics/)

XDET 영상처리 SW P1의 두 번째 작업 T1. 처리 모듈을 구현하지 않고, EVAL v1.1 지표의 **측정 절차를 표준 원문 근거로 자동화**하는 지표 산출 엔진(`metrics/`)을 확립한다. 엔진은 T0 프레임워크의 XFrame을 읽기 전용으로 소비하는 순수 측정 계층이며, EV 합격/불합격 판정 엔진의 산출부(XDET-TC-001~005, XDET-TC-018)를 담당한다.

- 근거: `docs/XDET_measurement_protocol_v1.0.md` 전체(구현 사양 단일 출처) · SWR-000-9(공용 컴포넌트) · SWR-1201/1202(NDT 지표) · EVAL v1.1 EV-101~104/301
- 완료 정의(DoD): **합성 팬텀 입력으로 기지값 재현** — 실측 영상 도착 전, 기지 MTF/노이즈/결함/IRF/duplex를 주입한 합성 데이터로 엔진 자체를 검증(XDET-TC-001~005·XDET-TC-018 판정 엔진의 산출부가 각 지표를 명시 허용오차 내로 재현)
- 선행 계약: [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md) — XFrame 입력·불변 계약, `common/` 공용 컴포넌트, import-linter 레이어링(`metrics → common` 단방향, `modules/`·`pipeline/` import 금지)
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.1.1 (2026-07-09)** — plan-audit iteration 1 (FAIL 0.71) 결함 12건 반영:
  - D1: REQ-METRICS-LAG-5(ghost CNR)를 Optional→Event-Driven 필수 요구로 승격, acceptance.md Scenario 8(주입 ghost 잔상 → CNR 재현) 추가, XDET-TC-005를 필수 DoD로 유지(spec·plan·acceptance 3자 정합).
  - D2: CORE-2를 SPEC-INFRA-001 DATA-2 방식으로 한정 — 자동 검출 가능 범위(XFrame 읽기 전용 위반 + import-linter 의존 방향)와 전역 상태·파일 우회(코드 리뷰 게이트 설계 규칙, 테스트 가능 AC 아님)를 분리, EC-7 정합.
  - D3: Optional 요구(MTF-5 방향별 MTF, NPS-8 라인노이즈 스펙트럼)에 조건부 AC(WHERE 해당 입력 제공 시) 추가. LAG-5는 D1로 필수화.
  - D4: CORE-6 메타 필드에 온도·필터 추가(측정프로토콜 §4), 미러 필드 목록(plan MetricResult·acceptance Scenario 1·DoD) 동기화.
  - D5: MTF 파이프라인 표기 정정 — oversampled ESF → LSF(미분+창함수) → FFT → presampled MTF(창함수는 LSF 단계, FFT 아님). spec·plan·acceptance 3파일 반영.
  - D6: 상수 등급 재분류 — q=[S](IEC 표값)·Ka=취득별 측정 입력·XN=TBD-[B]. 실측 후 치환 대상은 XN뿐.
  - D7: HISTORY·Exclusions 정정 — XDET-TC-006(라인노이즈)만 NPS Optional 흡수, XDET-TC-007(구조물 오보정률)은 무관 항목으로 T3 이연.
  - D8: "합성 검증 컨텍스트(synthetic-validation context)" 단일 용어를 Environment에 정의, T0 검증 모드(validation_mode, float64 병행 버퍼)와 구별 명시. State-Driven 요구의 단계/모드 변형 통일.
  - D9: 전 시험케이스 표기를 XDET- 접두 형식으로 통일.
  - D10: acceptance.md Scenario 3 Given에 DQE 입력용 기지 MTF(해석적) 추가.
  - D11: DEFECT-5를 "스택 매수 미달 또는 유효 픽셀 부족(예: ROI 전체 dead)"로 확장하여 EC-4 추적.
  - D12: MTF-3 + EC-1 결정론적 규칙화 — 허용 범위(1.5~3°) 밖=거부(명시 오류), 경계 근접(마진 [T] 이내)=경고("또는" 분기 제거).
- **v0.1.0 (2026-07-09)** — 초안 생성. GitHub 이슈 #2. 6개 요구 그룹(CORE/MTF/NPS/LAG/DEFECT/NDT) EARS 구조 확정. 명명된 7개 지표(MTF, NPS/NNPS, DQE, first-frame lag, bad-pixel 통계, SNRn, duplex-wire)를 6개 그룹으로 배치(DQE는 NPS 그룹에 합류 — DQE = MTF²·q·Ka/NPS로 NPS·MTF 소비, SNRn+duplex-wire는 NDT 그룹에 합류 — SRb가 SNRn 정규화에 투입). 범위 결정: CLAUDE.md T1 DoD의 광의 표기 "XDET-TC-001~009"에 대해, 본 SPEC은 태스크가 명시한 7개 지표(→ XDET-TC-001~005·XDET-TC-018)를 T1 핵심으로 한정한다. XDET-TC-006(라인노이즈 스펙트럼, EV-105)만 NPS 그룹의 Optional 부속으로 흡수하고, XDET-TC-007(구조물 오보정률)은 라인노이즈와 무관한 별개 항목으로 T3에 이연하며, XDET-TC-008/009(포화 경계·기하 잔차, EV-106)의 판정 엔진은 해당 처리 WP(T3)와 동반 개발로 이연(Exclusions 명시). status: draft (run 단계 착수 전까지 유지).

## Environment / Assumptions

- Python 3.11+, numpy/scipy 기반 float 골든 모델 (tech.md). **속도 최적화 금지 — 정확도 단일 목표**(P2에서 최적화).
- 대상 프레임: 3072×3072 / 3072×2560, 16-bit unsigned raw, pitch 140µm, Nyquist f_N = 3.57 lp/mm(EVAL v1.1 §0 파생 상수).
- **실측 영상 도착 전 — 합성 데이터로 엔진 자체를 검증한다.** 각 지표에 대해 기지값(해석적 MTF / 주입 분산·상관 / 주입 IRF / 주입 결함 좌표·종류 / 기지 dip 위치)을 담은 합성 팬텀을 생성하고, 엔진 산출이 그 기지값을 명시 허용오차 내로 재현하는지로 정확도를 확인한다(측정프로토콜 §1~2, CLAUDE.md T1 주의).
- **용어 정의 — 합성 검증 컨텍스트(synthetic-validation context)**: 본 SPEC에서 "합성 검증 컨텍스트"는 합성 팬텀 fixture 시험 실행(기지값 주입 → 재현 확인)을 가리키는 단일 용어이다. 이는 T0(SPEC-INFRA-001)의 **검증 모드(validation_mode — float64 병행 버퍼가 활성인 XFrame 상태, REQ-INFRA-DATA-1·CI-3b)**와는 **별개 개념**이다(전자는 엔진 정확도 자체 검증, 후자는 float32/float64 수치 정밀도 대조). 이하 모든 State-Driven 요구의 "합성 검증 컨텍스트인 동안"은 이 정의를 따른다.
- T0 계약 소비: 입력은 XFrame(불변)이며 엔진은 이를 변경하지 않는다. 엔진은 `common/` 공용 컴포넌트 스텁(`fft_psd` / `robust_stats` / `histogram_fov`)의 **첫 소비자**로서 이들의 실 알고리즘 첫 정의를 유발하나, 구현 코드는 `common/`에 두고 `metrics/`에 중복하지 않는다(SWR-000-9).
- 엔진은 **처리 모듈이 아니다.** `process(XFrame, CalibSet, Params) -> XFrame` 계약을 따르지 않으며, XFrame(또는 XFrame 스택/시퀀스)을 입력으로 받아 **지표 결과 구조(값 + 산출 조건 메타)**를 반환한다. 의존 방향은 `metrics → common` 단방향(import-linter).
- RQA5 공통 셋업(선질 70~74kV + Al 21mm, SID ≥1.5m, 조사야 16×16cm, 선량 3점 XN/2·XN·2XN, grid 미장착)은 **데이터 취득 조건**이다. 엔진은 취득 조건 메타를 소비하되 실제 취득은 범위 밖(측정프로토콜 §1.1).
- 물리·튜닝 상수(q(RQA5 fluence), Ka, XN, 88.6µm SRb 정규화 상수, 재현 허용오차, 결함 임계)는 CalibSet/Params로 주입한다. 등급 재분류: q는 IEC 표 기재값 **[S]**(RQA5 광자 fluence 상수), Ka는 취득별 측정 입력값(검출기면 air kerma, per-acquisition measured input), XN은 **TBD-[B]**. 이 중 실측 후 치환 대상은 **XN뿐**(자사 임상 정격 확정 후 측정프로토콜 v1.1에 명기 — protocol §5)이며(q는 표값 고정, Ka는 취득 시 측정으로 획득), 엔진은 어느 경우에도 값만 산출한다.
- EV 판정 수치(EVAL v1.1 EV min/typ/max)는 **엔진 외부에서 주입**된다. 엔진은 지표 값을 산출할 뿐 게이트 임계를 내장하지 않는다(측정=판정 분리).
- 재현 허용오차(tolerance)는 그 자체가 [T] 파라미터이며 Params로 외부화한다.

## Requirements (EARS)

### REQ-METRICS-CORE — 엔진 계약: XFrame 소비 · 순수함수 · 파라미터 외부화 · 판정 분리 · 합성 검증 (CLAUDE.md T1, SWR-000-6·7·9, 측정프로토콜 §4)

- **REQ-METRICS-CORE-1 (Ubiquitous)** — 모든 지표 산출 함수는 XFrame(단일 또는 스택/시퀀스)만을 픽셀 입력으로 소비하고, 구조화된 지표 결과(값 + 산출 조건 메타)를 반환하는 순수함수여야 한다. 엔진은 처리 모듈이 아니므로 `process(...) -> XFrame` 계약을 따르지 않으며, 입력 XFrame을 읽기 전용으로 취급해야 한다(T0 REQ-INFRA-DATA-6 불변 계약 준수).
- **REQ-METRICS-CORE-2 (Unwanted)** — IF 지표 함수가 입력 XFrame(pixel · mask · noise · history)을 변경하거나 전역 상태 · 파일 우회로 산출물을 전달하려 하면, THEN 시스템은 이를 계약 위반으로 취급해야 한다(부작용 금지 — 순수 측정 계층). 이 금지 중 자동 검출 가능한 범위는 입력 XFrame 읽기 전용(read-only 버퍼) 위반과 의존 방향 위반(import-linter 정적 검사, REQ-METRICS-CORE-3)이며(acceptance.md EC-7의 검증 범위와 동일), 전역 상태·파일 우회는 테스트 가능 AC가 아닌 설계 규칙으로서 코드 리뷰 게이트로 다룬다.
- **REQ-METRICS-CORE-3 (Ubiquitous)** — 의존 방향은 `metrics → common` 단방향이어야 하며, `metrics`는 `modules/` · `pipeline/`을 import해서는 안 된다(T0 REQ-INFRA-STATIC import-linter 계약 확장).
- **REQ-METRICS-CORE-4 (Ubiquitous)** — 모든 임계 · 튜닝 · 물리 상수(TBD-[B]/[T], [P]; 예: q, Ka, XN, 88.6µm, 재현 허용오차, 결함 임계)는 Params/CalibSet로 주입되어야 하며, 엔진 코드에 하드코딩되어서는 안 된다.
- **REQ-METRICS-CORE-5 (Ubiquitous)** — EV 합격/불합격 판정 수치(EVAL v1.1 EV min/typ/max)는 엔진 외부에서 주입되어야 하며, 엔진은 지표 값을 산출할 뿐 게이트 임계를 내장하지 않아야 한다(측정=판정 분리).
- **REQ-METRICS-CORE-6 (Event-Driven)** — WHEN 지표가 산출되면, THEN 시스템은 산출 조건 메타데이터(선질 · 선량 수준 · 온도 · 필터 · 보정 상태 · ROI · 파라미터 해시 · 소비 CalibSet ID)를 지표 결과에 결정론적으로 첨부해야 한다(측정프로토콜 §4 데이터·형상 규칙, IEC 62304 추적).
- **REQ-METRICS-CORE-7 (State-Driven)** — WHILE 실측 영상 도착 전 합성 검증 컨텍스트인 동안, 시스템은 기지값을 주입한 합성 팬텀 입력에 대해 각 지표가 그 기지값을 명시 허용오차(=[T] 파라미터) 내로 재현함을 보여야 한다(엔진 자체 검증, DoD 전제).
- **REQ-METRICS-CORE-8 (Ubiquitous)** — 공용 컴포넌트(`fft_psd` / `robust_stats` / `histogram_fov`)는 `common/`에 1회만 배치되고 참조로만 사용되어야 한다. `metrics`는 이들 스텁의 첫 소비자로서 실 알고리즘 첫 정의를 유발할 수 있으나, 구현 코드는 `common/`에 두고 `metrics/`에 중복하지 않아야 한다(SWR-000-9 중복 금지).

### REQ-METRICS-MTF — MTF (edge method) (측정프로토콜 §1.2, EV-102, XDET-TC-002)

- **REQ-METRICS-MTF-1 (Ubiquitous)** — MTF는 edge method로 산출되어야 한다: 자동 edge 각도 추정 → oversampled ESF → LSF(미분+창함수) → FFT → presampled MTF. 전 과정은 스크립트 산출이며 인력 판독이 없어야 한다.
- **REQ-METRICS-MTF-2 (Event-Driven)** — WHEN 불투과 edge 슬랩 영상의 edge ROI가 주어지면, THEN 시스템은 화소 격자 대비 edge 경사각을 자동 추정하고 그 각도로 ESF를 oversampling해야 한다.
- **REQ-METRICS-MTF-3 (Unwanted)** — IF 추정 edge 각도가 허용 범위(1.5~3°) 밖이면(0° / 90° 근처 과소표본 · 정렬 실패 포함), THEN 시스템은 산출을 거부하고 명시 오류를 발생시켜야 한다(범위 밖 = 거부). 각도가 허용 범위 내이나 경계 근접(범위 내 마진 [T] 이내)이면 산출하되 경고를 표시해야 한다(경계 근접 = 경고). 마진 [T]는 Params로 외부화한다.
- **REQ-METRICS-MTF-4 (State-Driven)** — WHILE 합성 검증 컨텍스트인 동안, 기지 MTF를 갖는 이상 slanted-edge 입력에 대해 산출 presampled MTF가 해석적 기지값을 허용오차 내로 재현해야 한다(특히 MTF@Nyquist 3.57 lp/mm). Nyquist 값은 패널 파생 상수로 CalibSet에서 소비한다.
- **REQ-METRICS-MTF-5 (Optional)** — WHERE 수평 · 수직 2방향 edge가 제공되면, 시스템은 방향별 MTF를 각각 산출해야 한다.

### REQ-METRICS-NPS — NPS / NNPS + DQE (측정프로토콜 §1.3·1.4, EV-101, SWR-000-9)

- **REQ-METRICS-NPS-1 (Ubiquitous)** — NPS는 균일 조사 영상 다수 매에서 중앙 영역 256×256 ROI를 다중(반중첩) 추출 → 트렌드 제거 → 2D FFT 앙상블 평균 → 1D 축방향 추출(중심축 제외)의 절차로 산출되어야 한다.
- **REQ-METRICS-NPS-2 (Ubiquitous)** — NNPS는 NPS를 대신호(평균 신호 제곱)로 정규화하여 산출되어야 한다.
- **REQ-METRICS-NPS-3 (Ubiquitous)** — DQE(f)는 DQE(f) = MTF²(f) · q · Ka / NPS(f)로 산출되어야 하며, q(RQA5 광자 fluence 계수)와 Ka(검출기면 air kerma)는 CalibSet/Params로 주입되어야 한다(하드코딩 금지, REQ-METRICS-CORE-4).
- **REQ-METRICS-NPS-4 (Event-Driven)** — WHEN 3개 선량 수준(XN/2, XN, 2XN)의 균일 세트가 주어지면, THEN 시스템은 선량 수준별 NPS/NNPS 및 DQE를 산출해야 한다.
- **REQ-METRICS-NPS-5 (State-Driven)** — WHILE 합성 검증 컨텍스트인 동안, 기지 분산 · 상관을 주입한 백색/유색 잡음 입력에 대해 산출 NPS가 해석적 기지값(크기 · 형상)을 허용오차 내로 재현해야 한다.
- **REQ-METRICS-NPS-6 (Unwanted)** — IF 256×256 ROI가 프레임 경계를 벗어나거나 유효 균일 영역이 부족하면, THEN 시스템은 해당 ROI를 거부하고 경고해야 한다.
- **REQ-METRICS-NPS-7 (Unwanted)** — IF NPS(f)가 0에 근접하여 DQE 분모가 불안정하면, THEN 시스템은 해당 주파수의 DQE를 무효로 표시해야 한다(0-나눗셈 방지).
- **REQ-METRICS-NPS-8 (Optional)** — WHERE 라인 노이즈 스펙트럼 정량이 요청되면, 시스템은 행/열 방향 1D NPS의 저주파 이상 피크 성분을 추출해야 한다(EV-105 보조, 측정프로토콜 §1.3 · SWR-504 검증 훅).

### REQ-METRICS-LAG — First-frame lag (측정프로토콜 §1.5, EV-104, XDET-TC-004)

- **REQ-METRICS-LAG-1 (Ubiquitous)** — first-frame lag %는 ASTM E2597 lag 절차를 준용하여, 포화 근접 노출 후 취득한 프레임 시퀀스로부터 자동 산출되어야 한다.
- **REQ-METRICS-LAG-2 (Event-Driven)** — WHEN 노출 종료 후 연속 프레임 시퀀스가 주어지면, THEN 시스템은 첫 잔상 프레임 신호를 직전 노출 신호 대비 백분율(first-frame lag %)로 산출해야 한다.
- **REQ-METRICS-LAG-3 (State-Driven)** — WHILE 합성 검증 컨텍스트인 동안, 기지 IRF(지수합 M=3~4)를 주입한 합성 시퀀스에 대해 산출 first-frame lag가 기지값을 허용오차 내로 재현해야 한다.
- **REQ-METRICS-LAG-4 (Unwanted)** — IF 시퀀스가 포화 근접 노출 전제(신호 수준 · 프레임레이트 메타)를 만족하지 않으면, THEN 시스템은 경고를 발생시켜야 한다.
- **REQ-METRICS-LAG-5 (Event-Driven)** — WHEN 고대비 패턴 후 균일 조사 ghost 시퀀스가 주어지면, THEN 시스템은 잔상 CNR을 산출해야 한다(EV-104 ghost 판정 산출부, XDET-TC-005 — 필수 DoD).

### REQ-METRICS-DEFECT — Bad-pixel 통계 (ASTM E2597 분류) (측정프로토콜 §2, EV-103, XDET-TC-003)

- **REQ-METRICS-DEFECT-1 (Ubiquitous)** — bad-pixel 통계는 dark/flat 스택 통계로부터 ASTM E2597 7종 분류 매핑(무응답 · out-of-range · noise · lag · non-uniform 등)으로 산출되어야 한다.
- **REQ-METRICS-DEFECT-2 (Event-Driven)** — WHEN dark 스택과 flat 스택이 주어지면, THEN 시스템은 7종 분류 결함 맵과 종류별 분율 통계를 산출해야 한다.
- **REQ-METRICS-DEFECT-3 (Ubiquitous)** — noisy 판정의 6× median 기준은 E2597-22 확정 표준 상수 [S]로 적용되어야 하고, dead / over-under-range / non-uniform 임계는 [P] 등급으로 Params에서 외부 주입되어야 한다(하드코딩 금지, REQ-METRICS-CORE-4).
- **REQ-METRICS-DEFECT-4 (State-Driven)** — WHILE 합성 검증 컨텍스트인 동안, 기지 좌표 · 종류의 결함을 주입한 합성 dark/flat 스택에 대해 검출 맵이 기지값을 재현하고 검출 누락률을 산출해야 한다(EV-103 검출 누락 기준 대비).
- **REQ-METRICS-DEFECT-5 (Unwanted)** — IF 스택 매수가 통계 산출 최소치 미만이거나 유효 픽셀이 부족하면(예: ROI 전체가 dead 픽셀), THEN 시스템은 산출을 거부하고 경고해야 한다.

### REQ-METRICS-NDT — SNRn + Duplex-wire IQI (측정프로토콜 §2, SWR-1201·1202, EV-301, XDET-TC-018)

- **REQ-METRICS-NDT-1 (Ubiquitous)** — SRb_image는 duplex wire IQI 자동 판독으로 산출되어야 하며, wire pair 프로파일에서 20% dip 기준(ISO 규정)으로 판정되어야 한다(SWR-1202).
- **REQ-METRICS-NDT-2 (Ubiquitous)** — SNRn은 SNRn = SNR × 88.6[µm] / SRb_image로 산출되어야 한다(측정프로토콜 §2, SWR-1201). 88.6µm는 표준 상수 [S]로 Params에서 소비한다.
- **REQ-METRICS-NDT-3 (Event-Driven)** — WHEN 균일 영역(사용자 지정 ROI 또는 자동 검출 균일 영역)이 주어지면, THEN 시스템은 SNR을 산출하고 SRb_image로 정규화하여 SNRn을 산출해야 한다.
- **REQ-METRICS-NDT-4 (Unwanted)** — IF duplex wire 프로파일에서 20% dip이 검출되지 않으면(no dip found), THEN 시스템은 판독 실패를 명시해야 한다(무단 SRb 추정 금지).
- **REQ-METRICS-NDT-5 (State-Driven)** — WHILE 합성 검증 컨텍스트인 동안, 기지 dip 위치의 합성 duplex wire 프로파일과 기지 SNR 균일 영역에 대해 산출 SRb · SNRn이 기지값을 허용오차 내로 재현해야 한다.

## Exclusions (What NOT to Build)

- **실측 측정 데이터 취득 · 판독 없음** — 본 T1은 합성 팬텀(기지값 주입)만으로 엔진을 검증한다. 실 영상(GDS) 판독은 2단계 실측 도착 후. RQA5 셋업 · 선량 취득 자체는 범위 밖(측정프로토콜 §1.1, 실측 항목 리스트).
- **처리 모듈 없음** — offset/gain/defect 보정 · lag 보정 · line noise · 포화/기하 등 처리 알고리즘은 T2 이후. metrics는 XFrame을 읽기만 하며 `process(...) -> XFrame`을 구현하지 않는다.
- **EV 게이트 임계 내장 없음** — EV min/typ/max 판정 수치(EVAL v1.1)는 EVAL 기준서/Params에서 참조 주입한다. 엔진은 지표 값만 산출하고 합격/불합격 결정 임계를 내장하지 않는다.
- **명명 지표 외 판정 엔진 이연** — XDET-TC-008/009(포화 경계 아티팩트 · 기하 잔차, EV-106)의 지표 엔진은 해당 처리 WP(T3)와 동반 개발로 이연. XDET-TC-006의 라인노이즈 성분 정량만 NPS 그룹 Optional(REQ-METRICS-NPS-8)로 한정 흡수하며, XDET-TC-007(구조물 오보정률, EV-105)은 라인노이즈와 무관한 별개 항목으로 처리 모듈 T3와 동반 이연한다.
- **CSa/SMTR · 두께보정 지표 없음** — EV-303 / XDET-TC-019(step wedge, CSa/SMTR)는 태스크 명시 7개 지표 밖. NDT 지표 중 SNRn · duplex-wire(SRb)만 T1 범위.
- **실시간 적산 · 취득 종료 신호 없음** — SWR-1201의 Welford 프레임 스트리밍 누적 · 실시간 SNRn 목표 도달 종료 신호는 T9(WP10 NDT 모듈)로 이연. T1은 주어진 프레임/스택에 대한 **정적 readout**만 제공.
- **관찰자 연구 · 관찰자 대체 IQA 없음** — EV-204(ICC/VGA/GSDF), CDRAD IQFinv, 무참조 IQA(측정프로토콜 §1.6, XDET-TC-022)는 인허가/개발 IQA 별도 트랙. T1 범위 밖.
- **Post 지표(scatter/grid/window/DRC) 없음** — EV-201/202/203/205 등의 지표 엔진은 각 처리 WP(T5~T7)에서. T1은 Common Core 물리 지표(EV-101~104)와 NDT SNRn/IQI(EV-301)의 명명 부분만.
- **성능 · 처리시간 · 티어 동일성 지표 없음** — EV-401/402, XDET-TC-020/021은 P2.
- **Gen 2 항목 없음** — ADR(EV-302) · DL 기반 지표는 P1 범위 밖.
- **공용 컴포넌트 범용 최적화 없음** — `metrics`가 유발하는 `common/`(fft_psd/robust_stats/histogram_fov) 실 구현은 정확도 목표의 최소 구현만. 속도 최적화는 P2.
