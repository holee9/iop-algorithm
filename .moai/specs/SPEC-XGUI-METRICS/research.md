---
id: SPEC-XGUI-METRICS
version: 0.5.1
status: completed
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
---

# SPEC-XGUI-METRICS 리서치 기록

## 조사 범위와 사실

- MTF 공개 작업은 `estimate_edge_angle`, `compute_mtf`, `mtf_value_at`이다.
- NPS 공개 작업은 `compute_nps`, `detect_line_noise`다.
- DQE 공개 작업은 `compute_dqe`, `dqe_value_at`이다.
- defect metric 공개 작업은 morphology/defect-map/defect-stats 계열이다.
- `compute_dqe`는 동일 shape의 freq/MTF/NNPS를 요구하고 `mtf_value_at`은 주어진 주파수에서 MTF를 반환한다.
- 등록 자료에는 승인된 edge phantom이 없으므로 DQE 실행 가능성과 결과 증거 등급을 분리해야 한다.

## 확정 결정

- MTF·NPS·line-noise·DQE·defect를 독립 source widget/action으로 제공한다.
- DQE engine은 strictly increasing `lp/mm` 축과 pixel pitch/domain/beam-quality provenance를 검증한다.
- `NPS_BINS_WITHIN_MTF_SUPPORT_V1`에 따라 MTF 범위 안의 NPS bin만 선택하고, 각 bin에서 `mtf_value_at`을 호출한 뒤 `compute_dqe`를 호출한다. 외삽과 endpoint clamp는 금지한다.
- 선택/제외 bin, 두 EntryPoint, upstream run/hash를 결과에 기록한다.
- JSON 리포트는 필수, CSV는 선택이다. metric engine은 값과 진단을 반환하고 UI가 임의 합격/불합격을 만들지 않는다.

## v0.5 초기 문서 통제 재검토

- v0.5 초기 검토는 이 문서가 기록한 Python golden 사실이나 알고리즘 의미를 바꾸지 않는다.
- 구현 전제는 `../SPEC-XGUI-MASTER/baseline-control.md` G0, 요구사항·TC·증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다.
- 사용자 승인과 기준선 동결 전에는 이 조사 결과를 근거로 소스·XAML·테스트 구현을 시작하지 않는다.
