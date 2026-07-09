---
id: SPEC-DENOISE-001
version: 0.2.0
status: implemented
created: 2026-07-09
updated: 2026-07-09
author: drake.lee
priority: high
issue_number: 6
---

# SPEC-DENOISE-001 — T5 WP5 VST+BM3D 노이즈 저감 처리 모듈 (modules/)

XDET 영상처리 SW P1의 여섯 번째 작업 T5(WP5). 분산 안정화 변환(VST/GAT) + BM3D 노이즈 저감 처리 모듈 `modules/denoise.py`를 T0 프레임워크의 단일 계약 `process(XFrame, CalibSet, Params) -> XFrame` 순수함수형으로 구현한다. 처리는 **(1) GAT 순변환으로 신호 의존 Poisson-Gaussian 노이즈를 단위분산으로 안정화 → (2) BM3D 2단계 denoiser 적용 → (3) exact unbiased 역변환으로 원 신호 영역 복귀**의 3단 구성이며, 역변환은 **점근 역변환((f/2)² 계열) 사용을 금지하고 사전 계산 LUT 기반 exact unbiased inverse만 사용한다(SWR-703 / CLAUDE.md 금지 사항)**. denoise 단계는 고정 파이프라인 순서 offset → gain → defect → lag → line noise → 포화 → 기하 → **denoise** → post 중 전용 `denoise` 스테이지(기하와 post 사이)에서만 실행된다(결정 1 확정, 「결정 필요/확인 사항」 1). 노이즈 모델 (α, σ)는 상류 SPEC(CORR/LNSG)이 재추정을 명시적으로 이연한 **SWR-701의 T5 소관 항목**으로, 실측 선량 계단 데이터 도착 전([B])에는 **기지 (α, σ)를 주입한 합성 Poisson-Gaussian 데이터로 VST 왕복 무편향성·denoiser 성능을 선검증**한다.

- 근거: SWR-701~706(VST+BM3D, FR-C010) · SWR-000-1~12(아키텍처) — `docs/XDET_SWR_spec_v1.2.md`; EVAL v1.1 XDET-EV-201(노이즈 저감·선량 절감) / XDET-EV-102(MTF·SRb 열화) / XDET-EV-101(DQE 변화); TestSpec XDET-TC-010~011; 측정프로토콜(SNR/NPS/MTF 지표 엔진)
- 완료 정의(DoD): **합성 주입 노이즈 저감 효과 + VST 왕복 무편향성을 검증** — 실측 저선량 영상 도착 전, (a) **[하드 DoD] VST 왕복 무편향성**(XDET-TC-011): 기지 평균 λ의 합성 Poisson-Gaussian 패치(저계수 영역 포함)에 GAT 순변환 → exact unbiased 역변환을 **denoiser 우회**로 적용하고, 각 강도 준위의 편향 지표 `bias(λ) = |mean(왕복출력) − λ|`의 정규화 최댓값 `max_j bias(λ_j)/max(λ_j, λ_floor)`([T] `λ_floor`)이 외부 주입 임계 `ε_unbias`([T]) 이내임을 판정한다. (b) **denoising 성능**(XDET-TC-010): 기지 clean + 저선량 노이즈 주입 합성 세트에 VST+BM3D 전 구간을 적용하고 T1 지표 엔진 `metrics/ndt.compute_snr`(SNR 개선 ≥ EV-201 min)·`metrics/mtf.compute_mtf`/`mtf_value_at`(MTF@Nyquist 유지·SRb 열화 ≤ EV-102 min)로 **노이즈 저감이 MTF를 EV 한계 이상으로 파괴하지 않음**을 판정한다. XDET-TC-010·011을 pytest skeleton(skip)에서 실동작 케이스로 전환
- 선행 계약: [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md) — `process` 계약·XFrame 불변·마스크 스택 비트플래그(DEFECT=1/SATURATION=2/INTERPOLATION=4/SATURATION_BAND=8)·이력 체인(`HistoryEntry.extra` 스칼라 진단 위탁 채널)·오케스트레이터 진입 게이트(CalibSet 존재·해상도·패널 ID·유효기간·종류-단계 배선)·import-linter 레이어링(`module → common` 단방향)·`CANONICAL_ORDER`·XFrame `NoiseModel(alpha, sigma)` 필드; [SPEC-METRICS-001](../SPEC-METRICS-001/spec.md) — 판정 엔진 `metrics/ndt.compute_snr`·`metrics/mtf.compute_mtf`/`mtf_value_at`·`metrics/nps.compute_nps`(측정=판정 분리); [SPEC-CORR-001](../SPEC-CORR-001/spec.md) — 선행 offset/gain/defect 모듈·offset 단계 raw 포화 검출(`raw_saturation_threshold` [B] 필수 Params — 무단 기본값 대체 금지 선례)·gain 노이즈 모델 미갱신 결정 계승; [SPEC-LNSG-001](../SPEC-LNSG-001/spec.md) — 포화 마스크 스택 계약(**T5 소비자는 SATURATION + SATURATION_BAND를 함께 제외해야 함** — T3 HISTORY v0.2.0)·`modules/` 처리 패턴·경로 결정론·부록 A 등재 선례; [SPEC-LAG-001](../SPEC-LAG-001/spec.md) — 오프라인 캘리브레이션 빌더 패턴(`metrics/lag_irf.py`가 `metrics→common`으로 CalibSet 방출; 합성 기지 파라미터 선검증)
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.2.0 (2026-07-09)** — 구현 완료(status: implemented). 커밋 0c2927b(denoise/noise_model/스테이지 신설) + 리뷰 결함 10건 수정. 224 passed / 10 skipped(2회 동일), 계약 5건 KEPT. 확정:
  - 역변환 LUT는 도메인 커버리지 검증(λ_max 초과 시 명시 오류, 조용한 클램프 금지), 2차 간격 노드로 16-bit 전역 커버.
  - BM3D 하드 임계는 DC 계수 비임계(그룹 평균 보존), 마스크 픽셀 값은 block-median 충전 후 적층(경계 bleed 차단).
  - XDET-TC-011은 변환 도메인 exact-inverse 속성 + 출하 경로(픽셀별 역변환) e2e 이중 게이트(ε_unbias_e2e [T]).
  - 프리셋 {0.6,0.8,1.0} 전부 EV-102 게이트 — 0.6의 초기 '실패'는 MTF 추정기 아티팩트로 판명(재측정 0.9526 PASS).

- **v0.1.1 (2026-07-09)** — plan-audit iter1(FAIL 0.78, D1~D8 + BLOCK 후보 3건) 반영 개정. run-blocking 「결정 필요/확인 사항」 1·2·3을 orchestrator 결정으로 확정하고(확인 5는 결정 2에 종속 확정), D1~D8 결함을 해소했다.
  1. **결정 1 확정(스테이지 배치)**: `CANONICAL_ORDER`에 전용 `denoise` 스테이지를 `geometry`와 `post` 사이에 신설한다(`… → geometry → denoise → post`). **rationale**: 오케스트레이터의 등록 stages = `CANONICAL_ORDER` 부분수열 검증이 스테이지 신설을 하위호환(하류 미등록 SPEC 무영향)으로 만들고, WP별 개별 스테이지 선례(line_noise/saturation/geometry)를 따르며, denoise 전용 CalibSet를 자체 종류-단계로 배선할 수 있다.
  2. **결정 2 확정(노이즈 모델 소재·CalibKind)**: `common/calibset.py`에 `CalibKind.NOISE = "noise"` 신설 + `_KIND_BY_STAGE["denoise"] = "noise"` + `NOISE_PAYLOAD_KEYS = (alpha, sigma)`(`LAG_PAYLOAD_KEYS` 선례). 오프라인 빌더 `metrics/noise_model.py`가 CalibSet(NOISE)를 방출하고 denoise 모듈이 유일 소비자로서 소비하며(무단 기본값 없음), 해결된 (α, σ)를 **출력 XFrame.noise에 기록**하여 하류 T6(SWR-803)가 재사용한다(D6 해소). 이로써 확인 5(denoise → NOISE 종류-단계 배선)도 확정.
  3. **결정 3 확정(BM3D 코어 = 자체 numpy/scipy 골든 구현)**: v0.1.0 가정 default(오픈 구현 래핑)를 **역전**한다. **rationale(라이선스 실사)**: `bm3d` PyPI는 비상업 커스텀 라이선스 + 클로즈드 바이너리 배포로 **오픈소스가 아니며 소스 감사 불가**, P2 상업화 승계 리스크가 있다. P1 철학은 정확도 단일 목표·속도 최적화 금지이므로 느린 순수 numpy/scipy 골든 구현이 정확히 부합하고, SWR-704 [L] 파라미터를 완전 제어·감사할 수 있다. **신규 의존성 없음**(D3 해소).
  - **D2 해소(VST 무편향 정규화 default)**: 정규화 기준을 상대 편향 `bias(λ)/max(λ, λ_floor)`(`λ_floor`는 [T] 시험 파라미터)로 가정 확정하여 하드 DoD `max_j bias(λ_j)/max(λ_j, λ_floor) ≤ ε_unbias`를 이진 판정 가능하게 한다(확인 7·acceptance Scenario 1 구체화).
  - **D1 해소**: REQ-DENOISE-BM3D-1(BM3D 코어) 전담 시나리오(acceptance Scenario 6 — 원저 파라미터·σ_BM3D = k_s 배선·Params 주입·하드코딩 없음 harness 확인) + DoD 항목 추가, 커버리지 노트 정정(BM3D-1 미커버 갭 제거).
  - **D4 해소**: DQE 변화 판정(EV-101)은 XDET-TC-010 게이트 외임을 Exclusions에 명시(P2/실측 시점 이연).
  - **D5 정정(SWR-706 등급)**: v0.1.0의 마스크 제외(SWR-706)=[S] 표기를 **무등급(부록 A-2 미등재; [S] 등재 요청)**으로 정정(부록 A-2 미등재이므로 [S] 근거 없음). REQ-DENOISE-BM3D-2 인라인 등급으로 반영 — 본 항목이 v0.1.0 grade bullet의 [S] 표기를 supersede.
  - **D7 해소**: acceptance NLM 시나리오의 BM3D 경로 참조를 스테이지 번호가 아닌 **REQ-DENOISE-BM3D-1 경로**로 정정.
  - **D8 해소**: EC-2(점근 역변환 음성 대조)에 점근 역변환은 **테스트 로컬 참조 수식으로만 계산(모듈 경로 아님)**임을 명시(REQ-DENOISE-INV-2 모듈 금지와 무모순).
  - status: draft 유지(annotation 승인 전). run-blocking 1·2·3 확정 완료로 run 착수 가능 상태.
- **v0.1.0 (2026-07-09)** — 초안 생성. GitHub 이슈 #6. 5개 요구 그룹(VST/INV/BM3D/CONTRACT/VALIDATE) EARS 구조 확정. 핵심 범위 결정:
  1. **3단 파이프라인**: GAT 순변환(SWR-702) → BM3D 2단계 denoiser(SWR-704) → exact unbiased 역변환(SWR-703). 역변환은 **점근/대수 역변환 금지(SWR-703 [HARD], CLAUDE.md 금지)**, 사전 계산 LUT + 보간의 exact unbiased inverse만 사용 — Unwanted 요구(REQ-DENOISE-INV-2)로 명문화.
  2. **노이즈 모델 (α, σ) = T5 소관·CalibSet 소비**: (α, σ)는 SWR-701 선량 계단 분산-평균 회귀로 추정되는 [B] 파라미터로, 오프라인 빌더(`metrics/noise_model.py`)가 CalibSet를 방출하고 denoise 단계가 이를 소비한다. XFrame `NoiseModel` 기본값 (0, 0)의 무단 사용 금지(재추정 이연을 CORR/LNSG가 T5로 위임) — 부재·퇴화 시 거부(REQ-DENOISE-VST-2). CalibSet 종류(NOISE 신설 vs OTHER 재사용)·XFrame.noise 기록 위치는 「결정 필요/확인 사항」 2.
  3. **BM3D 코어 구현 경로 = [C] 결정 대상**: SWR-704는 원저(Dabov 2007) 파라미터 [L]을 명시하나 현재 `pyproject.toml`은 numpy/scipy 전용(bm3d 패키지 없음). CLAUDE.md T5는 "BM3D 자체 구현 또는 검증된 오픈 구현 래핑"을 허용 — VST 순/역변환(LUT)은 감사가능·TC-011 게이트 대상이므로 자체 구현, BM3D 코어는 래핑-vs-자체를 「결정 필요/확인 사항」 3으로 이연.
  4. **마스크 가중 제외(SWR-706)**: BM3D 블록 매칭 가중에서 DEFECT·INTERPOLATION·SATURATION·SATURATION_BAND 화소를 제외한다(SWR-706 "Defect·포화" + T3 HISTORY의 SATURATION_BAND 병행 제외 계약 + 보간 합성값 배제). T3가 표시(substrate)만 한 제외 가중을 **T5가 최초로 적용**(LNSG Exclusion "하류 가중 적용은 T5/T6 소관" 계승).
  5. **강도 프리셋**: k_s ∈ {0.6, 0.8, 1.0}([T], SWR-705)는 Params 외부화. 프리셋별 SRb 열화를 XDET-TC-010으로 특성화하고 EV-102 min 초과 프리셋 배제 판정은 특성화표 + 외부 EV 주입으로 이뤄진다(P1 골든모델은 특성화까지; 실 출하 구성 gating은 P2 — 「결정 필요/확인 사항」 6).
  6. **TC 라벨 정정(확정)**: 착수 지시서는 TC-010=VST 왕복 / TC-011=denoising으로 표기했으나, TestSpec v1.0 실제 정의는 **XDET-TC-010 = SNR 개선 + SRb 열화 동시 판정(denoising 성능, EV-201·EV-102 min), XDET-TC-011 = VST 왕복 무편향(합성 Poisson-Gaussian, 편차 임계 내)**이다. 단일 출처 TestSpec v1.0을 채택하여 본 SPEC 전체가 이 매핑을 따른다(「결정 필요/확인 사항」 4).
  - 파라미터 등급 확정(SWR 부록 A 대조): 노이즈 모델 (α, σ)(SWR-701)=[B]; GAT 순변환·exact unbiased 역변환(SWR-702/703)=[L]; BM3D 원저 파라미터(블록 8×8·step 3·N2=16·Ns=39·λ_3D=2.7·Haar·Kaiser β=2.0, SWR-704)=[L]; 강도 계수 k_s(SWR-704)=[P], 프리셋 값 {0.6,0.8,1.0}(SWR-705)=[T]; NLM 대체 경로(SWR-704)=[C]; 마스크 제외(SWR-706)=[S] 표준 규칙. VST 왕복 편향 임계 `ε_unbias`는 판정 튜닝값 [T](부록 A 미등재 — 등재 요청, 「결정 필요/확인 사항」 7).
  - status: draft (run 단계 착수 전까지 유지; 「결정 필요/확인 사항」 1·2·3은 run-blocking 확정 대상).

## Environment / Assumptions

- Python 3.11+, numpy/scipy 기반 float 골든 모델(tech.md). **속도 최적화 금지 — 정확도 단일 목표**(P2에서 최적화). 현재 `pyproject.toml` 의존성은 numpy/scipy 전용이며, BM3D 코어를 자체 numpy/scipy 골든 구현하므로 신규 의존성을 추가하지 않는다(결정 3 확정, 「결정 필요/확인 사항」 3).
- 대상 프레임: 3072×3072 / 3072×2560, 16-bit unsigned raw, pitch 140µm, Nyquist f_N = 3.57 lp/mm(EVAL v1.1 §0).
- **실측 저선량 영상 도착 전 — 합성 데이터로 모듈을 검증한다.** 기지 평균 λ·기지 (α, σ)의 합성 Poisson-Gaussian 프레임(저계수~고계수 준위 sweep)과 기지 clean + 저선량 노이즈 주입 세트(GDS-임상 모사)를 생성하여 VST 왕복 무편향성·denoising 성능을 확인한다(CLAUDE.md T5 주의: VST 왕복 무편향 필수).
- **용어 정의 — 합성 검증 컨텍스트(synthetic-validation context)**: 합성 팬텀 fixture 시험 실행(기지 노이즈/신호 주입 → 처리 후 판정)을 가리키는 단일 용어로, T0(SPEC-INFRA-001)의 검증 모드(validation_mode — float64 병행 버퍼·단계별 중간 XFrame 보존)와는 별개 개념이다. SPEC-CORR/LNSG/LAG의 동명 정의를 계승한다.
- T0 계약 소비: denoise 모듈은 XFrame(불변)을 입력받아 새 XFrame을 반환하는 **무상태 처리 모듈**이며(lag과 달리 내부 상태 없음) `process(XFrame, CalibSet, Params) -> XFrame` 계약을 따른다. 마스크 스택 비트플래그(DEFECT/SATURATION/INTERPOLATION/SATURATION_BAND), 이력 체인, 오케스트레이터 진입 게이트, `CANONICAL_ORDER`를 그대로 소비한다. 의존 방향은 `modules → common` 단방향(import-linter).
- **노이즈 모델 소재**: 노이즈 모델 (α, σ)는 SWR-701의 오프라인 캘리브레이션(선량 계단 1–3에서 픽셀 분산 vs 평균 선형 회귀 → 기울기 α, 절편 σ²; gain 모드별 세트)로 산출되는 [B] 파라미터이며, 오프라인 빌더 `metrics/noise_model.py`(패턴: `metrics/lag_irf.py`·`metrics/defect_map.py`)가 CalibSet를 방출한다. denoise 단계는 이 CalibSet에서 (α, σ)를 소비하며 XFrame `NoiseModel` 기본값 (0, 0)을 무단 사용하지 않는다(무단 기본값 대체 금지, SWR-000-5). 상류 offset/gain/defect/lag/line_noise 단계는 노이즈 모델을 재추정하지 않으므로(CORR 결정 2·LNSG 결정 5), 입력 XFrame.noise가 미설정이면 CalibSet(`CalibKind.NOISE`, 결정 2 확정)가 유일 소재이며, denoise 모듈은 해결된 (α, σ)를 출력 XFrame.noise에 기록한다(하류 T6 재사용, 「결정 필요/확인 사항」 2).
- **마스크 소비**: denoise 모듈은 상류에서 누적된 마스크 스택(defect 단계 DEFECT/INTERPOLATION, offset·gain 단계 SATURATION, 포화 단계 SATURATION_BAND)을 소비하여 BM3D 블록 매칭 가중에서 제외하고, 어떤 마스크 플래그도 신규 설정·해제하지 않는다(마스크 substrate는 상류 소관).
- before/after 판정은 T1 지표 엔진(`metrics/ndt.compute_snr`·`metrics/mtf`·`metrics/nps`)을 소비하되, 모듈은 `metrics`를 import할 수 없으므로(CONTRACT-3) 판정 로직은 **시험 코드(`tests/`)에서** 모듈 + 엔진을 함께 소비한다.
- 물리·튜닝·[B] 상수(노이즈 모델 α·σ, BM3D 원저 파라미터, 강도 계수 k_s·프리셋, VST 편향 임계 ε_unbias, 정규화 하한 λ_floor)는 전부 Params/CalibSet로 외부화한다(하드코딩 금지). 등급은 SWR 부록 A를 따른다.
- EV 판정 수치(EVAL v1.1 EV-201/102 (EV-101은 근거 맥락 인용 — 주입·판정 대상 아님) min/typ/max)는 **엔진·모듈 외부에서 주입**된다(측정=판정 분리, METRICS/CORR/LNSG/LAG 계승).

## Requirements (EARS)

### REQ-DENOISE-VST — VST 순변환(GAT) + 노이즈 모델 소비 (SWR-701~702, FR-C010)

- **REQ-DENOISE-VST-1 (Event-Driven)** — WHEN denoise 모듈이 입력 XFrame을 처리하면, THEN 시스템은 소비 CalibSet(`CalibKind.NOISE`, 결정 2 확정)의 노이즈 모델 (α, σ)로 GAT 순변환 `f(z) = (2/α)·√(α·z + (3/8)·α² + σ²)`을 적용하고, 근호 인자가 정의역 미만인 화소는 0으로 클램프해야 한다(SWR-702, [L]). (α, σ)는 SWR-701 선량 계단 분산-평균 회귀로 산출되는 [B] 파라미터로 부록 A를 따른다.
- **REQ-DENOISE-VST-2 (Unwanted)** — IF denoise 단계에 유효한 노이즈 모델 (α, σ)가 부재하거나 퇴화(α ≤ 0, 또는 XFrame `NoiseModel` 기본값 (0, 0)만 존재)하면, THEN 시스템은 GAT를 무단 기본값으로 수행하지 않고 명시 오류로 거부해야 한다(무단 기본값 대체 금지, SWR-000-5; `raw_saturation_threshold` 필수 Params 선례 계승). 결정론적 단일 경로 — 추정·대체 분기 없음.
- **REQ-DENOISE-VST-3 (Ubiquitous)** — 노이즈 모델 (α, σ) 산출은 처리 모듈이 아닌 오프라인 캘리브레이션 빌더(`metrics/noise_model.py`, `metrics → common` 단방향; 선량 계단 분산 vs 평균 선형 회귀 → 기울기 α·절편 σ²; gain 모드별 세트)가 담당하며 CalibSet를 방출해야 한다(SWR-701; `metrics/lag_irf.py`·`metrics/defect_map.py` 빌더 선례). 빌더는 처리 파이프라인 단계가 아니므로 `modules`의 `metrics` import 금지 규칙과 무관하다.

### REQ-DENOISE-INV — exact unbiased 역변환(LUT) + 점근 역변환 금지 (SWR-703, FR-C010)

- **REQ-DENOISE-INV-1 (Event-Driven)** — WHEN GAT 영역 denoiser 출력을 원 신호 영역으로 복귀시키면, THEN 시스템은 exact unbiased inverse(Mäkitalo & Foi 2011)를 사전 계산 LUT + 보간으로 적용해야 한다(SWR-703, [L]). LUT는 (α, σ)로부터 결정론적으로 구성되며 감사 가능해야 한다.
- **REQ-DENOISE-INV-2 (Unwanted)** — IF 점근/대수 역변환((f/2)² 계열 등 asymptotic inverse)으로 GAT를 되돌리는 경로가 사용되면, THEN 시스템은 이를 금지하고 exact unbiased LUT 역변환만 수행해야 한다(저신호 편향 유발, SWR-703 [HARD] / CLAUDE.md 금지 사항 "점근 역 Anscombe 사용"). 결정론적 단일 경로 — 조건부 점근 분기 없음.

### REQ-DENOISE-BM3D — BM3D denoiser 코어 + 강도 프리셋 + 마스크 가중 (SWR-704~706, FR-C010)

- **REQ-DENOISE-BM3D-1 (Event-Driven)** — WHEN GAT 순변환으로 단위분산 안정화된 영상에 denoiser를 적용하면, THEN 시스템은 BM3D 2단계(hard-threshold + Wiener)를 원저 기본 파라미터 [L](블록 8×8, step 3, 유사블록 최대 N2=16, 탐색창 Ns=39, hard-threshold λ_3D=2.7, 3차원 변환 Haar, Kaiser β=2.0)로 수행하되 잡음 표준편차는 σ_BM3D = 1(GAT 후 단위분산) × 강도 계수 k_s([P])로 설정해야 한다(SWR-704). BM3D 원저 파라미터·k_s는 Params 외부화(부록 A). 코어는 자체 순수 numpy/scipy 골든 구현이다(신규 의존성 없음, 결정 3 확정, 「결정 필요/확인 사항」 3).
- **REQ-DENOISE-BM3D-2 (Ubiquitous)** — denoiser는 블록 매칭 가중에서 XFrame 마스크의 DEFECT · INTERPOLATION · SATURATION · SATURATION_BAND 화소를 제외해야 하며(SWR-706 "Defect·포화 마스크" — 부록 A-2 미등재로 **무등급([S] 등재 요청)** + T3 HISTORY의 SATURATION_BAND 병행 제외 계약 + defect 보간 합성값 배제; 마스크연산 공용 컴포넌트 SWR-000-9 소비), 마스크 플래그를 신규 설정·해제하지 않아야 한다(마스크 substrate는 상류 소관).
- **REQ-DENOISE-BM3D-3 (Event-Driven)** — WHEN 강도 프리셋 k_s가 선택되면, THEN 시스템은 k_s ∈ {0.6(약), 0.8(중), 1.0(강)}([T], SWR-705) 중 Params로 지정된 값을 사용해야 하며, 프리셋별 SRb 열화 특성화 결과(XDET-TC-010)를 산출할 수 있어야 한다(EV-102 min 초과 프리셋 배제 판정의 입력; 배제 gating 자체는 P1 범위 밖 — 「결정 필요/확인 사항」 6).
- **REQ-DENOISE-BM3D-4 (Optional)** — WHERE Params가 NLM 대체 denoiser 경로(SWR-704 [C])를 선택하면, 시스템은 BM3D 대신 NLM을 동일한 VST 순/역변환·마스크 가중 제외 계약 하에서 적용해야 한다. 대체 경로 미선택 시 본 요구는 적용되지 않으며 REQ-DENOISE-BM3D-1(BM3D) 경로를 사용한다. 경로 선택은 Params 값으로 결정론적으로 이뤄진다.

### REQ-DENOISE-CONTRACT — 공통 모듈 계약 준수 (SWR-000-2~12, REQ-INFRA-* 소비)

- **REQ-DENOISE-CONTRACT-1 (Ubiquitous)** — denoise 모듈은 단일 시그니처 `process(XFrame, CalibSet, Params) -> XFrame` 순수함수형이어야 하며(SWR-000-7, REQ-INFRA-CONTRACT-1), 입력 XFrame을 불변으로 취급(원본 미변경)하고 새 XFrame을 반환해야 한다(SWR-000-3, REQ-INFRA-DATA-6). 모듈은 내부 상태를 보유하지 않는다(lag과 달리 상태 재귀 없음).
- **REQ-DENOISE-CONTRACT-2 (Event-Driven)** — WHEN denoise 모듈이 출력 XFrame을 생성하면, THEN 시스템은 처리 메타(모듈 버전 · 파라미터 해시 · 소비 CalibSet ID)와 스칼라 진단(적용 k_s · 클램프율 · 해결된 (α, σ) 등)을 이력 체인 엔트리(`HistoryEntry.extra`)에 결정론적으로 추가해야 한다(SWR-000-4, REQ-INFRA-DATA-4, IEC 62304 추적). 하류 T6(SWR-803 노이즈 게이팅)가 재사용할 수 있도록 해결된 노이즈 모델 (α, σ)를 출력 XFrame.noise 필드에 기록해야 한다(결정 2 확정, 「결정 필요/확인 사항」 2).
- **REQ-DENOISE-CONTRACT-3 (Ubiquitous)** — 의존 방향은 `modules → common` 단방향이어야 하며, denoise 모듈은 다른 처리 모듈 · `pipeline` · `metrics`를 import해서는 안 된다(SWR-000-8, REQ-INFRA-STATIC import-linter 계약). 실행 순서·조합은 오케스트레이터 단독 소관이며 모듈 간 직접 호출은 금지된다(REQ-INFRA-ORCH-1/2). 지표 엔진(`metrics/ndt`·`metrics/mtf`·`metrics/nps`) 소비는 `tests/`에서만 이뤄진다.
- **REQ-DENOISE-CONTRACT-4 (Unwanted)** — IF denoise 모듈이 XFrame 컨테이너 외 채널(전역 상태 · 부가 반환값 · 파일 우회)로 데이터를 전달하려 하면, THEN 시스템은 이를 계약 위반으로 취급해야 한다(SWR-000-6 사이드채널 금지). 자동 검출 가능 범위는 시그니처·부가 반환값 위반(계약 검사)과 의존 방향 위반(import-linter 정적 검사)이며(acceptance.md EC-4의 검증 범위와 동일), 전역 상태·파일 우회는 테스트 가능 AC가 아닌 설계 규칙으로서 코드 리뷰 게이트로 다룬다(SPEC-INFRA-001 REQ-INFRA-DATA-2 방식 계승).
- **REQ-DENOISE-CONTRACT-5 (Unwanted)** — IF 등록된 denoise 단계의 CalibSet(노이즈 모델)이 부재하거나 불일치(해상도 · 패널 ID · 유효기간, 그리고 종류-단계 배선)하면, THEN 오케스트레이터 진입 게이트가 처리를 거부하고 명시 오류를 발생시켜야 한다(무단 기본값 대체 금지, SWR-000-5, REQ-INFRA-ORCH-4). 종류-단계 배선은 denoise → `CalibKind.NOISE`이다(결정 2·5 확정, 「결정 필요/확인 사항」 2·5).
- **REQ-DENOISE-CONTRACT-6 (Ubiquitous)** — denoise 모듈은 고정 파이프라인 순서 `CANONICAL_ORDER`의 전용 `denoise` 스테이지(기하와 post 사이, 결정 1 확정)에서만 실행되어야 하며(SWR-000-2, REQ-INFRA-ORCH-3; 등록 stages는 `CANONICAL_ORDER`의 부분수열), 합성 입력 + 기대 출력 fixture로 harness 단독 시험이 가능해야 한다(SWR-000-11, XDET-TC-000).

### REQ-DENOISE-VALIDATE — 합성 검증(VST 왕복 무편향 + denoising 성능) (XDET-TC-010~011, EV-201/102 (EV-101은 근거 맥락 인용 — 주입·판정 대상 아님))

- **REQ-DENOISE-VALIDATE-1 (State-Driven)** — WHILE 실측 저선량 영상 도착 전 합성 검증 컨텍스트인 동안, 시스템은 기지 (α, σ)·기지 신호를 주입한 합성 Poisson-Gaussian 데이터로 VST 왕복 무편향성·denoising 성능을 보여야 한다(DoD 전제, CLAUDE.md T5).
- **REQ-DENOISE-VALIDATE-2 (Event-Driven)** — WHEN 기지 평균 λ의 합성 Poisson-Gaussian 패치(저계수 영역 포함)에 GAT 순변환 → exact unbiased 역변환을 **denoiser 우회**로 적용하면, THEN 시스템은 각 강도 준위의 편향 지표 `bias(λ) = |mean(왕복출력) − λ|`를 산출하고 그 정규화 최댓값 `max_j bias(λ_j)/max(λ_j, λ_floor)`([T] `λ_floor` — 저계수 발산 방지 하한)가 외부 주입 임계 `ε_unbias`([T]) 이내임을 `tests/`에서 이진 판정 가능해야 한다(XDET-TC-011 "VST 왕복 무편향, 편차 임계 내"). 이것이 T5의 하드 DoD이다.
- **REQ-DENOISE-VALIDATE-3 (Event-Driven)** — WHEN 기지 clean + 저선량 노이즈 주입 합성 세트(GDS-임상 모사)에 VST+BM3D 전 구간을 적용하면, THEN 시스템은 `tests/`에서 (a) 균일 ROI SNR 개선율을 `metrics/ndt.compute_snr`로 산출하여 EV-201 min(SNR 개선 ≥ +20%) 이상, (b) 엣지 특징 MTF@Nyquist 유지율·SRb 열화를 `metrics/mtf.compute_mtf`/`mtf_value_at`로 산출하여 EV-102 min(MTF@Nyquist 유지율 ≥ 90%, SRb 열화 ≤ 10%) 이내임을 판정 가능해야 한다(XDET-TC-010 "SNR 개선 + SRb 열화 동시 판정" — 노이즈 저감이 MTF를 EV 한계 이상으로 파괴하지 않음).
- **REQ-DENOISE-VALIDATE-4 (Event-Driven)** — WHEN 각 강도 프리셋 k_s ∈ {0.6, 0.8, 1.0}로 denoising을 적용하면, THEN 시스템은 프리셋별 SRb 열화(및 SNR 개선)를 `tests/`에서 특성화표로 산출하여 EV-102 min과 비교 가능해야 한다(SWR-705 사전 특성화). 실제 프리셋 배제·출하 구성 gating은 P1 범위 밖이다(「결정 필요/확인 사항」 6).
- **REQ-DENOISE-VALIDATE-5 (Ubiquitous)** — EV-201/102 (EV-101은 근거 맥락 인용 — 주입·판정 대상 아님) min/typ/max 및 VST 편향 임계 `ε_unbias` 판정 수치는 EVAL v1.1/Params에서 외부 주입되어야 하며, 검증은 산출값과 외부 임계의 비교로만 이뤄져야 한다(측정=판정 분리 계승). 처리 모듈·판정 코드는 게이트 임계를 내장하지 않는다.
- **REQ-DENOISE-VALIDATE-6 (Ubiquitous)** — 시험 케이스 XDET-TC-010 · XDET-TC-011은 현재 pytest skeleton(skip)에서 합성 입력·판정 연동의 실동작 케이스로 전환되어야 한다(REQ-INFRA-CI-1 계승). 모듈은 `metrics`를 import하지 않으므로 SNR/MTF/NPS 판정은 `tests/`에서 모듈 + 지표 엔진을 함께 소비하고, VST 왕복 편향은 `tests/`에서 기지 λ 대조 직접 측정으로 판정한다.

## Exclusions (What NOT to Build)

- **후속·타 WP 처리 모듈 없음** — MSE/DRC·자동 윈도잉·GSDF(SWR-801~805·901~903/T6), grid 억제(SWR-1001~1006/T7), 커널 virtual grid(SWR-1101~1103/T8), NDT(SWR-1201~1204/T9), 티어·동일성(SWR-1301~1303/T10)은 T5 범위 밖. 선행 offset/gain/defect(T2)·lag(T4)·line noise/포화/기하(T3)도 본 SPEC 범위 밖.
- **노이즈 게이팅(SWR-803) 없음** — 레벨별 로컬 노이즈 추정 σ_ℓ 기반 증폭 억제 게이트는 T6(WP6 MSE) 소관. T5는 (α, σ) 모델을 산출·소비하고, 해결된 (α, σ)를 출력 XFrame.noise 필드에 기록하여 하류 T6(SWR-803)가 재사용하도록 전달만 한다(게이팅 자체는 미구현, 결정 2 확정).
- **DQE 변화 판정(EV-101) 없음** — EVAL v1.1 XDET-EV-101(DQE 변화)은 XDET-TC-010 게이트(SNR 개선·SRb 열화, EV-201·EV-102) 밖이다 — P2/실측 시점 이연. T5는 DQE 변화를 판정하지 않으며, EV-101은 근거 맥락으로만 인용한다.
- **실측 (α, σ) [B] 확정 없음** — SWR-701 선량 계단 실측 (α, σ)의 확정은 2단계 실측 도착 후. Gen 1은 기지 (α, σ) 주입 합성 데이터로 빌더·모듈을 선검증한다.
- **점근 역변환 경로 없음** — (f/2)² 계열 asymptotic inverse는 구현하지 않는다(REQ-DENOISE-INV-2, CLAUDE.md 금지). exact unbiased LUT 역변환만 존재한다.
- **포화 "복원" 없음** — 포화 화소는 마스크 제외 가중 대상일 뿐 denoiser가 신호를 재구성하지 않는다(SWR-602 [HARD] 복원 금지 계승). 마스크 플래그 신규 설정·해제 없음.
- **DL·hallucination 검출 없음** — EV-201의 "DL hallucination 0건"은 Gen 2(DL) 항목으로 P1 골든모델 범위 밖. P1 denoiser는 결정론적 BM3D(또는 NLM)이다.
- **프리셋 배제·출하 구성 gating 없음** — SWR-705의 EV-102 min 초과 프리셋 "출하 구성 배제"는 특성화표 산출까지만 T5가 담당하고, 실제 구성 gating은 P2/config 소관(「결정 필요/확인 사항」 6).
- **선량 절감률 실측 판정 없음** — EV-201의 선량 절감률(≥15%)은 동등 화질 기준 실측 비교로, 실 저선량/기준 선량 페어 데이터 도착 후. P1은 SNR 개선 대리 지표로 판정.
- **EV 게이트 임계 내장 없음** — EV-201/102 (EV-101은 근거 맥락 인용 — 주입·판정 대상 아님) 및 ε_unbias 수치는 외부 주입. 처리 모듈·판정 코드는 합격/불합격 임계를 내장하지 않는다.
- **성능·처리시간·티어 게이트 없음** — EV-401/402, XDET-TC-020/021은 P2.

## 결정 필요/확인 사항

SWR 조항이 T0/T1 구현과 모호하거나 상충하는 지점. plan-audit iter1 반영으로 「1·2·3」(run-blocking)·「4·5」는 **[확정 — RESOLVED]**, 「6·7」은 확인 대상이다(「7」은 정규화 default 가정 확정). 각 항목은 가정 default를 명시하되 최종 확정은 orchestrator 결정을 따랐다.

1. **[확정 — RESOLVED] denoise 파이프라인 스테이지 배치** — `CANONICAL_ORDER = offset → gain → defect → lag → line_noise → saturation → geometry → post`에는 medical-post용 단일 `post` 스테이지만 있으나, T5~T10(denoise·MSE/DRC·grid·virtual grid·NDT·티어)이 모두 이 한 슬롯에 대응해야 한다. **확정**: 전용 `denoise` 스테이지를 `geometry`와 `post` 사이에 신설한다(`CANONICAL_ORDER = … → geometry → denoise → post`). **rationale**: 오케스트레이터 진입 게이트는 등록 stages가 `CANONICAL_ORDER`의 부분수열이면 통과하므로 스테이지 신설은 하류 미등록 SPEC에 하위호환(무영향)이고, WP별 개별 스테이지 선례(line_noise/saturation/geometry)를 따르며, denoise 전용 CalibSet를 자체 종류-단계로 배선할 수 있다(대안 "기존 `post` 실현"은 T6+ post 모듈과 충돌하므로 기각). 확인(이연): T6+ 도착 시 post 하위 순서(다중 post 스테이지 vs 서브파이프라인)는 각 후속 SPEC이 본 결정과 독립적으로 재확인한다.
2. **[확정 — RESOLVED] 노이즈 모델 (α, σ) 소재와 CalibSet 종류** — SWR-701은 (α, σ)를 gain 모드별 캘리브레이션 파일로 저장한다고 명시하나, XFrame도 `NoiseModel(alpha, sigma)` 필드를 보유하고 `common/calibset.py` `CalibKind`에는 NOISE 종류가 없었다(OFFSET/GAIN/DEFECT/LAG/LINE_NOISE/OTHER). 상류 단계는 XFrame.noise를 설정하지 않는다(CORR/LNSG 재추정 이연). **확정**: `common/calibset.py`에 `CalibKind.NOISE = "noise"`를 신설하고 `_KIND_BY_STAGE["denoise"] = "noise"`·`NOISE_PAYLOAD_KEYS = (alpha, sigma)`를 등재한다(`LAG_PAYLOAD_KEYS` 선례). 오프라인 빌더 `metrics/noise_model.py`가 CalibSet(NOISE)를 방출하고 denoise 모듈이 **유일 소비자**로서 소비하며(무단 기본값 없음, REQ-DENOISE-VST-2), 해결된 (α, σ)를 **출력 XFrame.noise 필드에 기록**하여 하류 T6(SWR-803)가 재사용한다. **rationale**: LINE_NOISE/LAG가 각자 CalibKind + payload-key 선례를 세웠고, NOISE 신설이 OTHER 재사용보다 종류-단계 배선 게이트를 강제하여 무단 기본값 대체를 구조적으로 차단한다(D6 해소). 이로써 확인 5(종류-단계 배선)도 확정된다.
3. **[확정 — RESOLVED] BM3D 코어 구현 경로(자체 구현 vs 오픈 구현 래핑)** — SWR-704는 원저(Dabov 2007) 파라미터 [L]을 명시하나 현재 `pyproject.toml`은 numpy/scipy 전용(bm3d 패키지 없음)이고 CLAUDE.md T5는 BM3D 자체 구현과 오픈 구현 래핑을 모두 허용한다. VST 순/역변환(GAT + exact unbiased LUT)은 XDET-TC-011 게이트 대상·감사 필수이므로 자체 구현이 전제된다. **확정**: BM3D 코어도 **자체 순수 numpy/scipy 골든 구현**한다(v0.1.0 가정 default였던 오픈 구현 래핑을 **역전**). **rationale(라이선스 실사)**: `bm3d` PyPI 패키지는 비상업(non-commercial) 커스텀 라이선스 + 클로즈드 바이너리 배포로 **오픈소스가 아니며 소스 감사가 불가**하고 P2 상업화 시 승계 리스크가 있다. 또한 P1 철학은 정확도 단일 목표·속도 최적화 금지이므로 **느린 순수 numpy/scipy 골든 구현이 정확히 부합**하며, SWR-704 [L] 파라미터(블록 8×8·step 3·N2=16·Ns=39·λ_3D=2.7·Haar·Kaiser β=2.0)를 완전 제어·감사할 수 있다. **신규 의존성 없음**(numpy/scipy 전용 정책 유지). 확인(이연): 자체 구현의 원저 파라미터 특성화 부담(대규모 정확도 빌드), NLM 대체 경로(SWR-704 [C], REQ-DENOISE-BM3D-4) 유지 여부.
4. **[확정 — RESOLVED] XDET-TC 라벨 매핑** — 착수 지시서는 TC-010=VST 왕복 / TC-011=denoising으로 표기했으나, **확정**: 단일 출처 TestSpec v1.0의 실제 정의(**XDET-TC-010 = SNR 개선 + SRb 열화 동시 판정(denoising 성능, EV-201·EV-102 min); XDET-TC-011 = VST 왕복 무편향(합성 Poisson-Gaussian, 편차 임계 내)**)를 채택한다. 본 SPEC 전체(REQ-DENOISE-VALIDATE-2/3, acceptance)가 이 매핑을 따른다. **rationale**: TestSpec v1.0이 TC 정의의 단일 출처이며(house style: 측정=판정 분리·TC 단일 출처), 지시서 라벨은 편의 표기였다.
5. **[확정 — RESOLVED] denoise 단계 종류-단계 배선** — 결정 1의 전용 `denoise` 스테이지 신설과 결정 2의 `CalibKind.NOISE` 신설에 따라 종류-단계 배선이 결정된다. **확정**: `_KIND_BY_STAGE["denoise"] = "noise"`를 등재하여 CalibSet 종류를 강제하고, 진입 게이트가 종류-단계 불일치를 거부한다(REQ-DENOISE-CONTRACT-5; line_noise 선례). **rationale**: 결정 2 참조 — 종류 강제가 무단 기본값 대체를 구조적으로 차단한다(OTHER 재사용 시 종류 미강제라 기각).
6. **[확인] SWR-705 프리셋 배제 "출하 구성" 의미** — P1 골든모델에는 출하 구성 개념이 없다. **가정 default**: T5는 프리셋별 SRb 열화 특성화표만 산출(REQ-DENOISE-VALIDATE-4)하고, EV-102 min 초과 프리셋 배제 판정은 특성화표 + 외부 EV 주입으로 표현하되 실제 구성 gating은 P2/config 소관으로 이연한다. 확인: 특성화표를 이력 메타/리포트 중 어디에 산출할지.
7. **[확인] VST 편향 임계 `ε_unbias`·정규화 기준·`λ_floor`의 부록 A 등재** — VST 왕복 무편향 판정 임계 `ε_unbias`와 정규화 기준은 SWR 본문·부록 A 미등재이다. **가정 default(D2 반영)**: 정규화 기준을 **상대 편향** `bias(λ)/max(λ, λ_floor)`로 확정하고(저계수에서 λ 나눗셈 발산 방지 위해 하한 `λ_floor` 도입), `ε_unbias`·`λ_floor`를 모두 판정 튜닝값 [T]로 Params 외부화하며 부록 A 등재를 요청한다(LNSG `line_max_width`·경계 밴드 폭 부록 A 등재 선례). 이로써 하드 DoD `max_j bias(λ_j)/max(λ_j, λ_floor) ≤ ε_unbias`가 이진 판정 가능하다. 확인: `ε_unbias`·`λ_floor`의 [T]/[P] 등재 등급, `λ_floor` 기본값 크기.
