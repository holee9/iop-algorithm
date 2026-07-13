---
id: SPEC-XGUI-GRID
version: 0.5.1
status: completed
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
---

# SPEC-XGUI-GRID 리서치 기록

## 조사 범위와 사실

- grid 공개 작업은 `analyze`, `notch_gain_1d`, `process`다.
- virtual-grid 공개 작업은 `estimate_scatter`, `process`다.
- scatter kernel은 `build_scatter_kernel`과 `fit_scatter_kernel_from_samples` 두 경로를 제공한다.
- grid와 virtual-grid는 canonical pipeline에서 조합 가능하지만 목적과 파라미터가 다른 알고리즘이다.

## 확정 결정

- 여섯 공개 작업을 각각 선택·실행·검증할 수 있게 한다.
- 기본 builder는 `build_scatter_kernel`; sample 자료가 있으면 fit 경로를 별도 action으로 제공한다.
- builder 입력은 advanced panel에 노출하고 8 cm/100 kV는 시험 preset으로만 사용한다.
- folded-harmonic marker와 제외/선택 주파수 근거를 engine 결과 provenance로 표시한다.
- grid+virtual-grid 조합은 low-ratio residual scatter 목적을 명시한 preset에서만 기본 제공한다.

## v0.5 초기 문서 통제 재검토

- v0.5 초기 검토는 이 문서가 기록한 Python golden 사실이나 알고리즘 의미를 바꾸지 않는다.
- 구현 전제는 `../SPEC-XGUI-MASTER/baseline-control.md` G0, 요구사항·TC·증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다.
- 사용자 승인과 기준선 동결 전에는 이 조사 결과를 근거로 소스·XAML·테스트 구현을 시작하지 않는다.
