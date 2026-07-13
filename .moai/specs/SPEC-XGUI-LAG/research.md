---
id: SPEC-XGUI-LAG
version: 0.5.1
status: completed
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
---

# SPEC-XGUI-LAG 리서치 기록

## 조사 범위와 사실

- `LagCorrector.process`는 상태형이며 sequence 동안 같은 인스턴스를 재사용해야 한다.
- `serialize_state`와 `load_state`가 공개 snapshot/restore 경계다.
- `compute_first_frame_lag`, `compute_ghost_cnr`, `fit_lag_irf`는 서로 다른 입력과 결과를 갖는 metric 작업이다.
- 등록 GHOST는 SAMPLE sanity 자료이며 수치 승인 기준이 아니다.

## 확정 결정

- fresh sequence, step 실행, snapshot, restore, reset을 명시적인 SESSION 명령으로 제공한다.
- 주 IRF 경로는 합성 step-response를 `fit_lag_irf`에 전달한다. fixture 계수는 비정본 demo로만 허용한다.
- first-frame lag, ghost CNR, lag IRF를 각각 실행·리포트한다.
- float32/float64 차이는 진단으로 표시하며 invalid ROI와 부적합 IRF는 engine 오류를 그대로 구조화한다.

## v0.5 초기 문서 통제 재검토

- v0.5 초기 검토는 이 문서가 기록한 Python golden 사실이나 알고리즘 의미를 바꾸지 않는다.
- 구현 전제는 `../SPEC-XGUI-MASTER/baseline-control.md` G0, 요구사항·TC·증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다.
- 사용자 승인과 기준선 동결 전에는 이 조사 결과를 근거로 소스·XAML·테스트 구현을 시작하지 않는다.
