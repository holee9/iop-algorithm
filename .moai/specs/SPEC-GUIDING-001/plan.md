---
id: SPEC-GUIDING-001
title: 정본 지침(guiding) 취득세트 요구사항 — P1 수치 golden 검증 blocker 해제
version: 0.1.0
status: draft
created: 2026-07-11
updated: 2026-07-11
author: drake.lee
priority: high
issue_number: 33
---

# SPEC-GUIDING-001 취득 계획 (초안) — 정본 지침 취득세트

> 상태: **draft**. EARS 확정본은 [spec.md](./spec.md), 인수 기준은 [acceptance.md](./acceptance.md). 연관 SPEC은 [SPEC-REALDATA-001](../SPEC-REALDATA-001/spec.md)(#29 격리) · [SPEC-DQEDOC-001](../SPEC-DQEDOC-001/spec.md)(#38 DQE 형태).

## 1. 개요

SPEC-REALDATA-001 플러밍 검증 결과, 샘플 세트(`images/에드로지16BIT/`)로는 P1 수치 골든 검증(EV 기준)이 사실상 불가함이 확정되었다(전 항목 MISSING/PARTIAL, DQE 3입력 온전 공급 0개). 본 SPEC은 정본 "지침(guiding)" 취득세트가 **무엇을 어떤 조건으로** 취득해야 P1 DoD(EV-101~106/201~205/301~303, XDET-TC-001~019 수치 판정)를 unblock하는지 EARS로 명세한다. **본 SPEC은 소프트웨어 구현이 아니다** — 코드·모듈·파이프라인 스테이지·CalibKind·`process()` 시그니처를 추가하지 않으며, 물리 취득의 요구·조건·매수·추적성만 정의한다. 수치 확정·튜닝은 세트 도착 후 **별도 SPEC** 소관.

## 2. 취득 우선순위 계획 (A→B→C→D, 시간 추정 없음)

이슈 #33의 우선순위를 그대로 채택한다. 레버리지 순으로 A티어 전제를 먼저 확립하고, 최고 레버리지 2종을 취득해 대부분의 수치 아암을 활성화한 뒤, B/C/D 확장 항목을 순차 취득한다.

| 우선순위 | 취득 | unblock (TC/EV) | 대응 REQ |
|---|---|---|---|
| **A (전제)** | RQA5 확립(Al 21mm type-1100, HVL 실측 kV, SID≥1.5m) + 교정 이온챔버 Ka 실측 + XN 3점 선량 + offset/gain 전·후 | 전 항목의 전제 | BASELINE-1~7 |
| **A (레버리지 1)** | flat-field 선량 계단 6~8단계 × 단계당 ≥10매 + 단계별 선량 실측치 | XDET-TC-001/011, EV-101 (gain 다점 · NPS · DQE 분모 · 선형성 · 노이즈모델 α,σ) | LEVERAGE-1/4, DQE-2, COVERAGE-4 |
| **A (레버리지 2)** | 슬랜티드 엣지 W 2mm 후판, 수평·수직, 1.5~3° 미세경사, 방향·선량당 ≥5매 | XDET-TC-002, EV-102 (MTF · SRb · DQE 분자) | LEVERAGE-2/3, DQE-1 |
| **B** | 비포화 다중노출 lag step-response(2~90% 범위, 프레임 간격 기록, ≥5회, 노출/잔상 쌍) | XDET-TC-004, EV-104 | LAG-1/2/3/5 |
| **B** | ghost 시간계단(납판 반차폐 강노출 → 균일 조사 직후/1분/5분) | XDET-TC-005, EV-104 | LAG-4 |
| **B** | dark/flat 대량 스택(dark ≥50 · flat ≥50; offset은 온도3×시점4×≥20) | XDET-TC-003, EV-101/103 | COVERAGE-1/2 |
| **B** | 전용 저선량 line noise 세트(XN/8~XN/4, ≥20매) | XDET-TC-006, EV-105 | COVERAGE-3 |
| **C** | duplex wire + 단선 IQI + 용접시편(kV·노출 3점×5매 + 적산 연속 프레임) | XDET-TC-018, EV-301 | COVERAGE-5 |
| **C** | E2597 6단 step wedge(강/알루미늄) + 두께 경사 시편 | XDET-TC-019, EV-303 | COVERAGE-6 |
| **C** | grid 매트릭스(밀도 3부류 aliased 포함, grid당 ≥5매) | XDET-TC-015/016, EV-203 | COVERAGE-7 |
| **C** | scatter 팬텀(아크릴/물 두께 계단, grid 유/무 쌍) | XDET-TC-017, EV-202 | COVERAGE-8 |
| **C** | 구조물/포화구도/기하 팬텀(금속 3배치×5 / 경계 3×5 / 격자 3위치×3 + 실측 치수) | XDET-TC-007/008/009, EV-105/106 | COVERAGE-9 |
| **D** | 임상 모사 + CDRAD(부위별 다구도 ≥10, 표준 + 저선량 계단) | XDET-TC-010/012/013, EV-205 | COVERAGE-10 |

## 3. 등록·추적성 (산출물)

- **매니페스트 등록**: 정본 세트는 SPEC-REALDATA-001 매니페스트 규약에 따라 전 엔트리 `usage="guiding"`로 등록되어 샘플 세트(`usage="sample-plumbing"`)와 구분된다(TRACE-2).
- **RTM 매핑**: 각 취득 요구가 unblock하는 TC/EV(XDET-TC-001~019, EV-101~106/201~205/301~303)를 RTM 경유로 매핑한다(TRACE-1).
- **BLOCKER 상태**: 세트 도착 전까지 수치 검증은 합성 팬텀 경로로만 유효(수치 골든 BLOCKER 유지); 도착·등록 시 unblock 조건 충족 기록(TRACE-3/4). 수치 확정·튜닝은 별도 SPEC(TRACE-5).

## 4. 리스크 분석 (요약)

| 리스크 | 완화 | 우선순위 |
|---|---|---|
| 샘플 세트 수치로 파라미터 튜닝·EV 임계 조정 유입 | TRACE-5 [HARD] 격리 연장; 본 SPEC은 취득 요구만; 수치 작업은 별도 SPEC | High |
| flat 계단 선량 실측치 누락(라벨-only) → 선형성/DQE 분모/α,σ 회귀 불가 | LEVERAGE-4 거부; 단계별 선량 실측 필수(샘플 acrylic_step 축 불정합 반복 금지) | High |
| lag 포화·단일노출 취득 → IRF 불가 | LAG-2 거부(SWR-401); 비포화 2~90% 복수노출 + 노출/잔상 쌍(#32) | High |
| DQE Ka 미실측 → 절대값 불가 | BASELINE-3 + DQE-3 교정 이온챔버 실측 필수 | High |
| NPS 매수 미달(3매) → 저주파 편향 | DQE-2 선량점당 ≥16매 앙상블 | Medium |
| grid aliased 부류 누락 → 억제 검증 불완전 | COVERAGE-7 밀도 3부류(aliased 필수) | Medium |
| 무-코드 범위에서 소프트웨어 산출물 유입 | Exclusions [HARD] 무-코드; 검증은 매니페스트 체크리스트 대조 | Medium |

## 5. 마일스톤 (우선순위 기반, 시간 추정 없음)

- **Priority High — M1 A티어 전제 확립**: RQA5 + HVL 실측 kV + 교정 Ka + XN 3점 선량 + offset/gain 전·후 요구 확정·문서화. 다른 모든 취득의 전제.
- **Priority High — M2 최고 레버리지 2종**: flat 선량 계단 + 슬랜티드 엣지 취득 요구 확정 → MTF·NPS·DQE·gain·선형성·노이즈모델 아암 활성화 조건 정의. M1 확립 후.
- **Priority Medium — M3 B티어 확장**: lag/ghost 구조 제약(#32) + dark/flat 스택 + line noise 저선량 세트 요구 확정.
- **Priority Medium — M4 C티어 확장**: NDT IQI/wire/용접 + step wedge + grid 매트릭스 + scatter + 구조물/포화/기하 팬텀 요구 확정.
- **Priority Low — M5 D티어 + 추적성 마감**: 임상 모사 + CDRAD 요구 확정; `usage="guiding"` 등록 + RTM TC/EV 매핑 완료; BLOCKER 해제 기록 체계 확정.
- 순서 원칙: M1(A티어 전제) 확립 후 M2 착수 → M3~M5 순차. 레버리지 2종·A티어는 고정, B/C/D 내 순서는 실험 자원에 따라 조정 가능(spec.md 「결정 필요/확인 사항」 3).

## 6. 검증 전략 — 관측 가능 판정 (무-코드)

- **매니페스트 체크리스트 대조**(acceptance.md): 후보 세트 도착 시 각 항목을 요구 매수·조건에 대조하여 SUPPLIED/MISSING으로 판정.
- **거부 케이스 관측**: 포화 프레임(EC-1) · Ka 미실측(EC-2) · 매수 미달(EC-3) · 격리 위반(EC-4)이 매니페스트 대조로 관측 가능.
- **격리 준수**: 파라미터 유도·수치 피팅·EV 임계 조정이 본 SPEC 범위 내에 없음(TRACE-5).
- **DoD**: A티어 + 레버리지 2종 SUPPLIED 시 핵심 수치 아암 활성화; MISSING 항목 순차 취득으로 EV 전 범위 판정 가능화; `usage="guiding"` 등록 + RTM 매핑.

## 7. DoD (Definition of Done)

- [ ] A티어 전제(RQA5 + HVL 실측 kV + 교정 Ka + XN 3점 + offset/gain 전·후) 요구 확정 (BASELINE-1~7)
- [ ] 최고 레버리지 2종(flat 선량 계단 · 슬랜티드 엣지) 요구 확정 → 핵심 아암 활성화 조건 (LEVERAGE-1~4)
- [ ] DQE 3입력(MTF · NPS ≥16매×3선량점 · 교정 Ka) 온전 공급 요구 확정 (DQE-1~4)
- [ ] lag/ghost 구조 제약(비포화 2~90% · 노출/잔상 쌍 · ghost 직후/1분/5분) 요구 확정 (LAG-1~5, #32)
- [ ] 잔여 MISSING/PARTIAL 10항목 정본 취득 요구 확정 → EV-101~106/201~205/301~303 가능화 (COVERAGE-1~11)
- [ ] `usage="guiding"` 등록 규약 + RTM 경유 TC/EV 매핑 정의 (TRACE-1~4)
- [ ] 매니페스트 체크리스트로 SUPPLIED/MISSING 관측 가능 + 거부 케이스(포화/Ka미실측/매수미달/격리위반) 관측 가능
- [ ] **소프트웨어 산출물 없음 · 수치 확정·튜닝·EV 임계 조정은 별도 SPEC(격리 연장) — DoD** (TRACE-5, Exclusions)
