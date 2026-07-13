---
id: SPEC-XGUI-GRID
version: 0.5.1
status: planned
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
priority: medium
issue_number: 58
labels: [xgui, grid, virtual-grid, scatter, wpf]
---

# SPEC-XGUI-GRID — 구현 계획

## 0. 구현 착수 전제

이 계획은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 마스터 plan M0.5를 상속한다. 사용자 승인 기록, 기준선 동결, `implementation_authorized=true`가 모두 존재하기 전에는 아래 마일스톤의 소스·XAML·테스트·패키지 변경을 시작하지 않는다. 내부 감사 통과나 기술적 구현 가능성만으로 이 전제를 충족했다고 보지 않는다.

진입 증거는 승인된 v0.5.1 기준선, 요구사항-인수-TC 추적 차이 0, 미결정 임계 0, 현재 worktree/commit을 가리키는 최종 감사 기록이다. 규범 변경이 발생하면 작업을 멈추고 기준선 재승인을 수행한다.

구현 루트는 `apps/xdet-console/`이다.

## 기술 방향

Grid와 Virtual Grid를 같은 탭에서 개별 또는 순서가 표시된 부분수열로 실행한다. 주파수 분석, notch, scatter kernel과 scatter map은 Python 엔진이 산출한다.

## 마일스톤

### M1 — 입력과 Builder (High)

- grid phantom과 Params manifest를 로드한다.
- `build_scatter_kernel`을 유일한 kernel builder로 호출한다.
- 8 cm/100 kV는 알려진 시험 preset으로 제공하되 알고리즘 기본값으로 하드코딩하지 않는다.

### M2 — 개별 뷰 (High)

- Grid는 spectrum/notch와 folded-harmonic marker를 표시한다.
- Virtual Grid는 estimated scatter map과 보정 결과를 표시한다.
- 모든 곡선·맵은 엔진 반환 DTO에서만 가져온다.

### M3 — 조합·저장 (Medium)

- grid→virtual_grid와 저-ratio residual-scatter 조합을 명시 라벨과 함께 허용한다.
- 각 중간 프레임의 stage sequence를 표시한다.
- raw/JSON/mask를 저장한다.

### M4 — 검증 (High)

- `XDET-TC-136~143` 전체로 analyze/notch/process, scatter estimate/process, 두 kernel builder, 조합·오류·evidence를 검증한다.

### M-COVERAGE — grid diagnostics와 scatter 2개 builder

- physical grid service는 analyze/notch/process를, virtual-grid service는 estimate_scatter/process를 실제 호출한다.
- scatter calibration UI는 parametric과 measured sample-fit 두 경로를 모두 제공한다.
- XDET-TC-136~143에 analyze, process, virtual grid, 두 builder, diagnostics, export, guard를 배정한다.

## 변경 대상

- `Xdet.Engine.Contract`: grid/vgrid Params·analysis·scatter DTO
- `Xdet.Engine.PythonNet`: grid, virtual_grid, scatter-kernel 위임
- `Xdet.Console.App`: Grid 탭의 frequency/spatial 전환 뷰
- `Xdet.Engine.Tests`: `XDET-TC-136~143`

## 완료 게이트

- [ ] 시험 preset과 알고리즘 기본값이 구별된다.
- [ ] folded harmonic이 명시적으로 표시된다.
- [ ] grid+vgrid 조합의 목적이 라벨로 설명된다.
- [ ] C-09/C-20/QUARANTINE이 통과한다.
