---
id: SPEC-XGUI-LINESATGEO
version: 0.5.1
status: completed
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
---

# SPEC-XGUI-LINESATGEO 리서치 기록

## 조사 범위와 사실

- `modules.line_noise.process`, `modules.saturation.process`, `modules.geometry.process`가 이 그룹의 세 public action이다.
- line-noise는 reference/no-reference 경로를 제공한다.
- saturation은 포화 픽셀을 복원하지 않고 core/band 상태를 `uint8` mask에 기록한다.
- geometry 결과 계약에 별도 curve/vector 진단이 없다. 반환하지 않는 값을 GUI가 계산하거나 가짜 capability로 만들 수 없다.

## 확정 결정

- 세 알고리즘의 실제 Params·입력·출력·오류를 그대로 노출하고 engine 반환값만 표시한다.
- geometry 합성 입력은 기존 linesat phantom preset을 사용하며 reference 경로는 advanced에 둔다.
- 실제 mask의 주 공급자는 Calibration 결과이고 합성 mask 주입은 시험 전용이다.
- mask는 `<name>_result_mask.raw`와 metadata로 분리 저장하며 dtype은 `uint8`이다.

## v0.5 초기 문서 통제 재검토

- v0.5 초기 검토는 이 문서가 기록한 Python golden 사실이나 알고리즘 의미를 바꾸지 않는다.
- 구현 전제는 `../SPEC-XGUI-MASTER/baseline-control.md` G0, 요구사항·TC·증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다.
- 사용자 승인과 기준선 동결 전에는 이 조사 결과를 근거로 소스·XAML·테스트 구현을 시작하지 않는다.
