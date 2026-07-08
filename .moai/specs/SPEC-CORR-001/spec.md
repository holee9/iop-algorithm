---
id: SPEC-CORR-001
version: 0.2.0
status: implemented
created: 2026-07-09
updated: 2026-07-09
author: drake.lee
priority: high
issue_number: 3
---

# SPEC-CORR-001 — T2 WP1 offset/gain/defect 보정 모듈 (modules/)

XDET 영상처리 SW P1의 세 번째 작업 T2(WP1). offset·gain·defect 보정 처리 모듈 3종(`modules/offset.py` · `modules/gain.py` · `modules/defect.py`)을 T0 프레임워크의 단일 계약 `process(XFrame, CalibSet, Params) -> XFrame` 순수함수형으로 구현한다. 세 모듈은 고정 파이프라인 순서 offset → gain → defect의 해당 위치에서만 실행되며, 캘리브레이션 데이터(offset map · gain map · defect map)를 CalibSet로 소비한다.

- 근거: SWR-101~104(offset, FR-C001) · SWR-201~204(gain, FR-C002) · SWR-301~304(defect, FR-C003/C004) · SWR-000-2~12(아키텍처) — `docs/XDET_SWR_spec_v1.2.md`; EVAL v1.1 EV-101/102/103; TestSpec XDET-TC-001~003
- 완료 정의(DoD): **합성 주입 왜곡 제거를 metrics/ 엔진으로 before/after 판정** — 실측 영상 도착 전, 기지 offset/gain/defect 패턴을 주입한 합성 프레임에 보정을 적용하고 T1 지표 엔진(`compute_dqe` · `compute_mtf` · `classify_defects`)으로 보정 전/후 개선·비열화를 판정한다. XDET-TC-003의 EV-103은 두 다리로 판정한다 — (a) `modules/defect.py` 보간 후 잔존 가시 cluster 0건, (b) defect-map 빌더(`metrics/defect_map.py`)가 dark/flat 스택에서 생성한 맵의 검출 누락률 ≤ EV-103 min(ground truth 대조). XDET-TC-001·002·003을 pytest skeleton(skip)에서 실동작 케이스로 전환하여 EV-101/102/103 min 대비 통과
- 선행 계약: [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md) — `process` 계약·XFrame 불변·마스크 스택·이력 체인·오케스트레이터 진입 게이트(종류-단계 배선: offset→OFFSET, gain→GAIN, defect→DEFECT)·import-linter 레이어링(`module → common` 단방향); [SPEC-METRICS-001](../SPEC-METRICS-001/spec.md) — before/after 개선을 판정하는 지표 산출 엔진
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.2.0 (2026-07-09)** — 구현 완료(status: implemented). 커밋 4451875(모듈 3종+빌더) + daa442e(리뷰 결함 10건 수정). 125 passed / 18 skipped(3회 재실행 동일), 레이어링 계약 5건 KEPT. 구현 중 확정:
  - LINE 분류 얇음 조건(직교 폭 ≤ line_max_width [T], 기본 1) 추가 — 대형 블롭의 C_max 게이트 우회 차단(리뷰 critical).
  - gain 65535 클램프 픽셀 SATURATION 플래그 + defect 앵커에서 SATURATION 제외.
  - 신규 [T] 파라미터: line_max_width — SWR 부록 A 등재 필요.
  - 다점 gain(GAIN-4)은 [B] 대기 이연(anchor_gains 입력 시 명시 NotImplementedError).

- **v0.1.1 (2026-07-09)** — plan-audit iteration 1 (FAIL 0.77) 결함 8건(D1~D8) 반영 + orchestrator 결정 1·4 확정:
  - **결정 1 확정(defect 맵 생성 = T2 포함)**: defect-map 빌더 `metrics/defect_map.py`를 신설하여 T1 엔진 `metrics/defect_stats.classify_defects`를 재사용해 dark/flat 스택에서 CalibSet(DEFECT) 맵을 생성한다(레이어링 불변 metrics→common; CalibSet은 common 소속). `modules/defect.py`는 보간 전용 소비자로 유지. REQ-CORR-DEFECT-6 신설, Exclusions·Environment의 "맵 생성 이연"을 "SWR-304 주기 재검출만 이연"으로 정정.
  - **결정 4 확정(gain→defect 이관 계약)**: gain 범위밖 화소는 출력값을 I₁으로 보존(무효 G 미적용)+DEFECT 플래그, defect 모듈은 이 분류 없는 화소를 단일점 8-이웃 거리 가중 보간+INTERPOLATION 플래그로 결정론적 처리(분기 없음). REQ-CORR-GAIN-3·REQ-CORR-DEFECT-8 반영.
  - D1: REQ-CORR-DEFECT-3을 빌더의 분류 임계 요구로 재범위화(임계는 빌더가 T1 엔진 파라미터로 위임), AC는 빌더 시나리오(Scenario 9).
  - D2: VALIDATE-3(EV-103)을 두 다리로 분할 — 잔존 cluster 0건(`modules/defect.py`, VALIDATE-3) + 검출 누락률(빌더, VALIDATE-7 신설). DoD 요약·acceptance DoD 정정.
  - D3: CalibSet(DEFECT) 스키마 위반(분류 라벨 결손) 명시 거부 요구 REQ-CORR-DEFECT-7 신설, EC-2(b) 추적.
  - D4: 클램프 발생률 전달 채널을 이력 체인 엔트리 메타데이터(스칼라)로 확정, acceptance Scenario 2/4·plan §3의 "이력/마스크" 분기 제거.
  - D5: EC-3 사후조건 명시(DEFECT 플래그 유지·INTERPOLATION 미설정·화소값 입력 보존).
  - D6: DQE 인용 문구 정정(HISTORY 항목 4·REQ-CORR-VALIDATE-2) — "T1 엔진 구현이 IEC 형태로 정정됨(SPEC-METRICS-001 HISTORY v0.2.0)"로 상류 REQ 본문 정정 함의 제거. 별도 상류 동기화로 SPEC-METRICS-001 REQ-METRICS-NPS-3 본문을 IEC 형태로 동기화(v0.2.1).
  - D7: Exclusions에 SWR-103 "촬영 세션 시작 시 신규 다크 취득 옵션"은 취득 소관(T2 SW 밖) 명시.
  - D8: REQ-CORR-GAIN-3에 범위밖 G 화소값 처리(I₁ 보존) 명시, REQ-CORR-DEFECT-8에 gain 플래그 화소 hand-off 명시.
  - status: draft 유지(run 단계 착수 전까지).
- **v0.1.0 (2026-07-09)** — 초안 생성. GitHub 이슈 #3. 5개 요구 그룹(OFFSET/GAIN/DEFECT/CONTRACT/VALIDATE) EARS 구조 확정. 핵심 범위 결정:
  1. **defect 모듈 = 보간 전용 소비자**: `process(XFrame, CalibSet, Params) -> XFrame` 단일 프레임 계약은 dark/flat 스택 기반 검출(SWR-301/302)을 수행할 수 없고, E2597 분류는 이미 T1 `metrics/defect_stats.classify_defects`에 존재하므로, T2 defect 모듈은 사전 생성된 CalibSet(defect) 맵을 소비하여 SWR-303 보간만 수행한다. 결함 맵 생성·주기적 재검출(SWR-304)은 캘리브레이션/운영 소관으로 이연 — 「결정 필요/확인 사항」 1 참조.
  2. **SWR-203 결함 후보 이관 = XFrame 마스크**: gain map 범위 밖 화소는 XFrame 마스크의 DEFECT 플래그로 표시하여 고정 순서 gain→defect를 통해 하류로 전달(사이드채널 금지 준수). 통합 세부는 「결정 필요/확인 사항」 4.
  3. **노이즈 모델 미갱신**: SWR-201~204는 gain 배율에 따른 XFrame 노이즈 모델(α,σ) 갱신을 명시하지 않고, 노이즈 추정은 SWR-701(T5) 소관이므로 보정 모듈은 노이즈 모델을 재추정하지 않는다 — 「결정 필요/확인 사항」 2.
  4. **DQE는 IEC 형태 참조**: 측정프로토콜 v1.0 §1.4의 DQE 공식은 IEC 62220-1과 차원 역전 상충 — T1 엔진 구현이 IEC 형태로 정정됨(SPEC-METRICS-001 HISTORY v0.2.0, 이슈 #2)에 따라 T2 개선 게이트도 IEC 형태를 참조한다.
  - 파라미터 등급 확정(SWR 부록 A 대조): noisy 6× median = [S], dead/over-under/non-uniform 임계 = [P](B5 확정 대기), gain 범위 [0.5,2.0] = [T], cluster C_max 5×5 = [T], offset 잔여 10% = [T], 동적 offset 모델(SWR-103) = [B], 다점 gain anchor(SWR-202) = [B].
  - status: draft (run 단계 착수 전까지 유지).

## Environment / Assumptions

- Python 3.11+, numpy/scipy 기반 float 골든 모델 (tech.md). **속도 최적화 금지 — 정확도 단일 목표**(P2에서 최적화).
- 대상 프레임: 3072×3072 / 3072×2560, 16-bit unsigned raw, pitch 140µm, Nyquist f_N = 3.57 lp/mm(EVAL v1.1 §0).
- **실측 영상 도착 전 — 합성 데이터로 보정 모듈을 검증한다.** 기지 offset(다크 패턴)·gain(비균일 flat)·defect(좌표·종류)를 주입한 합성 프레임을 생성하고, 보정 후 주입 왜곡이 제거되었는지를 T1 지표 엔진 산출로 확인한다(CLAUDE.md T2 주의: 합성+실측 중 합성 선행).
- **용어 정의 — 합성 검증 컨텍스트(synthetic-validation context)**: 합성 팬텀 fixture 시험 실행(기지 왜곡 주입 → 보정 후 제거 확인)을 가리키는 단일 용어이다. 이는 T0(SPEC-INFRA-001)의 **검증 모드(validation_mode — float64 병행 버퍼가 활성인 XFrame 상태)**와는 별개 개념이다(전자는 보정 모듈 정확도 검증, 후자는 float32/float64 수치 정밀도 대조). SPEC-METRICS-001의 동명 용어 정의를 계승한다.
- T0 계약 소비: 세 모듈은 XFrame(불변)을 입력받아 새 XFrame을 반환하는 처리 모듈이며 `process(XFrame, CalibSet, Params) -> XFrame` 계약을 따른다. 마스크 스택 비트플래그(DEFECT/SATURATION/INTERPOLATION), 이력 체인, 오케스트레이터 진입 게이트(종류-단계 배선), CalibKind(OFFSET/GAIN/DEFECT)를 그대로 소비한다. 의존 방향은 `modules → common` 단방향(import-linter).
- **defect 맵은 defect-map 빌더(`metrics/defect_map.py`, REQ-CORR-DEFECT-6)가 dark/flat 스택에서 생성한 CalibSet(DEFECT)로 소비된다**(결함 검출·분류는 빌더가 T1 엔진 `metrics/defect_stats.classify_defects` 재사용으로 수행 — 「결정 필요/확인 사항」 1 확정). 처리 모듈 `modules/defect.py`는 이 맵을 소비만 하며(보간 전용) 재생성하지 않는다. offset/gain map도 각각 CalibSet(OFFSET/GAIN) 데이터로 소비하며 모듈은 이를 재생성하지 않는다.
- before/after 개선 판정은 T1 지표 엔진(`compute_dqe` · `compute_mtf`/`mtf_value_at` · `classify_defects`)을 소비한다. 단, 모듈은 `metrics`를 import할 수 없으므로(CONTRACT-3) 판정 로직은 **시험 코드(`tests/`)에서** 모듈과 엔진을 함께 소비하여 릴리스 게이트를 구성한다.
- 물리·튜닝·[P] 상수(offset 잔여 임계·gain 범위·cluster C_max·dead/over/under/non-uniform 임계·동적 offset/다점 gain [B] 파라미터)는 전부 Params/CalibSet로 외부화한다(하드코딩 금지). 등급은 SWR 부록 A를 따른다.
- EV 판정 수치(EVAL v1.1 EV min/typ/max)는 **엔진·모듈 외부에서 주입**된다(측정=판정 분리, SPEC-METRICS-001 계승).

## Requirements (EARS)

### REQ-CORR-OFFSET — Offset 보정 (다크프레임 감산) (SWR-101~104, FR-C001)

- **REQ-CORR-OFFSET-1 (Ubiquitous)** — offset 모듈은 CalibSet(OFFSET)의 offset map O(x,y)를 소비하여 다크프레임 감산 I₁ = I_raw − O를 수행해야 한다(SWR-102). offset map은 다크 N_d≥16매를 프레임축 3σ 클리핑 후 평균하여 생성된 CalibSet 데이터이며(SWR-101), 모듈은 이를 재생성하지 않는다.
- **REQ-CORR-OFFSET-2 (Event-Driven)** — WHEN 감산 결과에 음수 화소가 발생하면, THEN 시스템은 해당 화소를 0으로 클램프하고 클램프 발생률을 리포트해야 한다(과대 offset 진단, SWR-102).
- **REQ-CORR-OFFSET-3 (Optional)** — WHERE 온도 T·경과시간 t 의존 동적 offset 모델(O(x,y;T) = O_ref(x,y) + ΔO(T))이 CalibSet에 제공되면, 시스템은 해당 취득 조건의 offset을 적용해야 한다(SWR-103). ΔO 모델 차수·갱신 주기는 TBD-[B](1단계 B1 온도별 다크로 확정)로 Params/CalibSet에 외부화하며, 미제공 시 정적 O_ref 경로를 사용한다.

### REQ-CORR-GAIN — Gain 보정 (평탄장 정규화) (SWR-201~204, FR-C002)

- **REQ-CORR-GAIN-1 (Ubiquitous)** — gain 모듈은 CalibSet(GAIN)의 단일점 gain map G(x,y)를 소비하여 평탄장(flat-field) 정규화 I₂ = I₁ × G를 수행해야 한다(SWR-201). G(x,y) = mean_ROI(F̄)/F̄(x,y)이며 F̄는 offset 보정된 flat 평균(≥10매)으로 생성된 CalibSet 데이터로, 모듈은 이를 재생성하지 않는다.
- **REQ-CORR-GAIN-2 (Event-Driven)** — WHEN 정규화 결과가 상한 65535를 초과하면, THEN 시스템은 해당 화소를 65535로 클램프하고 클램프 발생률을 리포트해야 한다(SWR-201).
- **REQ-CORR-GAIN-3 (Unwanted)** — IF gain map 화소값이 유효 범위 [0.5, 2.0](TBD-[T], Params 외부화) 밖이면, THEN 시스템은 (1) 해당 출력 화소값을 gain 미적용 상태 I₁으로 보존하고(무효 G 미적용), (2) 해당 화소를 XFrame 마스크의 DEFECT 플래그로 표시하여 하류 defect 단계로 결함 후보를 이관해야 한다(SWR-203, 고정 순서 gain→defect 의존; 결정론적 단일 경로 — 「결정 필요/확인 사항」 4 확정).
- **REQ-CORR-GAIN-4 (Optional)** — WHERE 선량 계단 K개(K≥3) anchor의 다점 gain 데이터가 CalibSet에 제공되면, 시스템은 픽셀별 구간 선형 보간(anchor 외삽 구간은 최근접 구간 기울기 연장) 다점 gain 보정을 적용해야 한다(SWR-202). anchor 수·비선형성 판정(선형성 오차 <1%면 단일점 채택)은 TBD-[B](1단계 1-3 데이터)로 외부화하며, 미제공 시 REQ-CORR-GAIN-1의 단일점 경로를 사용한다.

### REQ-CORR-DEFECT — Defect 보정 (맵 기반 보간) + 결함 맵 빌더 (SWR-301~304, FR-C003/C004)

- **REQ-CORR-DEFECT-1 (Ubiquitous)** — defect 모듈은 CalibSet(DEFECT)의 결함 맵과 분류(단일점 / line(행·열 연속 ≥8px) / cluster(연결 성분 ≥2px); SWR-302)를 소비하여 SWR-303 보간을 수행해야 한다: 단일점 = 정상 8-이웃 거리 가중 평균, line = 직교 방향 1D 선형 보간, cluster = 4방향(0/45/90/135°) 분산 최소 방향 1D 선형 보간(edge-directed). 결함 검출·분류(SWR-301/302, dark/flat 스택 기반)는 defect-map 빌더(REQ-CORR-DEFECT-6) 소관이며 처리 모듈은 맵을 재생성하지 않는다.
- **REQ-CORR-DEFECT-2 (Event-Driven)** — WHEN 결함 화소가 보간되면, THEN 시스템은 해당 화소를 XFrame 마스크에 INTERPOLATION 플래그로 표시하고, defect·interpolation 마스크를 하류로 전달해야 한다(노이즈 통계 오염 방지 — 하류 NPS·denoiser에서 제외 가중, SWR-303).
- **REQ-CORR-DEFECT-3 (Ubiquitous)** — defect-map 빌더(REQ-CORR-DEFECT-6)의 결함 분류 임계 등급은 SWR-301 및 부록 A를 따라야 한다: noisy 판정 6× median 기준은 E2597-22 확정 표준 상수 [S]로 고정하고, dead(<20% 응답)·over/under-range(±30%)·non-uniform(±20%) 임계는 [P] 등급 기본값으로 Params/CalibSet에 외부 주입되어야 한다(하드코딩 금지; E2597 원문 수치는 B5 스택+원문으로 확정 대기 — 부록 A [B] 등재). 빌더는 이 임계를 T1 엔진(`metrics/defect_stats.classify_defects`)에 파라미터로 위임하며, 등급 규약은 SPEC-METRICS-001 REQ-METRICS-DEFECT-3와 일치한다.
- **REQ-CORR-DEFECT-4 (Unwanted)** — IF CalibSet(DEFECT) 맵의 연결 cluster 크기가 상한 C_max(5×5, TBD-[T], Params 외부화)를 초과하면, THEN 시스템은 해당 결함 맵의 보간 사용을 거부하고 패널 판정 경고를 발생시켜야 한다(진단 ROI 품질 보증 불가, SWR-302).
- **REQ-CORR-DEFECT-5 (Unwanted)** — IF 결함 화소의 SWR-303 보간이 유효한 정상 이웃 위에서 성립하지 못하면(모든 이웃이 결함), THEN 시스템은 해당 화소를 무단 "복원"하지 않고 결함/미보정 상태로 유지·표시해야 한다(허위 신호 생성 금지 — 사후조건: DEFECT 플래그 유지·INTERPOLATION 미설정·화소값 입력 보존; SWR-303 정상 이웃 전제, SWR-602 복원 금지 원칙 준용). 포화 화소 처리(SWR-601/602)는 고정 순서상 defect 이후 단계(T3)이므로 defect 보간의 직접 대상이 아니다.
- **REQ-CORR-DEFECT-6 (Event-Driven)** — WHEN dark/flat 스택이 캘리브레이션 입력으로 주어지면, THEN defect-map 빌더(`metrics/defect_map.py`)는 T1 엔진 `metrics/defect_stats.classify_defects`를 재사용하여 결함을 검출·분류(단일점/line/cluster)하고 그 결과를 CalibSet(kind=DEFECT) 맵으로 생성해야 한다(SWR-301/302 검출·분류의 T2 소관 — 「결정 필요/확인 사항」 1 확정). 빌더는 metrics 계층 아티팩트로서 `metrics → common` 단방향을 준수하며(생성물 CalibSet은 common 소속), 처리 모듈의 metrics import 금지(REQ-CORR-CONTRACT-3)는 빌더에 적용되지 않는다. 처리 모듈 `modules/defect.py`는 이 맵을 소비만 하고(보간 전용) metrics를 import하지 않는다. 생성된 맵의 cluster가 C_max(5×5, TBD-[T]) 초과이면 빌더는 맵 생성을 거부하고 패널 판정 경고를 발생시켜야 한다(SWR-302 생성 시점 게이트; 소비 시점 게이트 REQ-CORR-DEFECT-4와 이중화).
- **REQ-CORR-DEFECT-7 (Unwanted)** — IF CalibSet(DEFECT) 맵이 필수 분류 라벨(단일점/line/cluster)을 결손한 스키마 위반 상태이면, THEN 시스템은 해당 맵의 보간 사용을 거부하고 명시 오류를 발생시켜야 한다(무단 기본값 대체·추정 금지 — SWR-000-5·SWR-302 스키마 무결성). 이는 분류 라벨을 전제하는 REQ-CORR-DEFECT-1 보간의 입력 계약을 보증한다.
- **REQ-CORR-DEFECT-8 (Event-Driven)** — WHEN defect 모듈이 gain 단계가 DEFECT 플래그로 이관한(CalibSet(DEFECT) 분류가 없는) 화소를 만나면, THEN 시스템은 해당 화소를 단일점 결함으로 취급하여 정상 8-이웃 거리 가중 평균으로 보간하고 INTERPOLATION 플래그를 설정해야 한다(SWR-203 이관 화소의 결정론적 처리 — 「결정 필요/확인 사항」 4 확정). 유효한 정상 이웃이 없으면 REQ-CORR-DEFECT-5(무단 복원 금지)를 따른다.

### REQ-CORR-CONTRACT — 공통 모듈 계약 준수 (SWR-000-2~12, REQ-INFRA-* 소비)

- **REQ-CORR-CONTRACT-1 (Ubiquitous)** — offset/gain/defect 세 모듈은 각각 단일 시그니처 `process(XFrame, CalibSet, Params) -> XFrame` 순수함수형이어야 하며(SWR-000-7, REQ-INFRA-CONTRACT-1), 입력 XFrame을 불변으로 취급(원본 미변경)하고 새 XFrame을 반환해야 한다(SWR-000-3, REQ-INFRA-DATA-6).
- **REQ-CORR-CONTRACT-2 (Event-Driven)** — WHEN 각 모듈이 출력 XFrame을 생성하면, THEN 시스템은 처리 메타(모듈 버전 · 파라미터 해시 · 소비 CalibSet ID)를 이력 체인에 결정론적으로 추가해야 한다(SWR-000-4, REQ-INFRA-DATA-4, IEC 62304 추적).
- **REQ-CORR-CONTRACT-3 (Ubiquitous)** — 의존 방향은 `modules → common` 단방향이어야 하며, 모듈은 다른 처리 모듈 · `pipeline` · `metrics`를 import해서는 안 된다(SWR-000-8, REQ-INFRA-STATIC import-linter 계약 확장). 실행 순서·조합은 오케스트레이터 단독 소관이며 모듈 간 직접 호출은 금지된다(REQ-INFRA-ORCH-1/2).
- **REQ-CORR-CONTRACT-4 (Unwanted)** — IF 처리 모듈이 XFrame 컨테이너 외 채널(전역 상태 · 부가 반환값 · 파일 우회)로 데이터를 전달하려 하면, THEN 시스템은 이를 계약 위반으로 취급해야 한다(SWR-000-6 사이드채널 금지). 자동 검출 가능 범위는 시그니처·부가 반환값 위반(계약 검사)과 의존 방향 위반(import-linter 정적 검사)이며(acceptance.md EC-4의 검증 범위와 동일), 전역 상태·파일 우회는 테스트 가능 AC가 아닌 설계 규칙으로서 코드 리뷰 게이트로 다룬다(SPEC-INFRA-001 REQ-INFRA-DATA-2 방식 계승).
- **REQ-CORR-CONTRACT-5 (Unwanted)** — IF offset/gain/defect 단계의 CalibSet이 부재하거나 불일치(해상도 · 패널 ID · 종류-단계 배선: offset→OFFSET, gain→GAIN, defect→DEFECT)하면, THEN 오케스트레이터 진입 게이트가 처리를 거부하고 명시 오류를 발생시켜야 한다(무단 기본값 대체 금지, SWR-000-5, REQ-INFRA-ORCH-4).
- **REQ-CORR-CONTRACT-6 (Ubiquitous)** — 세 모듈은 고정 파이프라인 순서 offset → gain → defect 내 해당 위치에서만 실행되어야 하며(SWR-000-2, REQ-INFRA-ORCH-3), 각 모듈은 합성 입력 + 기대 출력 fixture로 harness 단독 시험이 가능해야 한다(SWR-000-11, XDET-TC-000).

### REQ-CORR-VALIDATE — 합성 검증 + before/after 판정 (XDET-TC-001~003, EV-101/102/103)

- **REQ-CORR-VALIDATE-1 (State-Driven)** — WHILE 실측 영상 도착 전 합성 검증 컨텍스트인 동안, 시스템은 기지 offset/gain/defect 패턴을 주입한 합성 프레임에 대해 각 보정 모듈이 주입 왜곡을 제거함을 보여야 한다(DoD 전제, CLAUDE.md T2).
- **REQ-CORR-VALIDATE-2 (Event-Driven)** — WHEN 기지 offset/gain 왜곡을 주입한 합성 프레임에 보정(offset → gain)을 적용하면, THEN 시스템은 보정 전/후 DQE(3선량 XN/2 · XN · 2XN)와 MTF@Nyquist(3.57 lp/mm) 유지율을 metrics/ 엔진(`compute_dqe` · `compute_mtf`)으로 산출하여 개선·비열화를 판정 가능해야 한다(XDET-TC-001 EV-101 min, XDET-TC-002 EV-102 min). DQE는 T1 엔진 구현의 IEC 형태(DQE = MTF²/(q·Ka·NNPS))로 산출된다(측정프로토콜 v1.0 §1.4의 차원 역전에 대해 T1 엔진 구현이 IEC 형태로 정정 — SPEC-METRICS-001 HISTORY v0.2.0; 상류 REQ 본문 동기화 v0.2.1).
- **REQ-CORR-VALIDATE-3 (Event-Driven)** — WHEN 기지 결함(단일점/line/cluster)을 주입한 합성 프레임에 defect 보정(`modules/defect.py` 보간)을 적용하면, THEN 시스템은 metrics/ 엔진(`classify_defects`)으로 보정 후 잔존 가시 cluster 0건임을 판정 가능해야 한다(XDET-TC-003 EV-103 min의 잔존 cluster 다리 — 처리 모듈 게이트).
- **REQ-CORR-VALIDATE-4 (Event-Driven)** — WHEN 다크 프레임을 offset 보정하면, THEN 시스템은 잔여 offset(보정 후 다크 평균)이 σ_d 중앙값의 [T](기본 10%, Params 외부화) 이내임을 확인해야 한다(SWR-104 검증 훅). σ_d는 CalibSet(OFFSET)가 담는 픽셀별 표준편차이다(SWR-101).
- **REQ-CORR-VALIDATE-5 (Ubiquitous)** — EV min/typ/max 판정 수치는 EVAL v1.1/Params에서 외부 주입되어야 하며, 검증은 metrics/ 엔진 산출값과 외부 임계의 비교로만 이뤄져야 한다(측정=판정 분리 계승). 보정 모듈·판정 코드는 게이트 임계를 내장하지 않는다.
- **REQ-CORR-VALIDATE-6 (Ubiquitous)** — 시험 케이스 XDET-TC-001 · XDET-TC-002 · XDET-TC-003은 현재 pytest skeleton(skip)에서 합성 입력·판정 엔진 연동의 실동작 케이스로 전환되어야 한다(REQ-INFRA-CI-1 계승). 모듈은 `metrics`를 import하지 않으므로 판정 로직은 `tests/`에서 모듈+엔진을 함께 소비한다.
- **REQ-CORR-VALIDATE-7 (Event-Driven)** — WHEN 기지 결함(단일점/line/cluster)을 주입한 합성 dark/flat 스택을 defect-map 빌더(REQ-CORR-DEFECT-6)에 입력하면, THEN 시스템은 빌더가 생성한 CalibSet(DEFECT) 맵을 ground truth와 대조하여 검출 누락률이 EV-103 min 이내임을 판정 가능해야 한다(XDET-TC-003 EV-103 min의 누락률 다리 — 빌더 게이트, 「결정 필요/확인 사항」 1 확정). `classify_defects` 재사용으로 산출된 누락률은 측정=판정 분리에 따라 외부 EV-103 min과 비교된다.

## Exclusions (What NOT to Build)

- **후속 WP 처리 모듈 없음** — lag(SWR-401~404/T4), line noise(SWR-501~504/T3), 포화·기하(SWR-601~603/T3), VST+BM3D 노이즈 저감(SWR-701~706/T5), MSE/DRC(SWR-801~805/T6), 자동 윈도잉·GSDF(SWR-901~903/T6), grid 억제(SWR-1001~1006/T7), 커널 virtual grid(SWR-1101~1103/T8), NDT(SWR-1201~1204/T9), 티어·동일성(SWR-1301~1303/T10)은 T2 범위 밖.
- **주기적 재검출·운영 diff 없음** — SWR-304의 주기(월 1회, TBD 운영) 재검출·diff 리포트는 캘리브레이션 운영 소관으로 이연한다. 단, SWR-301/302의 dark/flat 스택 기반 결함 검출·분류를 통한 **결함 맵 1회 생성**은 defect-map 빌더(`metrics/defect_map.py`, REQ-CORR-DEFECT-6)로 T2에 포함된다(「결정 필요/확인 사항」 1 확정). 처리 모듈 `modules/defect.py`는 사전 생성된 맵을 **소비**하여 SWR-303 보간만 수행한다.
- **노이즈 모델 재추정 없음** — 노이즈 모델(α, σ) 추정은 SWR-701(T5) 소관. 보정 모듈은 노이즈 모델을 재추정하지 않는다(「결정 필요/확인 사항」 2).
- **heel effect 별도 보정 모듈 없음** — 저주파 비균일은 gain map에 내재 보정되며 별도 처리 단계를 두지 않는다(SWR-204). flat/임상 기하 불일치 잔차 경고는 캘리브레이션 절차서 문서 소관(런타임 모듈 아님).
- **다크 재취득 없음** — SWR-103의 "촬영 세션 시작 시 신규 다크 취득 옵션"은 취득(acquisition) 소관으로 T2 SW 처리 범위 밖이다. T2 offset 모듈은 제공된 CalibSet(OFFSET)만 소비하며 다크를 재취득하지 않는다(동적 offset 모델 소비는 REQ-CORR-OFFSET-3 Optional 경로로 한정).
- **포화 영역 "복원" 없음** — SWR-602 복원 금지는 포화 모듈(T3, 고정 순서상 defect 이후) 소관이며, T2 defect 보간은 포화 화소를 복원 대상으로 삼지 않는다(REQ-CORR-DEFECT-5).
- **[B] 값 확정 없음** — 동적 offset 모델(SWR-103, 1단계 B1), 다점 gain anchor(SWR-202, 1단계 1-3), dead/over/under/non-uniform 임계(SWR-301, B5)의 실측 [B] 값 확정은 범위 밖. Optional 경로/[P] 기본값만 두고 Params/CalibSet로 외부화한다.
- **실 캘리브레이션 데이터·GDS 채우기 없음** — 합성 팬텀(기지 왜곡 주입)만으로 모듈을 검증한다. 실 offset/gain/defect map과 실 영상(GDS) 판정은 2단계 실측 도착 후.
- **EV 게이트 임계 내장 없음** — EV min/typ/max 판정 수치(EVAL v1.1)는 외부 주입. 보정 모듈·판정 코드는 합격/불합격 임계를 내장하지 않는다.
- **성능·처리시간 게이트 없음** — EV-401/402, XDET-TC-020/021은 P2.
- **Gen 2 항목 없음** — DL 기반 처리·ADR은 P1 범위 밖.

## 결정 필요/확인 사항

SWR 조항이 T0/T1 구현과 모호하거나 상충하는 지점. 「1·4」는 orchestrator 결정으로 확정(RESOLVED, HISTORY v0.1.1 반영)하고, 「2·3·5」는 run 착수 전 확인 대상으로 남긴다(임의 해소하지 않음).

1. **[확정 — RESOLVED] defect 검출/맵 생성의 T2 소속** — SWR-301/302의 결함 검출·분류는 T2에 **포함**한다. 단일 프레임 처리 계약으로는 스택 검출이 불가하나, defect-map 빌더 `metrics/defect_map.py`(REQ-CORR-DEFECT-6)를 metrics 계층에 신설하여 T1 엔진 `metrics/defect_stats.classify_defects`를 **재사용**해 dark/flat 스택에서 CalibSet(DEFECT) 맵을 생성한다. 레이어링은 불변(metrics→common; CalibSet은 common 소속). 처리 모듈 `modules/defect.py`는 보간 전용 소비자로 유지한다. **rationale**: 빌더가 맵을 생성하므로 XDET-TC-003의 누락률 다리(REQ-CORR-VALIDATE-7)가 실제 게이트 가능해진다(기지 결함 주입 → 빌더 맵 생성 → ground truth 대비 누락률 ≤ EV-103 min). SWR-304의 주기 재검출·diff만 캘리브레이션 운영으로 이연.
2. **gain 배율에 따른 노이즈 모델 갱신** — SWR-201~204는 I₂ = I₁ × G 배율이 XFrame 노이즈 모델(α, σ)에 미치는 영향을 명시하지 않는다. 하류 VST(SWR-701/T5)가 정확한 노이즈 모델을 전제한다면 gain이 (α,σ)를 배율 반영해 전파해야 할 수 있으나, 노이즈 추정 자체는 SWR-701 소관이다. 본 SPEC은 보정 모듈이 노이즈 모델을 재추정·변경하지 않는 것으로 가정. 확인: gain이 노이즈 모델을 배율 전파해야 하는지, 아니면 T5에서 재추정으로 처리하는지.
3. **SWR-602 포화 복원 금지의 적용 경계** — 고정 순서 offset→gain→defect→…→saturation 에서 포화 단계는 defect 이후이므로 defect 보간 시점에는 SATURATION 마스크가 아직 설정되지 않는다. 따라서 SWR-602 복원 금지는 포화 모듈(T3)의 직접 관심사이고, defect 보간의 유사 안전장치는 SWR-303 정상 이웃 전제(REQ-CORR-DEFECT-5)이다. 확인: 캘리브레이션 결함 집합과 장면 포화 집합이 상호 배타적(disjoint)이라는 전제가 유효한지.
4. **[확정 — RESOLVED] SWR-203 결함 후보 이관의 통합 계약** — gain map 범위밖 화소는 (i) 출력값을 gain 미적용 I₁으로 보존하고 DEFECT 플래그를 설정한다(REQ-CORR-GAIN-3). 하류 defect 모듈은 이 **분류 없는** gain 플래그 화소를 **단일점 결함**으로 취급하여 정상 8-이웃 거리 가중 평균으로 보간하고 INTERPOLATION 플래그를 설정한다(REQ-CORR-DEFECT-8). 유효한 정상 이웃이 없으면 REQ-CORR-DEFECT-5(무단 복원 금지)를 따른다. **rationale**: 결정론적 단일 경로 — "맵 결함만 보간 / 마스크만 전달" 분기를 제거하여 gain→defect 고정 순서에서 이관 화소가 반드시 처리되도록 보증한다.
5. **DQE 공식 정정 상태** — 측정프로토콜 v1.0 §1.4의 `DQE = MTF²·q·Ka/NPS`는 IEC 62220-1과 차원 역전으로 상충한다. T1 엔진 구현은 IEC 형태 `DQE = MTF²/(q·Ka·NNPS)`로 정정되어 있고(SPEC-METRICS-001 HISTORY v0.2.0), **상류 REQ 본문(REQ-METRICS-NPS-3)도 IEC 형태로 동기화 완료**(SPEC-METRICS-001 v0.2.1, D6). T2 개선 게이트(REQ-CORR-VALIDATE-2)는 IEC 형태를 참조한다. 확인 잔여: 측정프로토콜 문서 v1.1 개정 반영 시점(참조 문서 정합).
