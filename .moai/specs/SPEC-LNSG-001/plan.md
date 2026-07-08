---
id: SPEC-LNSG-001
title: T3 WP3 line noise 보정 + WP4 포화·기하 처리 모듈 (열 프로파일 감산 · 포화 마스킹 · 격자 왜곡 보정)
version: 0.1.1
status: draft
created: 2026-07-09
updated: 2026-07-09
author: drake.lee
priority: high
issue_number: 4
---

# SPEC-LNSG-001 구현 계획 (초안) — T3 WP3 line noise + WP4 포화·기하 처리 모듈

> 상태: **draft** (run 단계 착수 전까지 유지). EARS 확정본은 [spec.md](./spec.md), 인수 기준은 [acceptance.md](./acceptance.md). 선행 계약은 [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md)(프레임워크)·[SPEC-METRICS-001](../SPEC-METRICS-001/spec.md)(line noise 판정 엔진)·[SPEC-CORR-001](../SPEC-CORR-001/spec.md)(선행 보정 모듈·SATURATION 플래그 계약).

## 1. 개요

XDET P1의 네 번째 작업 T3(WP3+WP4). line noise·포화·기하 처리 모듈 3종을 T0 계약 `process(XFrame, CalibSet, Params) -> XFrame`으로 구현한다. 세 모듈은 고정 순서 `CANONICAL_ORDER`의 line_noise → saturation → geometry 위치에서 실행된다. line noise 보정은 **레퍼런스 부재 전제의 SWR-503 대안 경로를 P1 우선 경로로 구현**(EARS Optional/WHERE, reference 부재 조건)하고 레퍼런스 기반 SWR-501/502는 상보 조건부(Optional, reference 제공)로 둔다. 포화는 검출·마스킹·경계 밴드·**복원 절대 금지**(SWR-602)를 담당하고, 기하는 격자 팬텀 캘리브레이션 잔차가 EV-106 min 이상일 때만 조건부 활성한다. 완료 정의: **합성 주입 왜곡 억제·처리 검증** — line noise 제거는 T1 엔진 `metrics/nps.detect_line_noise`로, 구조물 오보정률·포화 사후조건·기하 잔차는 `tests/` ground truth 대조 직접 측정으로 판정하고, XDET-TC-006~009를 skeleton에서 실동작 케이스로 전환(EV-105/106 min 대비).

## 2. 기술 스택

| 항목 | 선택 | 근거 |
|---|---|---|
| 언어/런타임 | Python 3.11+ | tech.md |
| 수치 연산 | numpy, scipy (float 골든 모델) | tech.md, CLAUDE.md 아키텍처 |
| 시험 프레임워크 | pytest + CI (XDET-TC-006~009 실동작 전환) | TestSpec, SWR-000-11 |
| 처리 계약 | `process(XFrame, CalibSet, Params) -> XFrame` 순수함수 | SPEC-INFRA-001 REQ-INFRA-CONTRACT-1 |
| 조합 계약 | 오케스트레이터 registry 등록(line_noise/saturation/geometry 단계) | SPEC-INFRA-001 REQ-INFRA-ORCH-1/3 |
| 진입 게이트 | CalibSet 존재·해상도·패널 ID·유효기간; line_noise→LINE_NOISE 배선; saturation/geometry→OTHER | `pipeline/orchestrator.py` `_calibration_gate`·`_KIND_BY_STAGE` |
| 공용 컴포넌트 | `common/robust_stats`(중앙값/MAD)·`common/fft_psd`(FFT/PSD)·`common/mask_ops`(마스크/경계 밴드) 참조(중복 금지) | SWR-000-9, REQ-INFRA-STATIC-3 |
| 정적 검사 | import-linter 레이어 `module → common` 단방향 | SPEC-INFRA-001 REQ-INFRA-STATIC |
| 판정 소비 | `metrics.nps.detect_line_noise`(tests/에서만); 오보정률·포화·기하 잔차는 tests/ 직접 측정 | SPEC-METRICS-001 |
| 파라미터 | SWR-503 창/컷오프·S_th·다항 차수·reference 좌표·오염계수·밴드폭 = Params/CalibSet | CLAUDE.md 파라미터 정책, SWR 부록 A |

원칙: **정확도 단일 목표, 속도 최적화 금지.** 하드코딩 금지 — 전 상수 Params/CalibSet 주입. EV 판정 수치 미내장(측정=판정 분리).

## 3. 모듈 분해 (modules/ 패키지 레이아웃)

```
modules/
  __init__.py
  line_noise.py  # SWR-501~504: (Optional/WHERE reference 부재, P1 우선) SWR-503 열 방향 저주파 프로파일
                 #   (행별 강건 평균 → 1D median, 창 length [T]) 감산 + 고역 제한(컷오프 [T]);
                 #   (Optional/WHERE reference 제공) SWR-501/502 행 중앙값 감산 + k·MAD(6) 오염 배제;
                 #   강건 통계에서 DEFECT/INTERPOLATION/SATURATION 마스크 제외; 노이즈 모델 미갱신
  saturation.py  # SWR-601~602: 상류 offset(raw ≥ S_th, REQ-CORR-OFFSET-4) ∪ gain 클램프 누적 SATURATION 마스크 소비·전달;
                 #   경계 밴드(2px) 완충 가중 표시; 복원 절대 금지(값 불변·SATURATION 유지·INTERPOLATION 신규 미설정[기존 보존]);
                 #   포화 통계 이력 체인 메타 기록 (raw 재검출 없음 — S_th는 offset 단계 Params `raw_saturation_threshold`)
  geometry.py    # SWR-603: CalibSet(OTHER) 저차 다항 왜곡 모델(차수 [B], 2-6) → 기하 보정;
                 #   캘리브레이션 잔차 < EV-106 min 이면 비활성(무처리 통과)
```

`common/`(중복 금지, CORE 소비 — SWR-000-9): 프로파일·행 중앙값·MAD는 `common/robust_stats`, 1D NPS/스펙트럼 유틸은 `common/fft_psd`, 마스크·경계 밴드(팽창) 연산은 `common/mask_ops`를 참조로 사용한다. 실 구현이 필요하면 T1이 유발한 스텁을 재사용하고 `common/`에만 두며 `modules/`에 중복하지 않는다.

**진단 부산물(포화 통계·경고)의 전달**: XFrame 컨테이너 외 사이드채널 금지(SWR-000-6). 포화 화소 비율 등은 스칼라로 해당 처리 단계의 **이력 체인 엔트리 메타데이터**에 기록한다(마스크 아님, 부가 반환값 아님). DICOM 태그 실제 emission은 출력 포맷 소관(Exclusions).

합성 팬텀 생성기(기지 왜곡 주입)는 **`tests/` 전용 fixture**로 둔다(SPEC-INFRA-001·METRICS-001·CORR-001의 tests/ 전용 결정 계승). `tests/modules/phantoms/`에 모듈별 생성기(기지값 동반)를 배치하고 `modules/`는 순수 처리만 유지한다.

## 4. EARS 구조 설계 (확정본은 spec.md)

5개 요구 그룹. `[Ubiquitous]`/`[Event]`/`[State]`/`[Optional]`/`[Unwanted]`는 EARS 패턴 표기.

- **REQ-LNSG-LINE** — SWR-503 열 프로파일 감산+고역 제한 우선 경로(`[Optional]` WHERE reference 부재, LINE-1), reference 기반 행 중앙값+6·MAD 오염 배제 조건부(`[Optional]` WHERE reference 제공, LINE-2), 마스크 제외+노이즈 모델 미갱신(`[Ubiquitous]`, LINE-3). LINE-1·LINE-2는 reference 유무로 갈리는 상호배타 보완쌍.
- **REQ-LNSG-SAT** — 누적 SATURATION 마스크(offset raw ∪ gain 클램프) 소비·전달(`[Event]`, SAT-1), 경계 밴드 완충 가중 표시(`[Event]`, SAT-2), 복원 금지 사후조건(`[Unwanted]`, SAT-3), 포화 통계 이력 메타 기록(`[Event]`, SAT-4).
- **REQ-LNSG-GEOM** — 다항 왜곡 보정 조건부 적용(`[Optional]`, GEOM-1), 잔차 < EV-106 min 시 비활성(`[State]`, GEOM-2).
- **REQ-LNSG-CONTRACT** — process 시그니처·불변(`[Ubiquitous]`), 이력 체인(`[Event]`), 의존 방향(`[Ubiquitous]`), 사이드채널 금지 한정(`[Unwanted]`), CalibSet 게이트 거부(`[Unwanted]`), 고정 순서·harness(`[Ubiquitous]`).
- **REQ-LNSG-VALIDATE** — 합성 검증(`[State]`), line noise 제거 detect_line_noise 판정(`[Event]`, VALIDATE-2), 구조물 오보정률(`[Event]`, VALIDATE-3), 포화 검출·마스킹·복원금지 T3 부분 게이트(`[Event]`, VALIDATE-4), 기하 잔차(`[Event]`, VALIDATE-5), EV 외부 주입(`[Ubiquitous]`), TC skeleton→live(`[Ubiquitous]`).

## 5. CalibSet fixture 전략 (모듈별)

`common.calibset.CalibSet` 공통 스키마(panel_id · resolution · valid_from/until · kind · data · provenance)를 사용한다. 게이트가 존재·해상도·패널 ID·유효기간을 검사하고, line_noise 단계는 추가로 종류-단계 배선(kind=LINE_NOISE)을 검사한다.

| 모듈 | CalibSet(kind) data 페이로드 | 무효 fixture(부정 경로) |
|---|---|---|
| line_noise | (우선) reference-availability=없음(SWR-503 경로 선택 표식); (Optional) reference 영역 좌표([B], SWR-501/502 경로) | 해상도 불일치 · kind≠LINE_NOISE · 유효기간 밖 |
| saturation | kind=OTHER (S_th 없음 — raw 검출·`raw_saturation_threshold`는 offset 단계 소관, 결정 2) | 해상도 불일치 · 패널 ID 불일치 · 유효기간 밖 |
| geometry | kind=OTHER; 저차 다항 왜곡 계수(차수 [B]) + 캘리브레이션 잔차 | 해상도 불일치 · 패널 ID 불일치 · 유효기간 밖 |

무효 fixture는 오케스트레이터 진입 게이트(`_calibration_gate`)가 `CalibrationError`로 거부함을 확인한다(REQ-LNSG-CONTRACT-5, acceptance EC-1). line_noise 경로 선택은 CalibSet(LINE_NOISE)의 reference-availability 내용으로 결정론적으로 이뤄진다(spec 「결정 필요/확인 사항」 1 — CalibSet vs 게이트 예외 표현은 확인 대상).

## 6. 합성 팬텀 전략 (모듈별 기지 왜곡 주입 → 억제·처리 확인)

| 모듈 | 합성 팬텀(기지 왜곡 주입) | 처리 후 검증(기지값) |
|---|---|---|
| line_noise (제거) | 균일 신호 + 기지 행/열 저주파 오프셋(line noise) + 잡음 | `metrics/nps.detect_line_noise`로 보정 전 이상 피크 검출 → 보정 후 미검출(SWR-504 + REQ-METRICS-NPS-8 확장(행/열), XDET-TC-006) |
| line_noise (오염) | 균일 신호 + line noise + 금속 구조물 오염 모사(고감쇠 영역, ground truth 동반) | 구조물 영역 오보정률 ≤ EV-105 min(ground truth 대비 허위 변경 화소 비율, XDET-TC-007) |
| saturation | 균일/신호 + 기지 포화 영역(좌표·강도, raw ≥ S_th; offset 단계가 SATURATION 검출) | offset 검출 SATURATION 플래그 전수 보존 + 경계 밴드 표시 + 복원 금지 사후조건(값 불변·INTERPOLATION 신규 미설정, XDET-TC-008 T3 부분 게이트) |
| geometry | 이상 격자 + 기지 저차 다항 왜곡 주입(격자선 변위) | 보정 후 격자선 잔차 ≤ EV-106 min; 잔차 < min 주입 시 모듈 비활성 관측(XDET-TC-009) |

원칙: 팬텀 생성기는 `tests/modules/phantoms/`에 두고 기지값(주입 좌표·패턴·격자 위치)을 함께 반환. 허용오차·EV 임계는 [T]/외부 주입(하드코딩 금지). line noise 판정은 `tests/`에서 `metrics.nps.detect_line_noise`를 소비한다(모듈은 metrics import 금지 — CONTRACT-3). 오보정률·포화 사후조건·기하 잔차는 T1 엔진에 대응 함수가 없어 `tests/` ground truth 대조 직접 측정으로 판정한다.

## 7. 파이프라인 통합

- 세 모듈의 `process`를 오케스트레이터 registry에 `"line_noise"`·`"saturation"`·`"geometry"` 스테이지로 등록한다(`pipeline/orchestrator.py` `run_pipeline(registry=...)`).
- `PipelineDefinition(stages=(…,"line_noise","saturation","geometry"))`는 `CANONICAL_ORDER` 부분수열이므로 순서 계약을 만족한다(REQ-LNSG-CONTRACT-6).
- 진입 게이트는 각 스테이지 CalibSet의 존재·해상도·패널 ID 상호일치·유효기간을 검사하고, line_noise 단계는 종류-단계 배선(kind=LINE_NOISE)을 추가 검사한다. saturation/geometry는 `_KIND_BY_STAGE` 미등재로 종류 강제는 없다(CalibKind.OTHER). 세 모듈은 게이트 통과 후에만 실행된다(REQ-LNSG-CONTRACT-5).
- 검증 모드(validation_mode) 활성 시 단계별 중간 XFrame이 보존되므로(REQ-INFRA-DATA-5) before/after 판정 입력에 재사용한다. raw 포화 검출은 I_raw를 받는 유일 단계인 offset이 수행하므로(REQ-CORR-OFFSET-4, spec 「결정 필요/확인 사항」 2 확정) 포화 모듈은 raw 참조가 불필요하며 누적 SATURATION 마스크만 소비한다.

## 8. 리스크 분석 (요약)

| 리스크 | 완화 | 우선순위 |
|---|---|---|
| line noise 우선 경로(SWR-503)와 게이트 CalibSet 요구 충돌 | 경로 선택을 CalibSet(LINE_NOISE) 내용으로 결정론화, 게이트 예외/표현은 spec 「결정 필요」 1 확인 후 확정 | High |
| SWR-601 raw 검출 시점(포화 단계가 파이프라인 후반) | **확정(결정 2)**: raw 검출을 I_raw 소비 유일 단계 offset으로 이관(REQ-CORR-OFFSET-4), 포화 모듈은 누적 SATURATION 소비 | 해소 |
| SWR-602 경계 밴드(2px)의 XFrame 표현(가중 채널 부재) | SATURATION 팽창 근사(P1), graded 가중은 T5, spec 「결정 필요」 3 확인 | High |
| 복원 금지(SWR-602 [HARD]) 위반 유입 | Unwanted REQ-LNSG-SAT-3 사후조건(값 불변·플래그 유지) + EC 부정 케이스 게이트 | High |
| 하드코딩 유입(창/컷오프·S_th·차수·오염계수·밴드폭) | Params/CalibSet 주입 필수화, [B]/[T]/[C] 등급 주석 규약, 6·2px 부록 A 등재 요청 | High |
| EV-106 포화 비가시 종단 판정 T3 과대약속 | T3는 검출·마스킹·복원금지 부분 게이트, 종단 비가시는 T5/T6, spec 「결정 필요」 4 | Medium |
| 구조물 오보정률 게이트 경로 의존(SWR-502 vs SWR-503) | 활성 경로 기준 오보정률 측정, 레퍼런스 fixture 포함 여부 spec 「결정 필요」 5 | Medium |
| 고역 제한 컷오프 튜닝(해부학 저주파 보호 vs 제거율) | [T] 외부화, 합성 기지값으로 특성화, 정확도 우선 | Medium |
| line noise 감산 후 노이즈 모델 영향 | 재추정 안 함(SWR-701/T5 소관, 결정 5) 명시 | Medium |
| 기하 활성/비활성 경계 판정(잔차 대 EV-106 min) | 결정론적 비교(State-Driven GEOM-2), 무단 기본값 없음 | Low |
| EV 판정 임계 엔진/모듈 내장(측정=판정 결합) | 판정 수치 외부 주입, tests/에서만 비교(VALIDATE-6) | Low |

## 9. 마일스톤 (우선순위 기반, 시간 추정 없음)

- **Priority High — M1 LINE(우선 경로)**: `modules/line_noise.py` — SWR-503 열 프로파일 감산 + 고역 제한(창/컷오프 [T]) + 마스크 제외 + 노이즈 모델 미갱신. line_noise CalibSet(LINE_NOISE, reference 없음) fixture + 합성 line noise 팬텀. XDET-TC-006 입력부.
- **Priority Medium — M2 LINE(레퍼런스 경로, Optional)**: SWR-501/502 행 중앙값 감산 + k·MAD(6) 오염 배제. reference 영역 CalibSet fixture + 구조물 오염 팬텀. XDET-TC-007 오보정률(레퍼런스 경로). M1과 동일 파일, 경로 분기.
- **Priority High — M3 SAT**: `modules/saturation.py` — offset(raw≥S_th, REQ-CORR-OFFSET-4) ∪ gain 클램프 누적 SATURATION 마스크 소비·통합 + 경계 밴드 표시 + 복원 금지 사후조건 + 포화 통계 이력 메타(raw 재검출 없음). saturation CalibSet(OTHER) fixture + 합성 포화 팬텀(offset이 SATURATION 검출). XDET-TC-008 T3 부분 게이트.
- **Priority Medium — M4 GEOM**: `modules/geometry.py` — 다항 왜곡 보정(차수 [B]) + 잔차 < EV-106 min 비활성. geometry CalibSet(OTHER) fixture + 격자 팬텀. XDET-TC-009. M1~M3과 독립.
- **Priority High — M5 VALIDATE**: 오케스트레이터 registry 통합, line noise 제거 판정(`metrics/nps.detect_line_noise`, tests/), 오보정률·포화 사후조건·기하 잔차 ground truth 대조, XDET-TC-006~009 skeleton→live 전환. M1~M4 완료 후.
- 순서 원칙: M1(우선 경로) → M2(레퍼런스 경로)·M3(포화)·M4(기하, 병행 가능) → M5(통합·판정). harness 단독 시험(XDET-TC-000)은 각 모듈 착수와 동반. run 착수 전 spec 「결정 필요/확인 사항」 1·3·4·5·6 확인 필요(항목 2는 결정 확정 — raw 포화 검출 = offset REQ-CORR-OFFSET-4).

## 10. 검증 전략 — 합성 팬텀 + 왜곡 억제 판정

- **fixture 구성**: 모듈별 CalibSet(유효/무효) + 합성 팬텀(기지 왜곡 동반, `tests/modules/phantoms/`).
- **판정**: (a) line noise — `metrics/nps.detect_line_noise`로 보정 전/후 1D NPS 이상 피크 검출·미검출(SWR-504 + REQ-METRICS-NPS-8 확장(행/열), XDET-TC-006); 구조물 오보정률 ground truth 대조 ≤ EV-105 min(XDET-TC-007); (b) 포화 — offset 검출(raw ≥ S_th) SATURATION 플래그 보존·경계 밴드·복원 금지 사후조건(XDET-TC-008 T3 부분 게이트); (c) 기하 — 격자선 잔차 ≤ EV-106 min·잔차 < min 비활성(XDET-TC-009).
- **부정/경계 케이스**: CalibSet 부재/불일치 게이트 거부(EC-1), 복원 금지 사후조건(EC-2), line noise 마스크 제외 미준수 검출(EC-3), 사이드채널·의존 위반(EC-4).
- **계약 검사**: `common.contract.check_process_contract`/`run_harness`로 시그니처·반환형·전체 XFrame 비교(XDET-TC-000); import-linter로 `module → common` 단방향·모듈 간/`metrics`/`pipeline` import 금지.
- **DoD**: 3개 처리 모듈 합성 왜곡 억제·처리 PASS(line noise 이상 피크 제거·오보정률 ≤ EV-105 min·포화 마스크 통합/복원 금지·기하 잔차 ≤ EV-106 min) + 부정/경계 케이스 정상 거부 + XDET-TC-006~009 실동작 전환 + 계약/의존 위반 0건.
- acceptance.md에 Given-When-Then 시나리오(모듈별)·Optional 조건부 AC·엣지 케이스·품질 게이트를 상세화.
