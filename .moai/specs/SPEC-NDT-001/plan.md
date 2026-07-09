---
id: SPEC-NDT-001
title: T9 WP10 NDT (실시간 SNRn 적산 · IQI 자동 판독 · 두께 보정)
version: 0.1.1
status: draft
created: 2026-07-09
updated: 2026-07-09
author: drake.lee
priority: high
issue_number: 10
labels: [T9, WP10, NDT]
---

# SPEC-NDT-001 구현 계획 (초안) — T9 WP10 NDT

> 상태: **draft** (run 단계 착수 전까지 유지). EARS 확정본은 [spec.md](./spec.md), 인수 기준은 [acceptance.md](./acceptance.md). 선행 계약은 [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md)·[SPEC-METRICS-001](../SPEC-METRICS-001/spec.md).

## 1. 개요

XDET P1의 열 번째 작업 T9. NDT 검사 성적 산출 능력 WP10(SWR-1201~1204, FR-N001~N003)을 구현한다. 세 축 — (1) Welford 온라인 누적 기반 **실시간 SNRn 적산** + 목표 도달 취득 종료 신호 + shot별 자동 로그(SWR-1201), (2) duplex SRb 재사용 + 단선 IQI 자동 판독 + **Class A/B 리포트**(SWR-1202 재사용 + SWR-1204), (3) **두께 보정**(저주파 프로파일 감산 · 고역 결함 대역 보존, SWR-1203). **T9는 측정·리포트 계층이며 픽셀 보정 처리 스테이지가 아니다** — `metrics/ndt.py` 확장 + `common/robust_stats.py`(Welford) 확장으로 배치하고 T0 오케스트레이터 표면을 변경하지 않는다(결정 1). 완료 정의: **합성 팬텀으로 SNRn/SRb/IQI 자동 판독 정확도(XDET-TC-018) + 두께 보정 SRb 보호(XDET-TC-019)를 선검증**.

## 2. 기술 스택

| 항목 | 선택 | 근거 |
|---|---|---|
| 언어/런타임 | Python 3.11+ | tech.md |
| 수치 연산 | numpy, scipy (float 골든 모델; morphological opening/Gaussian, 온라인 누적) | tech.md, 측정프로토콜 |
| 시험 프레임워크 | pytest + CI (XDET-TC-018/019 등록) | TestSpec, SWR-000-11 |
| 입력 계약 | XFrame(불변) 읽기 전용 소비 — 처리 모듈 아님 | SPEC-INFRA-001, SPEC-METRICS-001 |
| 공용 컴포넌트 | `common/robust_stats`(Welford 첫 소비자) 참조; `common/histogram_fov`(자동 균일 영역) | SWR-000-9 |
| T1 재사용 | `metrics/ndt`(read_duplex_srb·compute_snr·compute_snrn), `metrics/mtf`(SRb 보호), `metrics/result`(MetricResult·MetricReadError·require_param) | SPEC-METRICS-001 |
| 정적 검사 | import-linter `metrics → common` 단방향 (`modules/`·`pipeline/` 금지) | SPEC-INFRA-001 REQ-INFRA-STATIC |
| 파라미터 | 88.6µm[S]·20% dip[S]·두께 스케일[T]·SNRn 목표/Class[S]/[P]·허용오차[T] = Params 외부화 | CLAUDE.md 파라미터 정책 |

원칙: **정확도 단일 목표, 속도 최적화 금지.** 하드코딩 금지. EV 판정 수치 미내장(측정=판정 분리). T0 표면 불변(결정 1).

### 두께 보정 기법 선택 (`thickness_method`, REQ-NDT-THICK-1 HOW)

Params `thickness_method`(문자열, 기본값 `"morphological_opening"`)로 두 기법 중 단일 경로를 결정론적으로 선택한다(SWR-1203 이접 조항의 단일 소스화):
- `"morphological_opening"`(기본) — 대구경 원형 structuring element(반경 = Params `thickness_scale_px` [T])로 grayscale opening, 저주파 두께 프로파일을 산출. 결함(고역, 좁은 구조)은 opening 반경보다 작아 보존됨.
- `"gaussian"` — 대형 Gaussian σ(= Params `thickness_scale_px` [T])로 저역 통과, 동일 프로파일을 산출. opening 대비 부드러운 profile이나 경계에서 링잉 가능.

두 경로 모두 출력은 "저주파 두께 프로파일"(감산 대상)이며, 나머지 처리(감산·고역 보존 검증)는 기법 무관 동일 경로. 알 수 없는 `thickness_method` 값은 명시 오류(REQ-NDT-CONTRACT-3 하드코딩 금지 정책과 별개로, 유효값 검증은 구현 방어 규칙).

## 3. 모듈 분해 (metrics/ · common/ 확장 — 신규 파일 없이 T1 확장 우선)

```
common/
  robust_stats.py   # [확장] WelfordAccumulator(온라인 count·mean·M2) + online_mean_var
                    #  — temporal_mean_std(배치)의 증분 형제, SWR-000-9 첫 소비자 정의 (결정 2)
metrics/
  ndt.py            # [확장] 기존: read_duplex_srb(SWR-1202)·compute_snr·compute_snrn(SWR-1201 수식)
                    #  신규: SNRnAccumulator(Welford 소비 → 실시간 SNRn·종료 신호·shot 로그, SWR-1201)
                    #        correct_thickness(저주파 프로파일 감산·고역 보존, SWR-1203)
                    #        read_single_wire_iqi(최소 가시 wire, SWR-1204)
                    #        build_iqi_report(Class A/B 합부·검사 성적, SWR-1204)
```

배치 원칙(결정 1): T9는 T0 표면(`CANONICAL_ORDER`·`CalibKind`·`_KIND_BY_STAGE`)을 변경하지 않는다. 신규 처리 스테이지·신규 CalibKind 없음. 두께 보정은 metrics-로컬 평탄화 연산(입력 XFrame 불변, 평탄화 결과 반환). 합성 팬텀 생성기(기지값 주입)는 **`tests/` 전용 fixture**(`tests/metrics/phantoms/` — SPEC-INFRA-001·METRICS-001 선례, 검증 도구는 프로덕션 트리 밖). CSa 산출·SRb 보호 판정은 T1 `metrics/mtf`를 tests/에서 소비.

## 4. EARS 구조 설계 (확정본은 spec.md)

5개 요구 그룹. `[Ubiquitous]`/`[Event]`/`[State]`/`[Unwanted]`는 EARS 패턴 표기.

- **REQ-NDT-ACCUM** (SWR-1201) — Welford 온라인 누적(`[Ubiquitous]`), 프레임 투입 시 실행 SNR·SNRn 갱신(`[Event]`), 목표 도달 취득 종료 신호(`[Event]`), shot별 SNRn·SRb 자동 로그(`[Event]`), Welford≡배치 등가(`[State]`), ROI/zero-noise 거부(`[Unwanted]`).
- **REQ-NDT-THICK** (SWR-1203) — 저주파 프로파일 감산 평탄화(`[Event]`), 고역 결함 대역 보존(`[Ubiquitous]`), 구배 부재/스케일 초과 시 무변화 통과+경고(`[Unwanted]`).
- **REQ-NDT-IQI** (SWR-1202 재사용 + SWR-1204) — duplex SRb 재사용(`[Ubiquitous]`), 단선 wire 최소 가시 판정(`[Event]`), Class A/B 리포트 자동 산출(`[Event]`), 기지 IQI 재현(`[State]`).
- **REQ-NDT-CONTRACT** (SWR-000-6~9) — metrics→common 단방향·XFrame 읽기 전용(`[Ubiquitous]`), T0 표면 불변(`[Ubiquitous]`), 상수 외부화(`[Ubiquitous]`), EV 판정 분리(`[Ubiquitous]`), Welford 공용 컴포넌트 중복 금지(`[Ubiquitous]`).
- **REQ-NDT-VALIDATE** (XDET-TC-018/019) — SNRn/SRb/IQI 정확도 재현(`[State]`, EV-301), 두께 보정 SRb 보호 + CSa proxy(`[State]`, EV-102/303), SMTR/관찰자 PARTIAL 이연(`[Ubiquitous]`).

## 5. 합성 팬텀 fixture 전략 (기지값 재현)

| 대상 | 합성 팬텀 (기지값 주입) | 재현 대상 (기지값) |
|---|---|---|
| Welford 적산 | 주입 평균·분산의 균일 프레임 시퀀스(프레임 수 N) | 실행 평균/분산 ≡ 배치 `temporal_mean_std`; 실시간 SNRn(f당); 목표 도달 프레임 인덱스 |
| SNRn 정규화 | 기지 SNR 균일 영역 + 기지 dip duplex 프로파일(T1 재사용) | SNRn = SNR × 88.6/SRb |
| 두께 보정 | 기지 저주파 두께 구배(step wedge) + 주입 고역 결함 신호 | 구배 제거 + 고역 결함 진폭·SRb 보존(EV-102 min 대비) + CSa proxy |
| 단선 IQI | 기지 최소 가시 wire를 담은 단선 IQI 프로파일 + 기지 SNRn | 최소 가시 wire 번호, Class A/B 합부 |

원칙: 팬텀 생성기는 `tests/metrics/phantoms/`에 두고 기지값 함께 반환. 허용오차는 [T] 파라미터로 주입(하드코딩 금지). 실측 GDS(GDS-NDT/step wedge) 도착 시 동일 산출 함수에 실 영상 입력해 baseline([B]) 치환(엔진 재구현 불필요).

## 6. 리스크 분석 (요약)

| 리스크 | 완화 | 우선순위 |
|---|---|---|
| 배치 vs 스테이지 오배치(결정 1 오판) | SWR 텍스트·`CANONICAL_ORDER` 코드 대조로 metrics 계층 확정; 하류 표시 요구 발생 시에만 스테이지 신설(run-blocking) 재검토 | High |
| Welford 온라인 vs 배치 수치 불일치 | `temporal_mean_std` 등가 게이트([T] 허용오차)로 왕복 검증; 정확도 목적(속도 아님) | High |
| 두께 보정이 고역 결함/SRb 손상 | 저주파만 감산(스케일 [T]) + SRb 보호 EV-102 min 결정론적 게이트(T1 metrics/mtf) | High |
| 상수 하드코딩 유입(88.6·20% dip·스케일·Class 임계) | Params 주입 필수화, [S]/[T]/[P] 등급 주석, T1 P_SRB_NORM_UM/P_DIP_THRESHOLD 재사용 | High |
| EV·Class 임계 엔진 내장(측정=판정 결합) | EV-301/303/102 외부 주입; Class 임계는 리포트 산출용 Params, 시험 합격선은 외부 | High |
| SMTR/CSa 범위 확대(EV-303 유입) | SRb 보호+CSa proxy를 하드 게이트로, SMTR 완전 특성화 PARTIAL 이연(결정 4) | Medium |
| duplex SRb 재구현(중복) | T1 read_duplex_srb 재사용, SWR-000-9 중복 금지(결정 5) | Medium |
| 취득 종료 "신호" 해석 과확장 | 반환 결정값으로 한정, 하드웨어 취득 제어 Exclusions 명시 | Medium |

## 7. 마일스톤 (우선순위 기반, 시간 추정 없음)

- **Priority High — M1 CONTRACT + Welford 공용 컴포넌트**: `common/robust_stats.WelfordAccumulator`(온라인 count·mean·M2) 첫 실 구현 + `temporal_mean_std` 등가 게이트, `metrics → common` import-linter 계약, T0 표면 불변 확인(CANONICAL_ORDER 무변경). 모든 후속의 전제(결정 1·2).
- **Priority High — M2 ACCUM**: `SNRnAccumulator`(Welford 소비 → 실시간 SNR·SNRn=SNR×88.6/SRb, T1 compute_snrn 재사용) + 목표 도달 취득 종료 신호 + shot별 SNRn·SRb 자동 로그. Welford 등가·SNRn 재현으로 XDET-TC-018 SNRn 부분 달성.
- **Priority High — M3 IQI 리포트**: duplex SRb 재사용(read_duplex_srb) + 단선 IQI 최소 가시 wire 판독 + Class A/B `build_iqi_report`. XDET-TC-018 IQI 판정부 완성(EV-301 min).
- **Priority Medium — M4 THICK**: `correct_thickness`(저주파 프로파일 감산·고역 보존) + SRb 보호 검증(T1 metrics/mtf 소비) + CSa proxy. XDET-TC-019 판정부(EV-303·EV-102 min).
- **Priority Medium — M5 VALIDATE 전환**: XDET-TC-018/019 pytest skeleton(skip) → 실동작 케이스 전환. SMTR/관찰자 PARTIAL 이연 문서화.
- 순서 원칙: M1(공용 Welford·계약) 확정 후 착수. M2·M4는 M1 이후 병행 가능(ACCUM은 시퀀스, THICK은 단일 프레임 — 독립). M3은 M2(SNRn) + T1 duplex SRb 의존.

## 8. 검증 전략 — 합성 팬텀 기지값 재현

- **fixture 구성**: Welford 시퀀스·SNRn 균일영역·두께 step-wedge·단선 IQI 팬텀 + 기지값(`tests/metrics/phantoms/`).
- **하드 DoD 판정**: (a) Welford 온라인 ≡ 배치 `temporal_mean_std`([T] 등가), (b) SNRn/SRb/최소 가시 wire/Class A/B 기지값 재현([T], EV-301 min), (c) 두께 보정 후 SRb 열화 ≤ EV-102 min(≤10%) · MTF@Nyquist 유지율 ≥ EV-102 min(≥90%) 결정론적 이진(T1 metrics/mtf) + CSa proxy(EV-303).
- **경계/부정 케이스**: ACCUM ROI 경계·zero-noise 거부, THICK 구배 부재·스케일 초과 무변화 통과+경고, IQI duplex dip 미검출 명시 실패(T1 승계).
- **PARTIAL**: SMTR 완전 특성화·관찰자(EV-303 고객 스펙·EV-204)는 인허가 이연.
- **DoD**: ACCUM/THICK/IQI 합성 팬텀 재현 통과 + 경계/부정 케이스 정상 거부/경고 + XDET-TC-018/019 pytest 등록·통과 + T0 표면 불변 확인.
- acceptance.md에 Given-When-Then 시나리오·엣지 케이스·품질 게이트 상세화.
