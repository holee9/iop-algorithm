---
id: SPEC-XGUI-ENHANCE
version: 0.5.1
status: completed
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
---

# SPEC-XGUI-ENHANCE 리서치 기록

## 조사 범위와 사실

- `modules.mse.required_params`는 method별 필수 Params를 결정하고 `modules.mse.process`는 noise model을 요구한다.
- `modules.window.process` 외에 `build_gsdf_lut`와 `remap_to_pvalue`가 독립 공개 golden 작업이다.
- MSE/window 결과는 raw DN이 아니라 display-normalized `[0,1]` 도메인이다.
- 원본 raw는 결과와 구별되는 pre-stage artifact다.

## 확정 결정

- MSE selector는 `required_params` 기반 동적 폼을 사용하고 명시 noise model 없이는 실행하지 않는다.
- window 실행, GSDF LUT 생성, P-value remap을 각각 GUI action과 Contract handler로 노출한다.
- display-normalized export는 도메인·EntryPoint·Params·입력 hash를 기록한다.
- DRC A/B는 optional이며 GSDF/P-value 값은 공개 golden 함수 결과만 표시한다.

## v0.5 초기 문서 통제 재검토

- v0.5 초기 검토는 이 문서가 기록한 Python golden 사실이나 알고리즘 의미를 바꾸지 않는다.
- 구현 전제는 `../SPEC-XGUI-MASTER/baseline-control.md` G0, 요구사항·TC·증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다.
- 사용자 승인과 기준선 동결 전에는 이 조사 결과를 근거로 소스·XAML·테스트 구현을 시작하지 않는다.
