---
id: SPEC-CORR-001
title: T2 WP1 offset/gain/defect 보정 모듈 (다크 감산 · 평탄장 정규화 · 결함 보간)
version: 0.1.1
status: draft
created: 2026-07-09
updated: 2026-07-09
author: drake.lee
priority: high
issue_number: 3
---

# SPEC-CORR-001 구현 계획 (초안) — T2 WP1 offset/gain/defect 보정 모듈

> 상태: **draft** (run 단계 착수 전까지 유지). EARS 확정본은 [spec.md](./spec.md), 인수 기준은 [acceptance.md](./acceptance.md). 선행 계약은 [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md)(프레임워크)·[SPEC-METRICS-001](../SPEC-METRICS-001/spec.md)(판정 엔진).

## 1. 개요

XDET P1의 세 번째 작업 T2(WP1). offset·gain·defect 보정 처리 모듈 3종을 T0 계약 `process(XFrame, CalibSet, Params) -> XFrame`으로 구현한다. 세 모듈은 고정 순서 offset → gain → defect의 해당 위치에서 실행되며, offset map·gain map·defect map을 CalibSet로 소비한다. 결함 맵은 defect-map 빌더(`metrics/defect_map.py`)가 T1 엔진 `classify_defects` 재사용으로 생성하며(결정 1 확정, metrics→common 레이어링), 처리 모듈 `modules/defect.py`는 이를 소비만 한다. 완료 정의: **합성 주입 왜곡 제거를 T1 지표 엔진으로 before/after 판정** — 실측 도착 전 기지 offset/gain/defect 주입 합성 프레임으로 각 보정을 검증하고, XDET-TC-001·002·003을 skeleton에서 실동작 케이스로 전환(EV-101/102/103 min 대비). XDET-TC-003의 EV-103은 잔존 cluster 0건(처리 모듈)과 검출 누락률(빌더) 두 다리로 판정한다.

## 2. 기술 스택

| 항목 | 선택 | 근거 |
|---|---|---|
| 언어/런타임 | Python 3.11+ | tech.md |
| 수치 연산 | numpy, scipy (float 골든 모델) | tech.md, CLAUDE.md 아키텍처 |
| 시험 프레임워크 | pytest + CI (XDET-TC-001~003 실동작 전환) | TestSpec, SWR-000-11 |
| 처리 계약 | `process(XFrame, CalibSet, Params) -> XFrame` 순수함수 | SPEC-INFRA-001 REQ-INFRA-CONTRACT-1 |
| 조합 계약 | 오케스트레이터 registry 등록(offset/gain/defect 단계) | SPEC-INFRA-001 REQ-INFRA-ORCH-1/3 |
| 진입 게이트 | CalibSet 종류-단계 배선(offset→OFFSET, gain→GAIN, defect→DEFECT) | `pipeline/orchestrator.py` `_calibration_gate` |
| 공용 컴포넌트 | `common/mask_ops`·`robust_stats` 참조(중복 금지) | SWR-000-9, REQ-INFRA-STATIC-3 |
| 정적 검사 | import-linter 레이어 `module → common` 단방향 | SPEC-INFRA-001 REQ-INFRA-STATIC |
| 판정 소비 | `metrics.dqe`·`metrics.mtf`·`metrics.defect_stats`(tests/에서만) | SPEC-METRICS-001 |
| 파라미터 | offset 잔여·gain 범위·C_max·[P] 임계·[B] 동적/다점 = Params/CalibSet | CLAUDE.md 파라미터 정책, SWR 부록 A |

원칙: **정확도 단일 목표, 속도 최적화 금지.** 하드코딩 금지 — 전 상수 Params/CalibSet 주입. EV 판정 수치 미내장(측정=판정 분리).

## 3. 모듈 분해 (modules/ 패키지 레이아웃)

```
modules/
  __init__.py
  offset.py    # SWR-101~104: I₁ = I_raw − O(CalibSet OFFSET); 음수 0 클램프 + 클램프율 리포트;
               #   (Optional) 온도/시간 동적 offset O_ref + ΔO(T) [B]
  gain.py      # SWR-201~204: I₂ = I₁ × G(CalibSet GAIN); 상한 65535 클램프 + 클램프율 리포트;
               #   G ∉ [0.5,2.0] [T] → XFrame DEFECT 마스크 이관; (Optional) 다점 구간 선형 [B]
  defect.py    # SWR-301~304: CalibSet DEFECT 맵 소비 → SWR-303 보간
               #   (단일점 8-이웃 거리가중 / line 직교 1D / cluster edge-directed 4방향 1D);
               #   보간 화소 INTERPOLATION 플래그; cluster > C_max(5×5 [T]) 맵 거부 + 패널 경고
```

`common/`(중복 금지, CORE 소비 — SWR-000-9): 결함 마스크·보간 이웃 연산은 `common/mask_ops`(연결 성분·이웃 선택), 강건 통계(중앙값/MAD, 클램프율)는 `common/robust_stats`를 참조로 사용한다. 두 스텁의 실 구현이 필요한 경우 T1이 유발한 `robust_stats`를 재사용하고, `common/`에만 두며 `modules/`에 중복하지 않는다.

**클램프율·경고 등 진단 부산물의 전달**: XFrame 컨테이너 외 사이드채널 금지(SWR-000-6). 클램프 발생률은 스칼라로 해당 처리 단계의 **이력 체인 엔트리 메타데이터(params/metadata)**에 기록하여 전달한다(마스크 아님, 부가 반환값 아님). 패널 판정 경고(cluster > C_max·맵 거부)도 이력 체인 엔트리 메타에 기록한다. 부가 반환값(튜플) 반환은 계약 검사 위반이다.

합성 팬텀 생성기(기지 왜곡 주입)는 **`tests/` 전용 fixture**로 둔다(SPEC-INFRA-001·METRICS-001의 tests/ 전용 결정 계승). `tests/modules/phantoms/`에 모듈별 생성기(기지값 동반)를 배치하고, `modules/`는 순수 보정만 유지한다.

**defect-map 빌더(metrics 계층 — 결정 1 확정)**: 결함 맵 생성은 `modules/`가 아닌 `metrics/defect_map.py`에 둔다. 빌더는 T1 엔진 `metrics/defect_stats.classify_defects`를 재사용해 dark/flat 스택 → CalibSet(DEFECT) 맵을 생성하며, 레이어링은 `metrics → common` 단방향(생성물 CalibSet은 `common.calibset`)이다. 빌더는 처리 파이프라인 스테이지가 아니라 캘리브레이션 시점 오프라인 생성 도구이며, 처리 모듈 `modules/defect.py`는 이 맵을 소비만 하고 `metrics`를 import하지 않는다(CONTRACT-3 불변).

## 4. EARS 구조 설계 (확정본은 spec.md)

5개 요구 그룹. `[Ubiquitous]`/`[Event]`/`[State]`/`[Optional]`/`[Unwanted]`는 EARS 패턴 표기.

- **REQ-CORR-OFFSET** — O 감산(`[Ubiquitous]`), 음수 클램프+리포트(`[Event]`), 동적 offset [B](`[Optional]`).
- **REQ-CORR-GAIN** — G 정규화(`[Ubiquitous]`), 상한 클램프+리포트(`[Event]`), 범위밖 → DEFECT 이관(`[Unwanted]`), 다점 gain [B](`[Optional]`).
- **REQ-CORR-DEFECT** — 맵 소비 보간(`[Ubiquitous]`), INTERPOLATION 플래그+하류 전달(`[Event]`), 빌더 분류 임계 외부화([S]/[P], `[Ubiquitous]`), cluster > C_max 맵 거부(`[Unwanted]`), 정상 이웃 부족 시 무단 복원 금지(`[Unwanted]`), **defect-map 빌더 생성**(`[Event]`, DEFECT-6), **스키마 위반 맵 거부**(`[Unwanted]`, DEFECT-7), **gain 플래그 화소 단일점 보간 hand-off**(`[Event]`, DEFECT-8).
- **REQ-CORR-CONTRACT** — process 시그니처·불변(`[Ubiquitous]`), 이력 체인(`[Event]`), 의존 방향(`[Ubiquitous]`), 사이드채널 금지 한정(`[Unwanted]`), CalibSet 게이트 거부(`[Unwanted]`), 고정 순서·harness(`[Ubiquitous]`).
- **REQ-CORR-VALIDATE** — 합성 검증(`[State]`), DQE·MTF before/after(`[Event]`), defect 잔존 cluster(`[Event]`, VALIDATE-3 — 처리 모듈 게이트), offset 잔여 훅(`[Event]`), EV 외부 주입(`[Ubiquitous]`), TC skeleton→live(`[Ubiquitous]`), **defect 검출 누락률**(`[Event]`, VALIDATE-7 — 빌더 게이트).

## 5. CalibSet fixture 전략 (모듈별)

`common.calibset.CalibSet` 공통 스키마(panel_id · resolution · valid_from/until · kind · data · provenance)를 사용한다. 게이트가 종류-단계 배선·해상도·패널 ID·유효기간을 검사하므로 fixture는 유효/무효 두 계열을 준비한다.

| 모듈 | CalibSet(kind) data 페이로드 | 무효 fixture(부정 경로) |
|---|---|---|
| offset | `O_map`(float32) + `sigma_d`(픽셀별 표준편차, SWR-104 훅용) | 해상도 불일치 · kind≠OFFSET · 유효기간 밖 |
| gain | 단일점 `G_map`; (Optional) 다점 `anchors`(선량 계단 K개) | 패널 ID 불일치 · kind≠GAIN |
| defect | 결함 `class_map`(단일점/line/cluster 라벨) | cluster > C_max 포함 맵 · 스키마 결손(라벨 누락) |

무효 fixture는 오케스트레이터 진입 게이트(`_calibration_gate`)가 `CalibrationError`로 거부함을 확인하는 데 사용한다(REQ-CORR-CONTRACT-5, acceptance EC-1). 단, defect 맵의 분류 라벨 결손(스키마 위반) 거부는 defect 모듈의 REQ-CORR-DEFECT-7이 담당하고(EC-2b), cluster > C_max 거부는 REQ-CORR-DEFECT-4가 담당한다(EC-2a). defect의 유효 `class_map`은 defect-map 빌더(`metrics/defect_map.py`)가 생성한 맵 또는 수작업 fixture 어느 쪽도 사용할 수 있다.

## 6. 합성 팬텀 전략 (모듈별 기지 왜곡 주입 → 제거 확인)

| 모듈 | 합성 팬텀(기지 왜곡 주입) | 보정 후 검증(기지값) |
|---|---|---|
| offset | 균일 신호 + 기지 다크 offset 패턴(공간 변조) + 잡음 | I₁ = I_raw − O로 offset 제거; 다크 잔여 offset < σ_d 중앙값 10%[T](SWR-104) |
| gain | 기지 gain 비균일(예: heel 모사 저주파 이득) 주입 flat/신호 | I₂ = I₁ × G로 평탄화; 상한 클램프율 리포트; 범위밖 화소 DEFECT 마스크 세팅 |
| defect | 기지 좌표·종류(단일점/line/cluster) 결함 주입 프레임 + CalibSet class_map | SWR-303 보간 후 잔존 가시 cluster 0건; INTERPOLATION 플래그 세팅 |
| defect-map 빌더 | 기지 좌표·종류 결함 주입 dark/flat 스택 | 빌더 생성 맵 대 ground truth 검출 누락률 ≤ EV-103 min(classify_defects 재사용, XDET-TC-003 누락률 다리) |
| offset+gain (통합) | 기지 MTF(해석적 slanted-edge)·기지 잡음 + offset/gain 왜곡 | before/after DQE(3선량)·MTF@Nyquist 유지율(metrics 엔진, XDET-TC-001/002) |

원칙: 팬텀 생성기는 `tests/modules/phantoms/`에 두고 기지값(주입 좌표·패턴·해석적 MTF)을 함께 반환. 허용오차·EV 임계는 [T]/외부 주입(하드코딩 금지). before/after 판정은 `tests/`에서 `metrics.dqe.compute_dqe`·`metrics.mtf.compute_mtf`/`mtf_value_at`·`metrics.defect_stats.classify_defects`를 소비한다(모듈은 metrics import 금지 — CONTRACT-3).

## 7. 파이프라인 통합

- 세 모듈의 `process`를 오케스트레이터 registry에 `"offset"`·`"gain"`·`"defect"` 스테이지로 등록한다(`pipeline/orchestrator.py` `run_pipeline(registry=...)`).
- `PipelineDefinition(stages=("offset","gain","defect"))`는 CANONICAL_ORDER 부분수열이므로 순서 계약을 만족한다(REQ-CORR-CONTRACT-6).
- 진입 게이트는 각 스테이지 CalibSet의 존재·해상도·패널 ID 상호일치·종류-단계 배선·유효기간을 검사한다. 세 모듈은 게이트 통과 후에만 실행된다(REQ-CORR-CONTRACT-5).
- 검증 모드(validation_mode) 활성 시 오케스트레이터가 단계별 중간 XFrame을 보존하므로(REQ-INFRA-DATA-5), offset/gain/defect 중간 산출을 before/after 판정 입력으로 재사용할 수 있다.

## 8. 리스크 분석 (요약)

| 리스크 | 완화 | 우선순위 |
|---|---|---|
| defect 검출/맵 생성 범위 모호(단일 프레임 계약 vs 스택 검출) | 결정 1 확정(v0.1.1): 맵 생성은 `metrics/defect_map.py` 빌더(classify_defects 재사용)로 T2 포함, 처리 모듈은 보간 전용. 빌더 metrics→common 레이어링 유지 | High |
| SWR-203 gain 플래그 화소와 맵 결함의 보간 통합 모호 | 결정 4 확정(v0.1.1): gain 범위밖 화소 I₁ 보존+DEFECT 플래그, defect가 분류 없는 화소를 단일점 보간(DEFECT-8) | High |
| 하드코딩 유입(gain 범위·C_max·[P] 임계·offset 잔여) | Params/CalibSet 주입 필수화, [S]/[B]/[T]/[P] 등급 주석 규약 | High |
| edge-directed cluster 보간 복잡도(4방향 분산 최소) | 정확도 우선, `common/mask_ops` 재사용, 합성 기지값 재현 | Medium |
| gain 배율 후 노이즈 모델 미갱신 → 하류 VST 영향 | 재추정 안 함(SWR-701/T5 소관) 명시 — spec 「결정 필요」 2 | Medium |
| 진단 부산물(클램프율·경고) 사이드채널 유입 | 이력 체인 엔트리 메타(스칼라) 전달로 확정, 부가 반환값 금지(계약 검사) | Medium |
| [B] 미확정(동적 offset·다점 gain) 조기 확정 부담 | Optional 경로 + [P]/정적 기본값, [B] 값 외부화·미주입 | Medium |
| EV 판정 임계 엔진/모듈 내장(측정=판정 결합) | 판정 수치 외부 주입, tests/에서만 비교(VALIDATE-5) | Medium |
| DQE 공식 문서 상충(프로토콜 §1.4) | T1 엔진 IEC 형태 재사용, spec 「결정 필요」 5 참조 | Low |

## 9. 마일스톤 (우선순위 기반, 시간 추정 없음)

- **Priority High — M0 결정 확정(완료)**: spec 「결정 필요/확인 사항」 1(defect 맵 생성 = 빌더로 T2 포함)·4(gain 플래그 화소 = 단일점 보간)를 v0.1.1에서 확정. defect 모듈 입력 계약 고정(빌더 생성 맵 + gain 플래그 화소). 다른 마일스톤의 전제.
- **Priority High — M1 OFFSET**: `modules/offset.py` — O 감산·음수 클램프+리포트(이력 체인 메타 스칼라)·이력 갱신. offset CalibSet fixture + 합성 다크 팬텀. XDET-TC-001 입력부 일부.
- **Priority High — M2 GAIN**: `modules/gain.py` — G 정규화·상한 클램프+리포트·범위밖 DEFECT 이관(출력값 I₁ 보존, 무효 G 미적용 — 결정 4). gain CalibSet fixture + 합성 비균일 팬텀. M1과 부분 독립(구현), 런타임 순서는 offset 뒤.
- **Priority Medium — M3 DEFECT**: `modules/defect.py` — 맵 소비 SWR-303 보간·INTERPOLATION 플래그·cluster C_max 거부·스키마 위반 맵 거부(DEFECT-7)·gain 플래그 화소 단일점 보간(DEFECT-8). defect CalibSet fixture + 합성 결함 팬텀. M0 확정 후 착수.
- **Priority Medium — M5 DEFECT-MAP 빌더**: `metrics/defect_map.py` — T1 엔진 `classify_defects` 재사용, dark/flat 스택 → CalibSet(DEFECT) 맵 생성(DEFECT-6). 검출 누락률 판정(VALIDATE-7, ground truth 대조). metrics→common 레이어링. M3와 병행 가능(별개 계층), M4의 누락률 다리 전제.
- **Priority High — M4 VALIDATE**: 오케스트레이터 registry 통합, before/after 판정(metrics 엔진 소비, tests/), XDET-TC-001·002·003 skeleton→live 전환(XDET-TC-003은 잔존 cluster 다리 + 빌더 누락률 다리), SWR-104 잔여 offset 훅. M1~M3·M5 완료 후.
- 순서 원칙: M0(결정, 완료) → M1·M2(구현 병행 가능) → M3(defect 모듈)·M5(defect-map 빌더, 병행) → M4(통합·판정). harness 단독 시험(XDET-TC-000)은 각 모듈 착수와 동반.

## 10. 검증 전략 — 합성 팬텀 + before/after 판정

- **fixture 구성**: 모듈별 CalibSet(유효/무효) + 합성 팬텀(기지 왜곡 동반, `tests/modules/phantoms/`).
- **판정**: (a) 단위 — 각 모듈이 주입 왜곡을 제거(offset 잔여·gain 평탄화·defect 잔존 cluster 0); (b) 통합 — before/after DQE·MTF·defect 통계를 metrics 엔진으로 산출해 EV min 외부 임계와 비교(tests/).
- **부정/경계 케이스**: CalibSet 부재/불일치 게이트 거부(EC-1), cluster > C_max 맵 거부·스키마 결손(EC-2), 정상 이웃 부족 무단 복원 금지(EC-3), 사이드채널·의존 위반(EC-4).
- **계약 검사**: `common.contract.check_process_contract`/`run_harness`로 시그니처·반환형·전체 XFrame 비교(XDET-TC-000); import-linter로 `module → common` 단방향·모듈 간/`metrics`/`pipeline` import 금지.
- **DoD**: 3개 보정 모듈 합성 왜곡 제거 PASS + 부정/경계 케이스 정상 거부·경고 + XDET-TC-001~003 실동작 전환·EV-101/102/103 min 대비 통과 + 계약/의존 위반 0건.
- acceptance.md에 Given-When-Then 시나리오(모듈별)·Optional 조건부 AC·엣지 케이스·품질 게이트를 상세화.
