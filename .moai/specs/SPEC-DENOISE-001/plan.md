# SPEC-DENOISE-001 구현 계획 (plan.md)

T5(WP5) VST+BM3D 노이즈 저감. `modules/denoise.py`(무상태 처리 모듈) + `metrics/noise_model.py`(오프라인 (α,σ) 캘리브레이션 빌더)를 구현하고, VST 순변환 → BM3D denoiser → exact unbiased 역변환의 3단 처리를 T0 계약 `process(XFrame, CalibSet, Params) -> XFrame`으로 실현한다. 근거: [spec.md](./spec.md) · 인수 기준: [acceptance.md](./acceptance.md).

> **버전 0.1.1 (2026-07-09)** — plan-audit iter1(FAIL 0.78, D1~D8 + BLOCK 후보 3건) 반영: 「결정 필요/확인 사항」 1·2·3·5 확정(결정 1 전용 `denoise` 스테이지; 결정 2 `CalibKind.NOISE` 신설·출력 XFrame.noise 기록; 결정 3 BM3D 자체 numpy/scipy 골든 구현), D1~D8 해소. spec.md HISTORY v0.1.1 참조.

## 선행 조건 (확정 완료)

「결정 필요/확인 사항」 1·2·3·5는 plan-audit iter1에서 orchestrator 결정으로 **확정**되었다(spec.md HISTORY v0.1.1). run-blocking 해소.

- **결정 1(스테이지 배치) 확정**: 전용 `denoise` 스테이지를 `geometry`와 `post` 사이에 신설(`CANONICAL_ORDER = … → geometry → denoise → post`). 등록 stages = 부분수열 검증으로 하류 미등록 SPEC에 하위호환.
- **결정 2(노이즈 모델 소재/CalibKind) 확정**: `CalibKind.NOISE = "noise"` 신설 + `_KIND_BY_STAGE["denoise"] = "noise"` + `NOISE_PAYLOAD_KEYS = (alpha, sigma)`. 빌더가 CalibSet(NOISE) 방출, 모듈이 유일 소비자, 해결된 (α,σ)를 출력 XFrame.noise에 기록. 확인 5(종류-단계 배선)도 확정.
- **결정 3(BM3D 코어) 확정**: BM3D 코어 = 자체 순수 numpy/scipy 골든 구현(v0.1.0 오픈 구현 래핑 default를 역전). `bm3d` PyPI는 비상업 라이선스·클로즈드 바이너리로 감사 불가 — **신규 의존성 없음**.

## 기술 접근 (WHAT — HOW 세부는 run 소관)

- **3단 파이프라인**: (1) GAT 순변환으로 신호 의존 Poisson-Gaussian을 단위분산으로 안정화 → (2) BM3D 2단계(hard-threshold + Wiener) 또는 NLM 대체 → (3) exact unbiased LUT 역변환. 역변환은 점근/대수 역변환 금지(감사 가능 LUT만).
- **측정=판정 분리**: 모듈은 EV 임계·판정 로직을 내장하지 않는다. SNR/MTF/NPS 판정은 `tests/`에서 T1 지표 엔진(`metrics/ndt.compute_snr`·`metrics/mtf`·`metrics/nps`)을 소비하고, VST 왕복 편향은 기지 λ 대조 직접 측정으로 판정한다.
- **오프라인 빌더 패턴**: (α,σ) 추정은 처리 모듈이 아닌 `metrics/noise_model.py` 빌더(`metrics → common`)가 담당하여 CalibSet를 방출한다(`metrics/lag_irf.py`·`metrics/defect_map.py` 선례). 이 분리가 노이즈 모델 산출을 게이트 가능한 캘리브레이션 산물로 만든다.
- **마스크 가중 최초 적용**: T3가 표시만 한 SWR-706 제외 가중(DEFECT·INTERPOLATION·SATURATION·SATURATION_BAND)을 T5가 블록 매칭에서 최초 적용한다.

## 마일스톤 (우선순위 순 — 시간 추정 없음)

### M0 — 선행 결정 확정 (Priority: High, 완료)
- 「결정 필요/확인 사항」 1·2·3·5를 orchestrator 결정으로 확정하고 spec.md HISTORY v0.1.1에 반영 완료(house style: 항목 번호 유지 + `[확정 — RESOLVED]` + rationale).
- 확정 산출: (a) 전용 `denoise` 스테이지(기하와 post 사이)·`CANONICAL_ORDER` 위치, (b) `CalibKind.NOISE` 신설·`_KIND_BY_STAGE["denoise"]="noise"`·출력 XFrame.noise 기록, (c) BM3D 코어 = 자체 numpy/scipy 골든 구현(신규 의존성 없음).

### M1 — 노이즈 모델 빌더 + CalibSet 스키마 (Priority: High)
- `metrics/noise_model.py`: 선량 계단 분산 vs 평균 선형 회귀 → 기울기 α·절편 σ² 산출, gain 모드별 CalibSet(`CalibKind.NOISE`) 방출(SWR-701). 합성 기지 (α,σ) 주입 데이터로 회귀 정확도 선검증.
- `common/calibset.py`에 `CalibKind.NOISE = "noise"`·`_KIND_BY_STAGE["denoise"]="noise"`·`NOISE_PAYLOAD_KEYS=(alpha, sigma)` 신설(결정 2, `LAG_PAYLOAD_KEYS` 선례).
- 대응: REQ-DENOISE-VST-3.

### M2 — VST 순변환 + exact unbiased 역변환 (Priority: High, 하드 DoD 핵심)
- GAT 순변환(SWR-702, 정의역 미만 0 클램프) + exact unbiased inverse LUT 구성·보간(SWR-703). 자체 구현(numpy/scipy, 감사 가능).
- 점근 역변환 부재 보장(REQ-DENOISE-INV-2, Unwanted 단일 경로).
- 대응: REQ-DENOISE-VST-1/2, REQ-DENOISE-INV-1/2. **하드 DoD(XDET-TC-011)의 알고리즘 근간.**

### M3 — BM3D denoiser 코어 + 마스크 가중 + 강도 프리셋 (Priority: High)
- BM3D 2단계 원저 파라미터 [L](블록 8×8·step3·N2=16·Ns=39·λ2.7·Haar·Kaiser β=2.0) + σ_BM3D = 1 × k_s([P]), 전부 Params 주입(하드코딩 없음). **자체 순수 numpy/scipy 골든 구현**(결정 3, 신규 의존성 없음).
- 마스크 제외 가중(REQ-DENOISE-BM3D-2): DEFECT·INTERPOLATION·SATURATION·SATURATION_BAND(SWR-706 — 부록 A-2 미등재로 무등급, [S] 등재 요청).
- 강도 프리셋 k_s ∈ {0.6,0.8,1.0}([T]) Params 외부화. NLM 대체 경로(Optional, REQ-DENOISE-BM3D-4).
- 대응: REQ-DENOISE-BM3D-1/2/3/4.

### M4 — 모듈 계약·오케스트레이터 통합 (Priority: High)
- `process(XFrame,CalibSet,Params)->XFrame` 무상태 순수함수, 불변성·이력 체인(`HistoryEntry.extra`에 k_s·클램프율·해결된 (α,σ))·의존 방향(`module → common`)·harness 단독 시험.
- 전용 `denoise` 스테이지(기하와 post 사이)를 `CANONICAL_ORDER`에, `_KIND_BY_STAGE["denoise"]="noise"`를 배선(결정 1·5), 진입 게이트 거부 경로(CalibSet 부재/불일치). 해결된 (α,σ)를 출력 XFrame.noise에 기록(결정 2, REQ-DENOISE-CONTRACT-2).
- 대응: REQ-DENOISE-CONTRACT-1~6.

### M5 — 합성 검증 + TC 전환 (Priority: High)
- XDET-TC-011(VST 왕복 무편향, 하드 DoD): 기지 λ sweep(저계수 포함) → GAT → exact inverse(denoiser 우회) → `max_j bias(λ_j)/max(λ_j, λ_floor) ≤ ε_unbias`([T] `ε_unbias`·`λ_floor`, D2 확정). 점근 역변환 음성 대조(테스트 로컬 참조 수식, 모듈 경로 아님) 포함.
- BM3D 코어 전담 검증(acceptance Scenario 6, D1): 원저 파라미터·σ_BM3D=k_s 배선·Params 주입·하드코딩 없음 harness 확인(REQ-DENOISE-BM3D-1).
- XDET-TC-010(denoising 성능): 저선량 합성 세트 → VST+BM3D → SNR 개선 ≥ EV-201 min, MTF@Nyquist 유지·SRb 열화 ≤ EV-102 min. 프리셋별 특성화표(REQ-DENOISE-VALIDATE-4).
- pytest skeleton(skip) → 실동작 케이스 전환(REQ-DENOISE-VALIDATE-6).
- 대응: REQ-DENOISE-VALIDATE-1~6, acceptance 전 시나리오.

## 산출물

| 경로 | 역할 | 대응 REQ |
|---|---|---|
| `modules/denoise.py` | VST+BM3D 처리 모듈(무상태) | VST/INV/BM3D/CONTRACT |
| `metrics/noise_model.py` | (α,σ) 오프라인 캘리브레이션 빌더 | VST-3 |
| `common/calibset.py` | `CalibKind.NOISE`·`_KIND_BY_STAGE["denoise"]`·`NOISE_PAYLOAD_KEYS` 신설(결정 2) | VST-1, CONTRACT-5 |
| `pipeline/orchestrator.py` | denoise 스테이지 `CANONICAL_ORDER`(기하와 post 사이)·`_KIND_BY_STAGE` 배선(결정 1·5) | CONTRACT-5/6 |
| `tests/…` | XDET-TC-010/011 실동작 케이스 + harness fixture(BM3D-1 코어 포함) | VALIDATE, BM3D-1 |

> `pyproject.toml`은 변경 없음 — BM3D 자체 numpy/scipy 구현으로 신규 의존성 미추가(결정 3).

## 리스크 및 완화

- **[High] VST 왕복 무편향 미달(저계수 편향)** — 점근 역변환 사용 시 저신호 편향으로 XDET-TC-011 실패. 완화: exact unbiased LUT만 사용(REQ-DENOISE-INV-2), 저계수 λ 패치를 sweep에 필수 포함, 점근 음성 대조로 필요성 입증.
- **[High] 노이즈 저감이 MTF 파괴(EV-102 초과)** — 과도한 k_s가 SRb 열화. 완화: 프리셋별 특성화(REQ-DENOISE-VALIDATE-4), MTF@Nyquist 유지율 EV-102 min 게이트, 마스크 제외로 구조 경계 오염 억제.
- **[Medium] 노이즈 모델 (α,σ) 무단 기본값** — XFrame 기본 (0,0) 사용 시 GAT 발산. 완화: 부재·퇴화 거부(REQ-DENOISE-VST-2), CalibSet 유일 소재.
- **[Medium] BM3D 자체 구현 정확도·규모** — 순수 numpy/scipy 골든 구현은 대규모이고 원저 파라미터 재현 정확도가 관건(래핑 대비 검증 부담 증가). 완화: 원저 파라미터 [L] 특성화, 합성 기지 노이즈로 SNR/MTF 검증, 속도 최적화 금지(P1 정확도 단일 목표)로 구현 단순화, 라이선스 리스크 원천 제거(감사 가능).
- **[Medium] 스테이지 배치 T0 표면 변경** — `CANONICAL_ORDER`·`_KIND_BY_STAGE` 신설이 하류 SPEC 회귀. 완화: 결정 1 확정(기하와 post 사이 전용 `denoise`), 등록 stages = `CANONICAL_ORDER` 부분수열 검증으로 하위호환 유지.
- **[Low] 실측 [B] 데이터 부재** — (α,σ)·선량 절감률 실측 대기. 완화: 합성 기지 데이터 선검증(빌더·모듈 형상 동결), 실측 도착 후 [B] 치환은 게이트 아님(부록 A 정책).

## 검증 전략

- 모든 판정은 `tests/`에서 모듈 + T1 지표 엔진(SNR/MTF/NPS)·기지 λ 대조로 수행(모듈은 `metrics` 미import — CONTRACT-3).
- EV 임계·`ε_unbias`는 외부 주입(측정=판정 분리). 처리·판정 코드에 임계 내장 금지.
- harness 단독 시험(합성 입력 + 기대 출력 fixture)으로 모듈 격리 검증(XDET-TC-000 계승).
