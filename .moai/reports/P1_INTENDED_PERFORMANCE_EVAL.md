# P1 최종 e2e 성능 평가 — 합성 팬텀 기지값 재현으로 본 의도 성능 (전체 계획대비)

- 평가일: 2026-07-11
- 이슈: #44
- 근거 하네스: [`scripts/eval_intended_performance.py`](../../scripts/eval_intended_performance.py) (`uv run python scripts/eval_intended_performance.py`, 결정론적·재실행 가능)
- 범위: **합성 팬텀 전용** — 실측(`images/에드로지16BIT`)은 참조하지 않음(SPEC-REALDATA-001 QUARANTINE 준수)

## 0. 평가 원칙 — 단순 동작이 아닌 의도 성능

본 평가는 "543 passed"(pass/fail)를 넘어, 각 지표가 **주입된 기지 물리값을 얼마나 정확히 재현하는가**(target vs achieved vs 선언된 [T] 허용오차 vs 마진)를 측정한다. 하네스는 프로젝트의 기존 합성 팬텀 생성기와 **실제 지표 엔진**을 pytest 스위트와 동일하게 배선하여, 물리를 재발명하지 않고 재현 정확도를 산출한다.

- MARGIN = 경계오차 / 선언 허용오차 (%). PASS ≤75% · MARGINAL 75–100% · FAIL >75% 초과.

## 1. 의도-성능 결과 — 골든 재현 (검증됨)

| 지표 | ID | 목표(기지값) | 실측 재현 | 상대오차 | [T] 허용 | 마진 | 판정 |
|---|---|---|---|---|---|---|---|
| MTF 곡선 (edge σ=0.6px) | MTF/Scen2 | 해석적 MTF(f) | max\|Δ\|=0.0040 | – | 0.02(abs) | 20% | PASS |
| MTF@Nyquist (3.57 lp/mm) | MTF@Nyq | 0.1692 | 0.1648 | 2.6% | 0.06(abs) | 7% | PASS |
| NPS flat level | NPS/Scen3 | 49 | 48.82 | 0.36% | 0.15(rel) | 2% | PASS |
| NNPS flat level | NNPS/Scen3 | 1.225e-05 | 1.221e-05 | 0.36% | 0.15(rel) | 2% | PASS |
| **DQE mid-band (이상 Poisson)** | DQE/Scen3 | 1.0 | **1.0033** | 0.33% | 0.10(abs) | 3% | PASS |
| DQE 선량 불변 \|1x−2x\| | DQE 1x/2x | 0 | 0.0027 | – | 0.10(abs) | 3% | PASS |
| First-frame lag % | LAG/Scen5 | 2.537 | 2.537 | 2e-7% | 1e-06(rel) | 20% | PASS |
| Ghost CNR (Δ/σ) | Ghost/Scen8 | 5 | 4.925 | 1.5% | 0.20(rel) | 7% | PASS |
| IRF 피팅 재구성 | LAG-IRF/Scen6 | 기지 afterglow | max\|Δ\|=1.0e-5 | – | 1e-04(abs) | 10% | PASS |
| Bad-pixel E2597 miss-rate | Defect/Scen6 | 0 (7/7 분류) | 0 | – | 0(abs) | 0% | PASS |
| Duplex-wire SRb | SRb/Scen7 | 130 µm | 130 | 0 | 1e-09 | 0% | PASS |
| SNRn = SNR·88.6/SRb | SNRn/Scen7 | 68.15 | 66.80 | 2.0% | 0.10(rel) | 20% | PASS |
| Single-wire IQI 최소가시선 | IQI-wire | 13 | 13 | 0 | 0 | 0% | PASS |
| Welford online == batch | Welford | batch 기준 | max\|Δ\|=6.8e-13 | – | 1e-06 | 0% | PASS |
| Streaming SNRn √k 진행 | SNRn-stream | (mean/σ)√k | max rel=0.0088 | 0.88% | 0.15(rel) | 6% | PASS |
| 노이즈모델 α | Noise-a/Scen10 | 2 | 1.998 | 0.11% | 0.10(rel) | 1% | PASS |
| 노이즈모델 σ | Noise-s/Scen10 | 3 | 2.864 | 4.5% | 0.15(rel) | 30% | PASS |
| VST 왕복 무편향 | VST-RT/TC-011 | λ(1..200) | max bias=0.0030 | – | 0.06(abs) | 5% | PASS |
| **Virtual-grid scatter Ŝ** | Scatter/TC-017 | 주입 S_inj | **rel L2=0.216** | 21.6% | 0.25(rel) | **86%** | **MARGINAL** |
| Grid 주파수 [below] | Grid/TC-015 | 2.511 | 2.511 | 0 | 0.12(abs) | 0% | PASS |
| Grid 주파수 [near] | Grid/TC-015 | 3.404 | 3.404 | 0 | 0.12(abs) | 0% | PASS |
| Grid 주파수 [aliased] | Grid/TC-015 | 2.121 | 2.121 | ~0 | 0.12(abs) | 0% | PASS |
| GSDF PS3.14 per-JND | GSDF/TC-014 | 0 | 5.3e-8 | – | 0.005(abs) | 0% | PASS |

**골든 23지표: 23/23 허용오차 내 (PASS 22 · MARGINAL 1 · FAIL 0).**

## 2. 의도-성능 결과 — EV 게이트 (외부 최소 바 통과)

이 지표들은 기지값 재현이 아니라 **외부 설정 최소 성능 바**(개선율·잔차 임계) 통과 여부로 판정한다.

| EV 지표 | ID | 실측 | 바 | 방향 | 결과 |
|---|---|---|---|---|---|
| Denoise SNR 개선 (BM3D) | EV-201/TC-010 | 7.503 (14.27→121.31) | 0.20 | ≥ | CLEARS |
| Grid MTF@Nyq 유지 | EV-102/TC-015 | 1.000 | 0.90 | ≥ | CLEARS |
| Grid 잔차 피크 유의성 | residual_db/TC-015 | 0 (잔차 없음) | 6 | ≤ | CLEARS |
| MSE-DRC 국소대비 이득 | local_contrast/TC-012 | 1.118 | 1.0 | ≥ | CLEARS |
| MSE-DRC 디테일에너지 유지 | detail_energy/TC-012 | 1.639 | 0.5 | ≥ | CLEARS |
| Virtual-grid CNR 개선 | EV-202/TC-017 | 0.574 (5.93→9.34) | 0.20 | ≥ | CLEARS |
| 기하 잔차 (보정 후) | EV-106/Scen9a | 0.0022px (2.903→0.002) | 1.0 | ≤ | CLEARS |

**EV 7지표: 7/7 통과.**

## 3. 전체 계획대비 커버리지 (CLAUDE.md T0–T10 / TC-000~021 / SPEC)

| WP/스테이지 | SPEC | 의도-성능 검증 상태 |
|---|---|---|
| T0 프레임워크 | INFRA-001 | 계약·의존검사·CI 구조 완성 (lint-imports 7 kept 0 broken) |
| T1 지표엔진 | METRICS-001 | MTF·NPS/NNPS·DQE·lag·IRF·defect·SNRn/IQI 골든 재현 ✓ |
| T2 WP1 보정 | CORR-001 | offset/gain/defect — E2597 7분류 miss-rate 0 ✓ |
| T3 WP3+4 라인/포화/기하 | LNSG-001 | 라인노이즈·포화·기하 잔차 EV 통과 ✓ |
| T4 WP2 lag | LAG-001 | first-frame lag·ghost CNR·IRF 골든 재현 ✓ |
| T5 WP5 VST+BM3D | DENOISE-001 | VST 왕복 무편향·denoise SNR 개선 ✓ |
| T6 WP6+7 MSE/DRC/GSDF | POST-001 | MSE-DRC·GSDF PS3.14 적합성 ✓ |
| T7 WP8 grid 억제 | GRID-001 | 관측 주파수 검출 exact·잔차 억제 ✓ |
| T8 WP9 virtual grid | VGRID-001 | scatter 추정(MARGINAL 86%)·CNR 개선 ✓ |
| T9 WP10 NDT | NDT-001 | SNRn·duplex SRb·IQI·두께보정·Welford 적산 ✓ |
| T10 티어/동일성 | TIER-001 | TC-020/021 **구조** 통과 — 절대 수치 판정은 설계상 P2 이연 |
| 측정프로토콜 정정 | DQEDOC-001 | §1.4 DQE IEC 무차원 정정 (본 세션) ✓ |
| 실측 취득 요구 | GUIDING-001 | 정본 지침 세트 취득 요구 정식화 — 실측 수치 golden **blocked** |

- 코어 스위트: **543 passed** (`uv run pytest --ignore=tests/apps`, 0 실패·0 skip)
- 캡스톤: `tests/test_tc_skeletons.py`가 전 22개 TC ID 실동작 존재 강제 검증

## 4. 정직한 범위 — 검증된 것 vs 이연/blocked

- **검증됨 (합성 골든)**: §1–2의 23 골든 + 7 EV 지표. P1 골든모델은 "이론적으로 정확"을 넘어 **합성 기지값을 선언된 허용오차 내로 재현하는 검증된 정확**을 달성했다.
- **MARGINAL 1건 (정직 표기)**: virtual-grid scatter Ŝ가 허용오차 예산의 86%(rel L2 0.216 vs 0.25)를 소모 — SKS 다운/업샘플 추정의 고유 오차. 통과하나 골든 재현 중 최저 정확도이며, 실측 커널 도착 시 재평가 대상.
- **설계상 P2 이연**: TC-020/021 절대 수치(티어별 시간·bit-동일성)는 SPEC 설계 단계부터 P2 명시 이연. "형상 동결"은 골든모델 코드 동결을 의미하며 하드웨어 티어별 실측 성능 확정은 아니다.
- **실측 blocked**: 실제 패널 하드웨어 기반 **수치 golden 검증**은 정본 지침(guiding) 취득세트 부재로 blocked — SPEC-GUIDING-001(#33)로 요구가 정식화됨. 현 샘플셋은 QUARANTINE(플러밍/sanity 전용). LAG IRF 계수·VGRID SKS 커널 등 TBD-[B]는 세트 도착 후 별도 SPEC에서 확정.
- **정책 이연**: 특허 검토(⚠P 6개소+)는 릴리스 게이트로 이연 — P1 범위 밖.

## 5. 종합 판정

P1 골든모델은 **P1 범위 내에서 의도된 성능을 충족한다** — 전 골든 지표가 선언된 [T] 허용오차 내로 기지 물리값을 재현하고(대부분 허용오차의 수% 이내, 다수는 exact), 전 EV 지표가 최소 성능 바를 통과한다. 계획(T0–T10 WP·TC-000~021·SPEC DoD)대비 구현은 합성 검증 경로에서 완결되었고, 남은 것은 **P1 범위 밖의 명시적 이연 항목**(실측 수치 golden = SPEC-GUIDING-001 대기, TC-020/021 절대 수치 = P2, 특허 = 릴리스 게이트)뿐이다.

즉, **"계획대비 구현"은 P1 골든모델의 의도 성능을 달성했으며, "검증된 정확"의 경계는 정직하게 합성 팬텀까지이고 실측 확정은 정본 지침 세트 취득이라는 물리적 선행조건에 걸려 있다.**
