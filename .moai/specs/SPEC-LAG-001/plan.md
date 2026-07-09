---
id: SPEC-LAG-001
title: T4 WP2 lag 보정 처리 모듈 (지수합 상태변수 재귀 · IRF 피팅 도구 · 상태 직렬화 CONTRACT-2 런타임 검증)
version: 0.1.1
status: draft
created: 2026-07-09
updated: 2026-07-09
author: drake.lee
priority: high
issue_number: 5
---

# SPEC-LAG-001 구현 계획 (초안) — T4 WP2 lag 보정 처리 모듈

> 상태: **draft** (run 단계 착수 전까지 유지). EARS 확정본은 [spec.md](./spec.md), 인수 기준은 [acceptance.md](./acceptance.md). 선행 계약은 [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md)(프레임워크·CONTRACT-2·`StatefulModule`)·[SPEC-METRICS-001](../SPEC-METRICS-001/spec.md)(lag 판정 엔진 `metrics/lag`)·[SPEC-CORR-001](../SPEC-CORR-001/spec.md)(선행 보정 모듈·offset 포화 검출·`metrics/` 빌더 선례)·[SPEC-LNSG-001](../SPEC-LNSG-001/spec.md)(`modules/` 처리 패턴·부분 게이트 선례).

## 1. 개요

XDET P1의 다섯 번째 작업 T4(WP2). lag(잔상) 보정 모듈 `modules/lag.py`를 T0 계약 `process(XFrame, CalibSet, Params) -> XFrame`으로 구현하되 **SWR-000-7 명시 예외인 내부 상태 보유 모듈**로 둔다. 지수합 IRF h[n] = Σᵢ aᵢ·bᵢⁿ(M=3~4, [L]) 기반 상태변수 재귀(SWR-401~402)를 수행하고, 프레임당 지수항 상태 {sᵢ}를 연속 촬영 순서로 유지한다. lag은 `CANONICAL_ORDER`의 `lag` 위치(defect 이후·line_noise 이전)에서 실행된다. IRF 계수(aᵢ, bᵢ, M)는 실측 대기 [B]이므로 CalibSet(LAG)로 외부화하고, **기지 지수합 IRF를 주입한 합성 데이터로 보정 엔진·IRF 피팅 도구를 선검증**한다(CLAUDE.md T4). 본 SPEC은 T0가 구조적으로만 확인한 **상태 직렬화 인터페이스(CONTRACT-2 — `serialize_state`/`load_state` ↔ XFrame)의 첫 런타임 검증**을 담당한다. 완료 정의: first-frame lag % 개선(`metrics/lag.compute_first_frame_lag`) + ghost CNR 감소(`compute_ghost_cnr`) + 상태 직렬화 왕복 바이트 재현 + XDET-TC-004(EV-104 min 게이트)·XDET-TC-005(부분 게이트 — ghost CNR 감소; ghost 종단 비가시는 FB/실 패널 통합 후) skeleton→live 전환.

## 2. 기술 스택

| 항목 | 선택 | 근거 |
|---|---|---|
| 언어/런타임 | Python 3.11+ | tech.md |
| 수치 연산 | numpy, scipy (float 골든 모델; IRF 피팅에 `scipy.optimize`) | tech.md, CLAUDE.md 아키텍처 |
| 시험 프레임워크 | pytest + CI (XDET-TC-004~005 실동작 전환) | TestSpec, SWR-000-11 |
| 처리 계약 | `process(XFrame, CalibSet, Params) -> XFrame` + 내부 상태(SWR-000-7 예외) | SPEC-INFRA-001 REQ-INFRA-CONTRACT-1/2 |
| 상태 직렬화 | `StatefulModule` 프로토콜 `serialize_state()->XFrame`/`load_state(XFrame)->None` | `common/contract.py`, REQ-INFRA-CONTRACT-2 |
| 조합 계약 | 오케스트레이터 registry 등록(`lag` 스테이지) + 신규 additive 시퀀스 러너 `pipeline/sequence.py`(결정 1) | SPEC-INFRA-001 REQ-INFRA-ORCH-1/3 |
| 진입 게이트 | CalibSet 존재·해상도·패널 ID·유효기간; `lag→LAG` 종류-단계 배선 | `pipeline/orchestrator.py` `_calibration_gate`·`_KIND_BY_STAGE` |
| 공용 컴포넌트 | `common/robust_stats`(피팅 강건성)·`common/mask_ops`(마스크 소비) 참조(중복 금지) | SWR-000-9, REQ-INFRA-STATIC-3 |
| 정적 검사 | import-linter 레이어 `module → common` 단방향 | SPEC-INFRA-001 REQ-INFRA-STATIC |
| 판정 소비 | `metrics/lag.compute_first_frame_lag`·`compute_ghost_cnr`(tests/에서만) | SPEC-METRICS-001 REQ-METRICS-LAG-1/2/5 |
| 파라미터 | IRF 계수(aᵢ,bᵢ,M)=CalibSet(LAG) [B]; lag 모듈 [T]/[P] 튜닝 없음 | CLAUDE.md 파라미터 정책, SWR 부록 A |

원칙: **정확도 단일 목표, 속도 최적화 금지.** 하드코딩 금지 — IRF 계수 CalibSet 주입. EV 판정 수치 미내장(측정=판정 분리).

## 3. 모듈 분해 (레이아웃)

```
modules/
  lag.py         # SWR-401~404: 지수합 IRF 상태변수 재귀 sᵢ[k]=bᵢ·(sᵢ[k−1]+aᵢ·Î[k−1]),
                 #   Î[k]=I[k]−Σsᵢ[k]; 내부 상태 {sᵢ}((M,ny,nx) float32 상태면) 보유(SWR-000-7 예외);
                 #   serialize_state()->XFrame / load_state(XFrame)->None (CONTRACT-2, float32 고정);
                 #   SATURATION 화소 출력 값 보존·재귀는 계산값 진행(REQ-LAG-CORR-5, 결정 6/D7);
                 #   전용 ghost 감쇠 없음(SWR-404)
pipeline/
  sequence.py    # (결정 1) 신규 additive 시퀀스 러너: 프레임별 run_pipeline 래핑,
                 #   lag 인스턴스 시퀀스 수명 재사용(시퀀스 개시=신규화=리셋 sᵢ[−1]=0, STATE-4/5),
                 #   FB 트리거(요청/완료 스텁, SWR-404) 호출(결정 4);
                 #   run_pipeline·CANONICAL_ORDER·진입 게이트·CONTRACT-1 표면 불변(T0 표면 변경 없음)
metrics/
  lag_irf.py     # (결정 5) 오프라인 IRF 피팅 빌더: 복수 노출 step-response → 지수합 계수(aᵢ,bᵢ,M)
                 #   피팅 → CalibSet(kind=LAG) emit; 단일 노출 입력 거부(SWR-401); metrics→common
```

- `metrics/lag.py`(first-frame lag %·ghost CNR 산출)는 **T1(SPEC-METRICS-001) 기존 구현**이며 본 SPEC은 재구현하지 않고 `tests/`에서 소비만 한다.
- IRF 피팅 빌더는 캘리브레이션 아티팩트(CalibSet(LAG))를 생성하는 오프라인 도구로, `metrics/defect_map.py`(defect map 빌더) 선례를 따라 `metrics/`에 둔다. 처리 모듈의 `metrics` import 금지는 `modules/`만 관장하므로(SPEC-CORR-001 선례) 빌더가 `metrics/`에 있어도 레이어링 위반이 아니다. 배치 최종 확정은 spec 「결정 필요/확인 사항」 5.
- 진단 부산물(포화 화소 보존 카운트·경고 등)은 XFrame 컨테이너 외 사이드채널 금지(SWR-000-6)에 따라 스칼라로 이력 체인 엔트리 메타(`HistoryEntry.extra`)에 기록한다.
- 합성 IRF 시퀀스 생성기(기지 계수 주입)는 **`tests/` 전용 fixture**로 둔다(SPEC-INFRA/METRICS/CORR/LNSG tests/ 전용 결정 계승). `tests/modules/phantoms/`(또는 `tests/lag/`)에 시퀀스 생성기(기지값 동반)를 배치하고 `modules/`는 순수 처리만 유지한다.

## 4. EARS 구조 설계 (확정본은 spec.md)

5개 요구 그룹. `[Ubiquitous]`/`[Event]`/`[State]`/`[Unwanted]`는 EARS 패턴 표기. **Optional(WHERE) 요구는 없다** — 모든 요구는 필수 또는 Exclusions로 처리(조건부 AC 페어링 불필요).

- **REQ-LAG-CORR** — 지수합 IRF·LTI 경로(`[Ubiquitous]`, CORR-1), 상태변수 재귀 공식(`[Event]`, CORR-2), FB 트리거 인터페이스(`[Event]`, CORR-3), 전용 ghost 감쇠 금지(`[Unwanted]`, CORR-4), 포화 화소 값 보존·재귀 계산값(`[Unwanted]`, CORR-5 — D1/결정 6).
- **REQ-LAG-STATE** — 내부 상태 보유(`[Ubiquitous]`, STATE-1), serialize/load XFrame 왕복(`[Event]`, STATE-2), 결정론(`[Ubiquitous]`, STATE-3), 시퀀스 간 리셋(`[Event]`, STATE-4), 프레임 간 threading(`[Event]`, STATE-5 — 구동은 `pipeline/sequence.py` 러너, 결정 1 확정).
- **REQ-LAG-IRF** — 복수 노출 피팅 → CalibSet(LAG)(`[Event]`, IRF-1), 단일 노출 거부(`[Unwanted]`, IRF-2), 합성 IRF 선검증(`[State]`, IRF-3).
- **REQ-LAG-CONTRACT** — process 시그니처·불변·상태 예외(`[Ubiquitous]`), 이력 체인(`[Event]`), 의존 방향(`[Ubiquitous]`), CalibSet 게이트 거부(`[Unwanted]`), 사이드채널 금지 한정+상태 예외 구분(`[Unwanted]`), 고정 순서·harness 확장(`[Ubiquitous]`).
- **REQ-LAG-VALIDATE** — 합성 검증(`[State]`), first-frame lag % 개선(`[Event]`, VALIDATE-2), ghost CNR 감소 부분 게이트(`[Event]`, VALIDATE-3), 상태 직렬화 왕복 재현 = CONTRACT-2 첫 런타임 검증(`[Event]`, VALIDATE-4), EV 외부 주입(`[Ubiquitous]`), TC skeleton→live(`[Ubiquitous]`).

## 5. CalibSet fixture 전략

`common.calibset.CalibSet` 공통 스키마(panel_id · resolution · valid_from/until · kind · data · provenance)를 사용한다. 게이트가 존재·해상도·패널 ID·유효기간을 검사하고, lag 단계는 추가로 종류-단계 배선(kind=LAG)을 검사한다.

| 스테이지 | CalibSet(kind) data 페이로드 | 무효 fixture(부정 경로) |
|---|---|---|
| lag | kind=LAG; 지수합 IRF 계수 {aᵢ, bᵢ} (i=1..M), 차수 M(3~4) — 합성 검증에서는 기지 주입 계수 | 해상도 불일치 · kind≠LAG · 패널 ID 불일치 · 유효기간 밖 · CalibSet 부재 |

- IRF 계수는 [B](2-1 실측 대기)이며 합성 검증에서는 기지 계수를 주입한 CalibSet(LAG)를 사용한다. 무단 기본값 대체 금지 — CalibSet 부재 시 게이트가 거부한다(REQ-LAG-CONTRACT-4, offset `raw_saturation_threshold` 선례).
- IRF 피팅 빌더(`metrics/lag_irf.py`)는 복수 노출 step-response로부터 이 CalibSet(LAG)를 산출한다. 합성 검증에서는 기지 IRF로 생성한 계단 응답을 빌더에 입력해 주입 계수 복원(REQ-LAG-IRF-3)을 확인하고, 그 CalibSet를 보정 엔진에 주입하는 왕복을 검증한다.

## 6. 합성 시퀀스 전략 (기지 IRF 주입 → 억제·판정)

| 시나리오 | 합성 시퀀스(기지 IRF 주입) | 처리 후 검증(기지값·판정 엔진) |
|---|---|---|
| first-frame lag | 포화 근접 노출 플래토 → X선 차단 → 잔상 감쇠 프레임열(기지 IRF로 생성) | `metrics/lag.compute_first_frame_lag`로 보정 전/후 first-frame lag %; 보정 후 ≤ EV-104 min(≤5%) 및 보정 전 대비 개선(XDET-TC-004, 기지 IRF 해석 잔존 = ground truth) |
| ghost | 고대비 패턴 프레임 → 균일 조사 프레임(패턴 잔상이 기지 IRF로 이월) | `metrics/lag.compute_ghost_cnr`로 보정 전/후 잔상 CNR; 보정 후 감소(XDET-TC-005 T4 부분 게이트; SWR-402 부산물 감소) |
| 상태 직렬화 왕복 | 임의 연속 시퀀스; 중간 프레임에서 `serialize_state`→`load_state`(새 인스턴스) | 왕복 후 이어 처리 출력·최종 상태가 무중단 처리와 바이트 동일(CONTRACT-2 런타임 검증, VALIDATE-4) |
| IRF 피팅 | 기지 IRF로 생성한 복수 노출 step-response | 빌더가 주입 계수를 허용오차 내로 복원, CalibSet(LAG) emit; 단일 노출 입력은 거부(IRF-2) |

원칙: 시퀀스 생성기는 `tests/` 전용에 두고 기지값(IRF 계수·플래토 인덱스·패턴 좌표)을 함께 반환. 허용오차·EV 임계는 외부 주입(하드코딩 금지). lag 판정은 `tests/`에서 `metrics/lag`를 소비(모듈은 metrics import 금지 — CONTRACT-3).

## 7. 파이프라인 통합 + 시퀀스 구동 (결정 1)

- lag 모듈의 `process`를 오케스트레이터 registry에 `"lag"` 스테이지로 등록한다(`pipeline/orchestrator.run_pipeline(registry=...)`). `PipelineDefinition(stages=(…,"lag",…))`는 `CANONICAL_ORDER` 부분수열이므로 순서 계약을 만족한다(REQ-LAG-CONTRACT-6).
- 진입 게이트는 lag 스테이지 CalibSet의 존재·해상도·패널 ID·유효기간·종류-단계 배선(kind=LAG)을 검사한다(REQ-LAG-CONTRACT-4).
- **시퀀스 구동(결정 1 확정)**: `run_pipeline`은 단일 프레임을 처리하므로, 연속 촬영 시퀀스 구동은 신규 additive 시퀀스 러너 `pipeline/sequence.py`가 담당한다 — 프레임별 `run_pipeline`을 래핑하고 상태 보유 lag 인스턴스를 시퀀스 수명 동안 재사용하며(프레임 k 최종 상태 → k+1 초기 상태), 시퀀스 개시 시 인스턴스 신규화 = 리셋(별도 리셋 프로토콜 메서드 없음), FB 트리거는 러너가 호출한다(결정 4). `run_pipeline`·`CANONICAL_ORDER`·진입 게이트·REQ-LAG-CONTRACT-1 표면은 불변(additive, T0 표면 변경 없음)이고, 구동 경로는 `pipeline/`(프로덕션)에 두며 `tests/`가 아니다.
- 검증 모드(validation_mode) 활성 시 단계별 중간 XFrame이 보존되나(REQ-INFRA-DATA-5), lag 상태 threading은 시퀀스 축(프레임 간)이므로 검증 모드의 단일 프레임 스테이지 보존과는 별개다.

## 8. 리스크 분석 (요약)

| 리스크 | 완화 | 우선순위 |
|---|---|---|
| 시퀀스 상태 threading 구동 위치(단일 프레임 계약 vs 시퀀스 연산) | **결정 1 확정** — 신규 additive `pipeline/sequence.py` 러너(run_pipeline 래핑, 인스턴스 수명=시퀀스 수명 리셋, T0 표면 불변) | Resolved |
| CONTRACT-2 상태 XFrame 패킹(M개 상태면 vs 단일 pixel 배열) | **결정 2 확정** — (M,ny,nx) float32 pixel+zeros 마스크(XFrame ndim 제약 없음), dtype 고정으로 왕복 바이트 동일 | Resolved |
| harness 단일 호출 순수함수 가정 vs 상태 보유 모듈 | harness fixture 확장(load/serialize 상태 대조), 결정 3 확인 | High |
| 포화 화소에 상태 감산 시 포화점 아래 값 생성(SWR-602 복원 금지 취지 위반) | **결정 6 확정** — 출력 값 보존(REQ-LAG-CORR-5) + 재귀는 계산값 Î[k−1] 진행(D7) | Resolved |
| IRF 계수 하드코딩 유입([B]) | CalibSet(LAG) 주입 필수화, 게이트 거부, raw_saturation_threshold 선례 | High |
| XDET-TC-005 ghost 비가시 종단 판정 T4 과대약속(FB 의존) | T4는 LTI 부산물 감소 부분 게이트, 운영 비가시는 실 패널 통합(결정 6) | Medium |
| 단일 노출 IRF 캘리브레이션 유입(SWR-401 금지) | IRF-2 결정론적 거부, 복수 노출 다점(2~90%) 요구 | Medium |
| 지수합 피팅 수렴·조건수(bᵢ 근접 시) | 강건 초기값·경계 제약, 합성 기지 계수로 복원 특성화, 정확도 우선 | Medium |
| 노출 구간별 IRF 전환(SWR-403) 과범위 구현 | Gen 1 단일 LTI 세트, 전환 로직 미구현(Exclusions), CalibSet 스키마만 확장 여지 | Low |
| EV 판정 임계 엔진/모듈 내장(측정=판정 결합) | 판정 수치 외부 주입, tests/에서만 비교(VALIDATE-5) | Low |

## 9. 마일스톤 (우선순위 기반, 시간 추정 없음)

- **Priority High — M0 결정 반영**: spec 「결정 필요/확인 사항」 1·2·4·6은 plan-audit 반복 1에서 확정(1=`pipeline/sequence.py` 러너, 2=(M,ny,nx) float32, 4=FB 트리거 러너 소유, 6=포화 보존+재귀 계산값); 3(harness 확장)·5(IRF 도구 배치)는 run 착수 전 확인. M1 이후 구현은 확정 결정을 전제로 한다.
- **Priority High — M1 CORR+STATE**: `modules/lag.py` — 지수합 상태변수 재귀(SWR-402) + 내부 상태 {sᵢ} 보유 + `serialize_state`/`load_state` + 시퀀스 간 리셋 + SATURATION 값 보존. lag CalibSet(LAG, 기지 IRF) fixture + 합성 잔상 시퀀스. XDET-TC-004 입력부.
- **Priority High — M2 CONTRACT+harness**: process 계약·불변·이력 체인·의존 방향·CalibSet 게이트, harness 상태 확장(load/serialize 대조, XDET-TC-000). registry `lag` 등록.
- **Priority Medium — M3 IRF 도구**: `metrics/lag_irf.py` — 복수 노출 step-response 피팅 → CalibSet(LAG); 단일 노출 거부; 합성 IRF 계수 복원 검증. M1과 독립(빌더는 오프라인).
- **Priority Medium — M4 GHOST**: FB 트리거 스텁(요청/완료, mock) — 시퀀스 러너 `pipeline/sequence.py` 소유(결정 4) + 전용 감쇠 없음 확인. 고대비→균일 합성 시퀀스. XDET-TC-005 부분 게이트.
- **Priority High — M5 VALIDATE**: 시퀀스 구동 통합(`pipeline/sequence.py` 러너, 결정 1), first-frame lag % 개선(`metrics/lag.compute_first_frame_lag`, tests/), ghost CNR 감소(`compute_ghost_cnr`), 상태 직렬화 왕복 바이트 재현(CONTRACT-2 첫 런타임 검증), XDET-TC-004(EV-104 min 게이트)·XDET-TC-005(부분 게이트) skeleton→live 전환. M1~M4 완료 후.
- 순서 원칙: M0(결정) → M1(재귀+상태)·M3(IRF 도구, 병행) → M2(계약+harness)·M4(ghost) → M5(통합·판정). harness 단독 시험(XDET-TC-000)은 M1 착수와 동반.

## 10. 검증 전략 — 합성 IRF + 보정 효과 판정

- **fixture 구성**: lag CalibSet(유효 기지 IRF/무효) + 합성 연속 시퀀스(기지 IRF 주입, `tests/` 전용).
- **판정**: (a) first-frame lag — `metrics/lag.compute_first_frame_lag`로 보정 전/후 %; 보정 후 ≤ EV-104 min 및 개선(XDET-TC-004, 측정프로토콜 §1.5); (b) ghost — `compute_ghost_cnr`로 보정 전/후 CNR 감소(XDET-TC-005 T4 부분 게이트); (c) 상태 직렬화 — 왕복 후 바이트 재현(CONTRACT-2, VALIDATE-4); (d) IRF 도구 — 주입 계수 복원·단일 노출 거부.
- **부정/경계 케이스**: CalibSet 부재/불일치 게이트 거부(EC-1), 단일 노출 IRF 거부(EC-2), 전용 ghost 감쇠 시도 부정 대조(EC-3), 사이드채널·의존 위반(EC-4), 시퀀스 간 상태 누출 부정 대조(EC-5), 포화 화소 값 보존(EC-6).
- **계약 검사**: `common.contract.check_process_contract`/`run_harness`(상태 확장)로 시그니처·반환형·전체 XFrame 비교·상태 왕복(XDET-TC-000); import-linter로 `module → common` 단방향·모듈 간/`metrics`/`pipeline` import 금지.
- **DoD**: lag 보정 합성 검증 PASS(first-frame lag % 개선·≤ EV-104 min + ghost CNR 감소 + 상태 직렬화 왕복 바이트 재현) + IRF 도구 복원·거부 + 부정/경계 케이스 정상 거부 + XDET-TC-004~005 실동작 전환 + 계약/의존 위반 0건.
- acceptance.md에 Given-When-Then 시나리오·엣지 케이스·품질 게이트를 상세화한다.
