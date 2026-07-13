---
id: SPEC-XGUI-ENHANCE
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
labels: [xgui, enhancement, mse, window, gsdf, wpf]
---

# SPEC-XGUI-ENHANCE — 구현 계획

## 0. 구현 착수 전제

이 계획은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 마스터 plan M0.5를 상속한다. 사용자 승인 기록, 기준선 동결, `implementation_authorized=true`가 모두 존재하기 전에는 아래 마일스톤의 소스·XAML·테스트·패키지 변경을 시작하지 않는다. 내부 감사 통과나 기술적 구현 가능성만으로 이 전제를 충족했다고 보지 않는다.

진입 증거는 승인된 v0.5.1 기준선, 요구사항-인수-TC 추적 차이 0, 미결정 임계 0, 현재 worktree/commit을 가리키는 최종 감사 기록이다. 규범 변경이 발생하면 작업을 멈추고 기준선 재승인을 수행한다.

## 기술 방향

구현 대상은 `apps/xdet-console/`이다. MSE·window 실행, DRC, GSDF LUT와 진단값은 Python golden이 산출하고 C#은 DTO 전달과 렌더링만 담당한다. raw-DN 입력과 `[0,1]` display-normalized 출력의 도메인을 UI와 export sidecar에서 명시적으로 분리한다.

## 마일스톤

### M1 — Params와 실행 계약 (High)

- MSE는 `required_params(params)`, window는 `REQUIRED_PARAMS`와 VOI 선택 규칙으로 폼을 구성한다.
- MSE 단독 실행은 명시 noise model이 있을 때만 허용한다.
- denoise→mse→window 또는 mse→window 부분수열은 pipeline seam으로 실행한다.

### M2 — Enhancement 뷰 (High)

- raw-DN 입력과 display-normalized 출력을 각자의 도메인 눈금으로 표시한다.
- history 진단, saturation overlay, DRC A/B, `build_gsdf_lut` 결과를 엔진 반환값으로 렌더한다.
- DRC A/B는 선택 기능이며 구현되지 않아도 핵심 MSE/window 흐름을 막지 않는다.

### M3 — 저장 (Medium)

- 출력은 `<name>_result.raw`에 uint16 display-normalized 양자화로 저장하고 JSON에 `domain=display_normalized`를 기록한다.
- 원본 raw는 별도 pre-stage artifact로만 저장한다.
- mask가 있으면 공통 mask raw를 함께 저장한다.

### M4 — 검증 (High)

- `XDET-TC-128~135`로 Params, 도메인, 진단, DRC/GSDF, composition, errors, export, guard를 검증한다.

### M-COVERAGE — MSE selector와 window 파생 연산

- MSE selector는 golden `required_params`로 form을 생성한다.
- window service는 process와 함께 `build_gsdf_lut`, `remap_to_pvalue` 결과를 typed diagnostics로 반환한다.
- XDET-TC-128~135에 MSE methods, window, GSDF/P-value, combination, domain/export/guard를 매핑한다.

## 변경 대상

- `Xdet.Engine.Contract`: enhancement Params/result/domain DTO
- `Xdet.Engine.PythonNet`: MSE/window/GSDF/pipeline 위임
- `Xdet.Console.App`: Enhancement 탭
- `Xdet.Engine.Tests`: `XDET-TC-128~135`

## 완료 게이트

- [ ] raw-DN과 display-normalized 도메인이 혼용되지 않는다.
- [ ] MSE noise gate가 무단 기본값 없이 동작한다.
- [ ] UI에 DRC/GSDF 산술이 없다.
- [ ] 저장 sidecar가 source/export domain과 quantization을 명시하고 run manifest가 input/calib/params/output hash를 보존한다.
- [ ] WPF/adapter의 Python `apps.gui` helper 직접 의존이 0건이다.
