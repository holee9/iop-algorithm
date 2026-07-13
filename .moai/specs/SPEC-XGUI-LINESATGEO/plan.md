---
id: SPEC-XGUI-LINESATGEO
version: 0.5.1
status: planned
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
priority: high
issue_number: 58
labels: [xgui, line-noise, saturation, geometry, wpf]
---

# SPEC-XGUI-LINESATGEO — 구현 계획

## 0. 구현 착수 전제

이 계획은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 마스터 plan M0.5를 상속한다. 사용자 승인 기록, 기준선 동결, `implementation_authorized=true`가 모두 존재하기 전에는 아래 마일스톤의 소스·XAML·테스트·패키지 변경을 시작하지 않는다. 내부 감사 통과나 기술적 구현 가능성만으로 이 전제를 충족했다고 보지 않는다.

진입 증거는 승인된 v0.5.1 기준선, 요구사항-인수-TC 추적 차이 0, 미결정 임계 0, 현재 worktree/commit을 가리키는 최종 감사 기록이다. 규범 변경이 발생하면 작업을 멈추고 기준선 재승인을 수행한다.

구현 루트는 `apps/xdet-console/`이다.

## 기술 방향

Line Noise·Saturation·Geometry는 하나의 목적 탭에서 개별 또는 정렬된 부분수열로 실행한다. WPF는 source·mask·Params를 조립하고, 실행과 중간 프레임 생성은 확장된 `IXdetEngine`/PythonNet seam이 맡는다.

## 마일스톤

### M1 — 입력·Params (High)

- `tests/modules/phantoms/linesat.py`의 fixture preset을 합성 geometry 기준으로 사용한다.
- reference-region line-noise 경로는 advanced 옵션으로 둔다.
- Calibration 출력 mask를 우선 소비하며 synthetic mask injection은 시험 전용으로 제한한다.

### M2 — 개별 실행과 전용 시각화 (High)

- before/after/diff, diagnostic, saturation core·band mask, geometry boundary mask를 엔진 반환값으로 표시한다.
- line spectrum과 geometry displacement는 엔진 DTO가 배열을 제공할 때만 capability를 활성화한다.
- mask 의미와 픽셀 보존 의미를 구분한다.

### M3 — 조합·저장 (High)

- line_noise→saturation→geometry 부분수열을 `run_pipeline` 한 번으로 실행한다.
- 중간 프레임과 mask 누적을 표시한다.
- `xdet.frame-artifact/1.0` raw/JSON, mask raw, `xdet.run-manifest/1.0`을 저장·재열기한다.

### M4 — 검증 (High)

- `XDET-TC-112~119`를 사용해 no-reference/reference/saturation/geometry/composition/export/guard/SAMPLE을 검증한다.

### M-COVERAGE — 세 stage 전수 도달성

- line_noise, saturation, geometry 각각의 action과 ordered combination을 구현한다.
- 반환 XFrame/mask/history scalar diagnostics만 렌더하고 엔진에 없는 correction curve/vector control은 만들지 않는다.
- strict 사용자 input을 허용하고 evidence grade를 run manifest에 기록한다.

## 변경 대상

- `Xdet.Engine.Contract`: 세 stage Params·mask·diagnostic DTO와 `AlgorithmCatalogManifest`
- `Xdet.Engine.PythonNet`: 개별 및 pipeline 위임
- `Xdet.Console.App`: Line/Sat/Geo 탭과 stage selector
- `Xdet.Engine.Tests`: `XDET-TC-112~119`

## 완료 게이트

- [ ] geometry 계수 기본값을 UI가 임의 생성하지 않는다.
- [ ] Calibration mask가 일급 입력으로 연결된다.
- [ ] 조합은 단일 golden pipeline 호출이다.
- [ ] raw·mask round-trip, run manifest hash와 C-20이 통과한다.
- [ ] WPF/adapter의 Python `apps.gui` helper 의존이 0건이다.
