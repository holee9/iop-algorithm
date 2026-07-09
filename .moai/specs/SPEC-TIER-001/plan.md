---
id: SPEC-TIER-001
title: T10 티어/동일성 프레임 (티어 판정·gating 구조 + 동일성 diff 프레임, 구조만·수치 P2)
version: 0.1.0
status: draft
created: 2026-07-09
updated: 2026-07-09
author: drake.lee
priority: high
issue_number: 11
labels: [T10, tier-gating]
---

# SPEC-TIER-001 구현 계획 (초안) — T10 티어/동일성 프레임

> 상태: **draft** (run 단계 착수 전까지 유지). EARS 확정본은 [spec.md](./spec.md), 인수 기준은 [acceptance.md](./acceptance.md). 선행 계약은 [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md)(REQ-INFRA-CI-4 동일성 훅·run_pipeline·sequence 래퍼 선례)·[SPEC-NDT-001](../SPEC-NDT-001/spec.md)(T0-표면-불변 계열 선례).

## 1. 개요

XDET P1의 **마지막 작업 T10**. 티어·동일성 프레임 WP12(SWR-1301~1303, FR-C012/C013)의 **구조**를 구현한다. 두 축 — (1) **티어 판정·gating 구조**(SWR-1301): 하드웨어 연산 능력(CPU 코어·AVX·GPU·VRAM) 소비 → 실행 티어 판정 + 근거 로그 + 강제 하향 수용/강제 상향 거부 + 실행 경로 선택; (2) **동일성 diff 프레임**(SWR-1302, XDET-TC-021): T0 `common/equivalence.diff_frames`(REQ-INFRA-CI-4 훅) 재사용 + 정수/부동소수점 경로 분류 + 구조 판정. **T10은 실행 인프라·검증 프레임 계층이며 처리 스테이지가 아니다** — 티어 gating은 `pipeline/tier.py`(신규, run_pipeline additive 래퍼), 동일성 diff는 `common/equivalence.py` 확장으로 배치하고 T0 오케스트레이터 표면을 변경하지 않는다(결정 1). **수치 임계는 전부 P2**(티어 판정 임계·bit-동일/±1 LSB·절대 처리시간). 완료 정의: **티어 gating 구조(XDET-TC-020) + 동일성 diff 프레임(XDET-TC-021)을 구조 검증으로 성립** — 본 SPEC의 TC-020/021 구조 통과가 Gen 1 XDET-TC-000~021 전체를 완성하고 **P1 완료 정의(골든 모델 형상 동결)** 마일스톤을 표시한다(P1 최종 SPEC).

## 2. 기술 스택

| 항목 | 선택 | 근거 |
|---|---|---|
| 언어/런타임 | Python 3.11+ | tech.md |
| 수치/타이밍 | numpy(구조 비교), `time.perf_counter`(cold/warm 타이밍 레코드 — 절대 게이트 없음) | tech.md, XDET-TC-020 |
| 시험 프레임워크 | pytest + CI (XDET-TC-020/021 skeleton → 실동작 구조 케이스 전환) | TestSpec, SWR-000-11 |
| 동일성 diff | **T0 `common/equivalence.diff_frames` 재사용**(REQ-INFRA-CI-4 훅, 재구현 금지) | SPEC-INFRA-001 |
| 파이프라인 소비 | `pipeline/orchestrator.run_pipeline`·`PipelineDefinition`(CANONICAL_ORDER 부분수열)을 additive 래퍼로 감쌈 | SPEC-INFRA-001 |
| 배치 선례 | `pipeline/sequence.py`(run_pipeline additive 래퍼) · T9 NDT(T0 표면 불변) | SPEC-LAG-001, SPEC-NDT-001 |
| 정적 검사 | import-linter — `common/equivalence` 순수(pipeline/modules/metrics import 없음) · `pipeline/tier`는 orchestrator만 소비 | SPEC-INFRA-001 REQ-INFRA-STATIC |
| 수치 정책 | 티어 판정 임계·bit-동일/±1 LSB·절대 처리시간 = **P1 하드코딩 금지, P2 이연** | CLAUDE.md T10 "수치 임계는 P2" |

원칙: **정확도·구조 성립 단일 목표, 속도 최적화 금지.** 수치 임계 하드코딩 금지(전부 P2). EV 판정 수치 미내장(측정=판정 분리). T0 표면 불변(결정 1).

### 티어 taxonomy·경로 선택 (REQ-TIER-GATE HOW)

P1의 실행 구현은 단 하나(결정론적 CPU float 골든 모델, ≈Tier 1)이므로 티어 taxonomy는 **구조**로 성립시키되 실 벤치마크 임계는 P2로 둔다:
- **티어 판정**: capability 기술자(CPU 코어·AVX 플래그·GPU 모델·VRAM)를 입력 구조로 받아 지원 티어를 반환. 어느 값→어느 티어의 수치 임계는 P1에 없고(P2 벤치마크), P1은 판정 함수 시그니처·근거 로그 구조·강제 하향/상향 규칙만 성립.
- **강제 하향/상향**: `요청 티어 ≤ 검출 티어` → 수용; `요청 티어 > 검출 티어` → 명시 오류(단일 경로, 택일 없음). 티어 순서(ordinal)는 구조적으로 비교 가능(수치 임계 무관).
- **경로 선택**: 확정 티어 → 대응 `PipelineDefinition`·registry 선택 → `run_pipeline`에 전달. P1은 Tier 1(결정론적) 경로만 실 실행 가능; Tier 2(GPU 가속) 경로는 taxonomy상 존재하나 구현 없음(P2). DL 티어(SWR-1303)는 미구현(Gen 2).

## 3. 모듈 분해 (pipeline/ · common/ 확장 — 신규 스테이지 없이 additive 배치)

```
common/
  equivalence.py    # [확장] 기존: diff_frames(a,b)->EquivalenceDiff (REQ-INFRA-CI-4 훅, 구조만)
                    #  신규: 경로 분류 헬퍼(정수 경로 offset/gain/defect/line_noise vs 부동소수점 경로)
                    #        + 경로 인지 구조 판정 래퍼 — diff_frames 재사용, 수치 임계 없음 (결정 2)
pipeline/
  tier.py           # [신규] run_pipeline additive 래퍼 (pipeline/sequence.py 선례):
                    #  - decide_tier(capability) -> tier + 근거 로그 (SWR-1301, 임계 P2)
                    #  - 강제 하향 수용 / 강제 상향 거부 (SWR-1301)
                    #  - select_pipeline(tier) -> (PipelineDefinition, registry) (경로 선택)
                    #  - run_tier(frame, tier, ...) -> XFrame (run_pipeline 위임, 표면 불변)
                    #  - time_tier(...) -> TimingRecord (cold/warm 중앙값, 절대 게이트 없음)
```

배치 원칙(결정 1): T10은 T0 표면(`CANONICAL_ORDER`·`CalibKind`·`_KIND_BY_STAGE`)을 변경하지 않는다. 신규 처리 스테이지·신규 CalibKind 없음. `pipeline/tier.py`는 `run_pipeline` 시그니처를 바꾸지 않고 감싸는 additive 래퍼(sequence.py 선례). `common/equivalence.py`는 `common/xframe`만 의존하는 순수 비교 확장(pipeline/modules/metrics import 없음). 티어 쌍 산출·perturbation·구조 검증 하니스는 **`tests/` 전용**(`tests/pipeline/` — INFRA/METRICS/NDT 선례, 검증 도구는 프로덕션 트리 밖). 티어 taxonomy·경로 선택은 P1에 Tier 1 실 경로 하나 + Tier 2 taxonomy 자리만.

## 4. EARS 구조 설계 (확정본은 spec.md)

5개 요구 그룹. `[Ubiquitous]`/`[Event]`/`[State]`/`[Unwanted]`는 EARS 패턴 표기.

- **REQ-TIER-GATE** (SWR-1301) — capability→티어 판정+근거 로그(`[Event]`, 임계 P2), 티어=경로 선택 not EV 등급(`[Ubiquitous]`), 강제 하향 수용(`[Event]`), 강제 상향 거부(`[Unwanted]`), 확정 티어→PipelineDefinition/registry 선택 additive 래퍼(`[Event]`).
- **REQ-TIER-EQUIV** (SWR-1302, XDET-TC-021) — diff_frames 재사용 재구현 금지(`[Ubiquitous]`), 정수/부동소수점 경로 분류+구조 판정(`[Event]`), 동일 쌍 structurally_equal 양성(`[State]`), perturbation 쌍 차이 검출 음성 대조(`[State]`).
- **REQ-TIER-TIMING** (SWR-1301/EV-401, XDET-TC-020) — cold/warm 중앙값 타이밍 레코드(`[Event]`), 절대 시간 게이트 없음 구조만(`[Ubiquitous]`).
- **REQ-TIER-CONTRACT** (SWR-000-6~12) — 처리 모듈 아님·T0 표면 불변·additive 래퍼(`[Ubiquitous]`), 레이어링 common 순수/tier는 orchestrator만(`[Ubiquitous]`), 수치 임계 P2 이연 하드코딩 금지(`[Ubiquitous]`), 측정=판정 분리(`[Ubiquitous]`), CI-4 훅 재사용 재구현 금지(`[Ubiquitous]`).
- **REQ-TIER-VALIDATE** (XDET-TC-020/021) — 티어 gating 구조 통과(`[State]`, TC-020), 동일성 diff 프레임 구조 통과+음성 대조(`[State]`, TC-021), 수치 게이트 P2 PARTIAL 이연(`[Ubiquitous]`), TC-000~021 완성·P1 완료 정의 골든 모델 형상 동결 capstone(`[Ubiquitous]`).

## 5. 구조 검증 fixture 전략 (수치 임계 없이 구조 성립)

| 대상 | 합성/구조 fixture | 검증 대상 (구조) |
|---|---|---|
| 티어 판정 | mock capability 기술자(CPU 코어·AVX 플래그·GPU 모델·VRAM 조합) | 판정 함수가 티어+근거 로그 산출; 임계 수치 미검증(P2) |
| 강제 하향/상향 | 검출 티어 + 사용자 요청 티어 쌍(이하/초과) | 이하 요청 수용, 초과 요청 명시 오류(구조 규칙) |
| 경로 선택 | 확정 티어 | 대응 PipelineDefinition/registry 선택, run_pipeline 위임(표면 불변) |
| 동일성 diff (양성) | 동일 입력 XFrame → 골든 모델 2회 산출 | diff_frames structurally_equal=True, max_pixel_abs_diff==0 |
| 동일성 diff (음성 대조) | 한쪽 pixel/mask 의도적 perturbation | structurally_equal=False, max_pixel_abs_diff>0 (공허 통과 아님) |
| 경로 분류 | 정수 경로(offset/gain/defect/line_noise) vs 부동소수점 경로 스테이지 셋 | 분류 라벨 산출(P2 게이트 타입 표시), 수치 허용오차 단정 없음 |
| 타이밍 하니스 | Tier 1 경로 + 표준 프레임 | cold/warm 중앙값 타이밍 레코드 산출; 절대 시간 게이트 없음 |

원칙: fixture·하니스는 `tests/pipeline/`에 두고, **수치 임계를 단정하지 않는다**(전부 P2). 동일성 프레임은 P1에 제2 실 구현이 없으므로 자기-대조(양성)·perturbation(음성)으로 프레임 기계장치를 검증한다. P2에서 실 GPU/정수 커널이 추가되면 동일 diff 훅에 실 출력 쌍을 입력해 수치 게이트(bit-동일/±1 LSB) 적용(프레임 재구현 불필요).

## 6. 리스크 분석 (요약)

| 리스크 | 완화 | 우선순위 |
|---|---|---|
| 배치 오판(결정 1) — 티어 gating이 T0 표면 변경 유혹 | `run_pipeline` 시그니처 불변 additive 래퍼(sequence.py 선례); 표면 변경 필요 판단 시에만 run-blocking 재검토 | High |
| 동일성 diff 재구현(중복) | T0 `common/equivalence.diff_frames` 재사용 필수화(SWR-000-9, CI-4 훅) | High |
| 수치 임계 조기 유입(P2 게이트 P1 진입) | bit-동일/±1 LSB/절대 시간 하드코딩 금지, P1은 구조·경로 분류만; P2 레지스터 이연 명시 | High |
| "티어"=EV 등급 오해석 | SWR-1301+EV-401 텍스트로 연산 능력 티어 확정(결정 3); EV min/typ/max와 독립 문서화 | High |
| 절대 처리시간 게이트 유입(EV-401 P1 진입) | 타이밍 하니스 구조만, 절대 시간 P2 이연(REQ-TIER-TIMING-2); P1 골든 모델 의도적 느림 | Medium |
| 동일성 프레임 공허 통과(음성 대조 부재) | perturbation 쌍 차이 검출 음성 대조 필수(REQ-TIER-EQUIV-4) | Medium |
| DL 경로(SWR-1303) 범위 유입 | Gen 2 미구현 Exclusions 명시(결정 5); taxonomy 예약 이름만(선택) | Medium |
| 측정=판정 결합(EV 임계 내장) | 티어 gating은 분류·경로만 산출, EV-401/402 판정 외부(CONTRACT-4) | Medium |

## 7. 마일스톤 (우선순위 기반, 시간 추정 없음)

- **Priority High — M1 CONTRACT + 동일성 훅 재사용 골격**: `common/equivalence.py`에 정수/부동소수점 경로 분류 헬퍼 + 경로 인지 구조 판정 래퍼(diff_frames 재사용) 확장; import-linter 계약(common 순수·tier는 orchestrator만), T0 표면 불변 확인(CANONICAL_ORDER 무변경). 모든 후속의 전제(결정 1·2).
- **Priority High — M2 EQUIV(동일성 diff 프레임)**: 동일 입력 2회 산출 양성 + perturbation 음성 대조 구조 케이스, 정수/부동소수점 경로 분류. XDET-TC-021 구조 통과(수치 임계 없이).
- **Priority High — M3 GATE(티어 판정·gating)**: `pipeline/tier.py` — `decide_tier`(capability→티어+근거 로그, 임계 P2) + 강제 하향 수용/강제 상향 거부 + `select_pipeline`(경로 선택, run_pipeline additive 래퍼). XDET-TC-020 티어 gating 구조 통과.
- **Priority Medium — M4 TIMING**: `time_tier`(cold/warm 중앙값 타이밍 레코드, 절대 게이트 없음). XDET-TC-020 타이밍 하니스 구조부.
- **Priority High — M5 VALIDATE 전환 + capstone**: XDET-TC-020/021 pytest skeleton(skip) → 실동작 구조 케이스 전환. **Gen 1 XDET-TC-000~021 전체 CI 통과 확인 + P1 완료 정의(골든 모델 형상 동결) 마일스톤 표시.** DL(SWR-1303)·수치 게이트 P2 PARTIAL 이연 문서화.
- 순서 원칙: M1(훅 재사용·계약) 확정 후 착수. M2(EQUIV)·M3(GATE)는 M1 이후 병행 가능(독립 — EQUIV는 common, GATE는 pipeline). M4는 M3(경로 선택) 의존. M5는 전체 후 capstone 확인.

## 8. 검증 전략 — 구조 성립 (수치 임계 없이)

- **fixture 구성**: mock capability 기술자·티어 요청 쌍·동일/​perturbation XFrame 쌍·정수/부동소수점 경로 셋·Tier 1 타이밍 하니스(`tests/pipeline/`).
- **구조 DoD 판정**: (a) 티어 판정·근거 로그·강제 하향 수용·강제 상향 거부·경로 선택 구조 동작(XDET-TC-020, 절대 시간·벤치마크 없이); (b) diff_frames 재사용으로 동일 쌍 structurally_equal=True(양성)·perturbation 쌍 차이 검출(음성)·정수/부동소수점 경로 분류(XDET-TC-021, 수치 bit-동일/±1 LSB 단정 없이).
- **경계/부정 케이스**: 강제 상향 요청 명시 거부, perturbation 쌍 공허-통과-아님, capability 결여/무효 기술자 명시 처리.
- **PARTIAL(P2/Gen 2 이연)**: 정수 bit-동일·부동소수점 ±1 LSB 수치 게이트(EV-402), 절대 처리시간 게이트(EV-401), 실 하드웨어 벤치마크·GPU 가속 커널, DL 경로(SWR-1303).
- **DoD**: GATE/EQUIV/TIMING 구조 케이스 통과 + 강제 상향 거부·음성 대조 정상 + XDET-TC-020/021 pytest 등록·구조 통과 + T0 표면 불변 확인 + **Gen 1 XDET-TC-000~021 전체 CI 통과 → P1 완료 정의(골든 모델 형상 동결) 마일스톤**.
- acceptance.md에 Given-When-Then 시나리오·엣지 케이스·품질 게이트 상세화.
