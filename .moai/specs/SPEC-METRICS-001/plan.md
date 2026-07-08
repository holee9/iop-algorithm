---
id: SPEC-METRICS-001
title: T1 지표 산출 엔진 (MTF·NPS/NNPS·DQE·lag·bad-pixel·SNRn·duplex-wire)
version: 0.1.1
status: draft
created: 2026-07-09
updated: 2026-07-09
author: drake.lee
priority: high
issue_number: 2
---

# SPEC-METRICS-001 구현 계획 (초안) — T1 지표 산출 엔진

> 상태: **draft** (run 단계 착수 전까지 유지). EARS 확정본은 [spec.md](./spec.md), 인수 기준은 [acceptance.md](./acceptance.md). 선행 계약은 [SPEC-INFRA-001](../SPEC-INFRA-001/spec.md).

## 1. 개요

XDET P1의 두 번째 작업 T1. `docs/XDET_measurement_protocol_v1.0.md`를 구현 사양 단일 출처로 하여, EVAL v1.1 지표의 측정 절차를 자동화하는 지표 산출 엔진(`metrics/`)을 구현한다. 엔진은 T0의 XFrame을 읽기 전용으로 소비하는 **순수 측정 계층**이며 처리 모듈이 아니다. 완료 정의: **합성 팬텀 입력으로 기지값 재현** — 실측 도착 전 기지값 주입 합성 데이터로 엔진 자체를 검증(XDET-TC-001~005 · XDET-TC-018 판정 엔진의 산출부).

## 2. 기술 스택

| 항목 | 선택 | 근거 |
|---|---|---|
| 언어/런타임 | Python 3.11+ | tech.md |
| 수치 연산 | numpy, scipy (float 골든 모델) | tech.md, 측정프로토콜 |
| 시험 프레임워크 | pytest + CI (XDET-TC-001~005·018 등록) | TestSpec, SWR-000-11 |
| 입력 계약 | XFrame(불변) 소비 — 처리 모듈 아님 | SPEC-INFRA-001 REQ-INFRA-DATA |
| 공용 컴포넌트 | `common/fft_psd`·`robust_stats`·`histogram_fov` 참조(첫 소비자) | SWR-000-9, REQ-INFRA-STATIC-3 |
| 정적 검사 | import-linter 레이어 `metrics → common` 단방향 | SPEC-INFRA-001 REQ-INFRA-STATIC |
| 파라미터 | q·Ka·XN·88.6µm·허용오차·결함 임계 = Params/CalibSet 외부화 | CLAUDE.md 파라미터 정책 |

원칙: **정확도 단일 목표, 속도 최적화 금지.** 하드코딩 금지 — 전 상수 Params/CalibSet 주입. EV 판정 수치 미내장(측정=판정 분리).

## 3. 모듈 분해 (metrics/ 패키지 레이아웃)

```
metrics/
  __init__.py
  result.py         # MetricResult 컨테이너: 값(들) + 산출 조건 메타(선질·선량·온도·필터·보정상태·ROI·params_hash·calibset_id) — CORE-6
  mtf.py            # edge method: 자동 각도추정 → oversampled ESF → LSF(미분+창함수) → FFT → presampled MTF (MTF 그룹)
  nps.py            # 256×256 ROI 앙상블 → detrend → 2D FFT 평균 → 1D 축추출; NNPS 정규화; 라인노이즈 스펙트럼 옵션 (NPS 그룹)
  dqe.py            # DQE(f) = MTF²·q·Ka / NPS  — mtf.py + nps.py 산출물 소비 (NPS 그룹)
  lag.py            # ASTM E2597 first-frame lag %; ghost CNR (필수) (LAG 그룹)
  defect_stats.py   # ASTM E2597 7종 분류(dark/flat 스택 통계); 검출 누락률 (DEFECT 그룹)
  ndt.py            # duplex-wire 20% dip → SRb_image; SNRn = SNR × 88.6/SRb (NDT 그룹)
```

`common/`(첫 소비자로서 실 구현을 유발하나 코드는 common/에 위치, metrics/에 중복 금지 — CORE-8):
- `common/fft_psd.py` — nps/dqe(2D FFT·PSD 앙상블), nps 라인노이즈 스펙트럼.
- `common/robust_stats.py` — mtf(LSF 강건 처리), defect_stats(median/MAD 기반 6× median · 임계 통계), ndt(균일 영역 SNR).
- `common/histogram_fov.py` — ndt(자동 균일 영역 검출), defect_stats(분포 기반 분류 보조).

합성 팬텀 생성기(기지값 주입)는 **`tests/` 전용 fixture**로 둔다(SPEC-INFRA-001의 레퍼런스 fixture는 tests/ 전용 결정 계승 — 검증 도구는 프로덕션 트리 밖). `tests/metrics/phantoms/`에 지표별 생성기 배치, `metrics/`는 순수 산출만 유지.

## 4. EARS 구조 설계 (확정본은 spec.md)

6개 요구 그룹. `[Ubiquitous]`/`[Event]`/`[State]`/`[Optional]`/`[Unwanted]`는 EARS 패턴 표기.

- **REQ-METRICS-CORE** — XFrame 소비·불변, 부작용 금지(`[Unwanted]`), `metrics → common` 단방향, 상수 외부화, EV 판정 분리, 산출 메타 첨부(`[Event]`), 합성 검증(`[State]`), common 중복 금지.
- **REQ-METRICS-MTF** — edge method 산출, 자동 각도추정(`[Event]`), 각도 이상 거부(`[Unwanted]`), 기지 MTF 재현(`[State]`), 수평·수직 2방향(`[Optional]`).
- **REQ-METRICS-NPS** — 256×256 ROI 앙상블 NPS, NNPS 정규화, DQE 조성, 3선량 산출(`[Event]`), 기지 잡음 재현(`[State]`), ROI 경계·0-나눗셈 거부(`[Unwanted]`), 라인노이즈 스펙트럼(`[Optional]`).
- **REQ-METRICS-LAG** — E2597 first-frame lag, 시퀀스 입력 산출(`[Event]`), 기지 IRF 재현(`[State]`), 포화 전제 위반 경고(`[Unwanted]`), ghost CNR 산출(`[Event]` — 필수).
- **REQ-METRICS-DEFECT** — E2597 7종 분류, 스택 입력 산출(`[Event]`), 6× median [S]/임계 [P] 외부화, 기지 결함 재현·누락률(`[State]`), 매수 미달 거부(`[Unwanted]`).
- **REQ-METRICS-NDT** — duplex 20% dip → SRb, SNRn 정규화, 균일영역 입력 산출(`[Event]`), dip 미검출 명시 실패(`[Unwanted]`), 기지 dip/SNR 재현(`[State]`).

## 5. 합성 팬텀 fixture 전략 (지표별 기지값 재현)

각 지표에 대해 **해석적으로 기지값을 아는 합성 입력**을 생성하고, 엔진 산출이 그 기지값을 허용오차([T] 파라미터) 내로 재현하는지로 정확도를 확인한다.

| 지표 | 합성 팬텀 (기지값 주입) | 재현 대상 (기지값) |
|---|---|---|
| MTF | 이상 slanted edge: 해석적 MTF(예: 알려진 Gaussian blur → 해석적 MTF, 또는 sinc 형상)를 1.5~3° 경사·서브픽셀 위치로 렌더 | presampled MTF(f), 특히 MTF@Nyquist 3.57 lp/mm |
| NPS/NNPS | 백색 잡음(평탄 NPS, 주입 분산) + 유색 잡음(주입 상관 커널 → 해석적 NPS 형상) 균일 프레임 다수 매 | NPS(f) 크기·형상, NNPS(대신호 정규화) |
| DQE | 기지 MTF 팬텀 + 기지 NPS 팬텀 + 주입 q·Ka → 해석적 DQE(f) | DQE(f), peak DQE, DQE@1·2 lp/mm |
| first-frame lag | 지수합 IRF(M=3~4, 주입 계수) 컨볼루션 프레임 시퀀스 → 해석적 first-frame lag % | first-frame lag % |
| bad-pixel | 기지 좌표·E2597 종류(dead/over-under/noisy/lag/non-uniform)를 주입한 합성 dark/flat 스택 | 7종 분류 맵, 종류별 분율, 검출 누락률 |
| SNRn + duplex | 기지 dip 위치의 합성 duplex-wire 프로파일(20% dip) + 기지 SNR 균일 영역(주입 평균·표준편차) | SRb_image, SNR, SNRn(= SNR×88.6/SRb) |

원칙: 팬텀 생성기는 `tests/metrics/phantoms/`에 두고 기지값을 함께 반환. 허용오차는 지표별 [T] 파라미터로 Params/설정에서 주입(하드코딩 금지). 실측 GDS 도착 시 동일 산출 함수에 실 영상을 입력해 baseline([B]) 치환(엔진 재구현 불필요).

## 6. 리스크 분석 (요약)

| 리스크 | 완화 | 우선순위 |
|---|---|---|
| 실측 부재 상태에서 정확도 확신 곤란 | 해석적 기지값 합성 팬텀으로 왕복 검증(재현 오차 [T] 게이트) | High |
| edge 각도 추정 실패(0°/90° 근처) | 각도 범위 검사 + 신뢰 불가 거부(MTF-3), 서브픽셀 위치 검증 | High |
| DQE 0-나눗셈(NPS→0) | 분모 안정성 가드 + 무효 표시(NPS-7) | High |
| 상수 하드코딩 유입(q·Ka·88.6·임계) | Params/CalibSet 주입 필수화, [S]/[B]/[T]/[P] 등급 주석 규약 | High |
| EV 판정 임계 엔진 내장(측정=판정 결합) | 판정 수치 외부 주입, 엔진은 값만 산출(CORE-5) | High |
| common/ 스텁 시그니처 조기 확정 부담 | metrics 소비 요건에 맞춰 최소 시그니처만 확정, 범용 최적화 이연 | Medium |
| duplex 20% dip 미검출 시 무단 추정 | 명시 실패 반환(NDT-4), 추정 금지 | Medium |
| 범위 확장(XDET-TC-006~009, CSa/SMTR 유입) | Exclusions 고정 — 명명 7개 지표만, 나머지 이연 | Medium |

## 7. 마일스톤 (우선순위 기반, 시간 추정 없음)

- **Priority High — M1 CORE**: `MetricResult` 컨테이너(값 + 산출 조건 메타 + params_hash), 합성 팬텀 harness 골격, `common/` 첫 실 구현(fft_psd·robust_stats 최소), import-linter `metrics → common` 계약. 모든 지표의 전제.
- **Priority High — M2 MTF · M3 NPS/NNPS**: 두 지표는 독립 병행 가능. 각기 합성 팬텀 기지값 재현으로 DoD 부분 달성(XDET-TC-002 · XDET-TC-001 입력부).
- **Priority High — M4 DQE**: M2·M3 완료 후 조성(DQE = MTF²·q·Ka/NPS). XDET-TC-001 판정부 완성.
- **Priority Medium — M5 DEFECT**: E2597 7종 분류. M1 이후 독립 병행(XDET-TC-003 판정부).
- **Priority Medium — M6 LAG**: 합성 IRF 재현 + ghost CNR 산출(XDET-TC-004·XDET-TC-005, 둘 다 필수).
- **Priority Medium — M7 NDT**: duplex 20% dip → SRb, SNRn 정규화(XDET-TC-018).
- 순서 원칙: M1(계약·harness·common 실구현) 확정 후 지표 착수. MTF·NPS·DEFECT는 상호 독립 병행, DQE는 MTF·NPS 의존.

## 8. 검증 전략 — 합성 팬텀 기지값 재현

- **fixture 구성**: 지표별 합성 팬텀 + 함께 반환된 기지값(`tests/metrics/phantoms/`).
- **판정**: 각 지표 산출 함수 출력이 기지값을 지표별 허용오차([T] 파라미터) 내로 재현.
- **경계/부정 케이스**: MTF 각도 0°/90°·범위 밖, NPS ROI 경계·균일영역 부족, DQE NPS→0, DEFECT 스택 매수 미달·전영역 dead, LAG 포화 전제 위반, NDT dip 미검출.
- **메타 첨부**: 모든 산출 결과에 산출 조건 메타(선질·선량·온도·필터·보정상태·ROI·params_hash·calibset_id) 결정론적 첨부 확인(CORE-6).
- **DoD**: 6개 지표 그룹 합성 팬텀 재현 통과 + 경계/부정 케이스 정상 거부/경고 + XDET-TC-001~005·XDET-TC-018 pytest 등록·통과.
- acceptance.md에 Given-When-Then 시나리오(지표별)·엣지 케이스·품질 게이트를 상세화.
