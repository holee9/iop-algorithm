---
id: SPEC-XGUI-NDT
version: 0.5.1
status: completed
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
---

# SPEC-XGUI-NDT 리서치 기록

## 조사 범위와 사실

- 공개 action은 `read_duplex_srb`, `compute_snr`, `compute_snrn`, `shot_log`, `correct_thickness`, `read_single_wire_iqi`, `build_iqi_report`다.
- `SNRnAccumulator`는 `update`, `target_reached`, `target_frame_index`, `current`를 가진 상태형 session이다.
- 등록 SAMPLE에는 duplex-wire가 없으므로 SRb를 자동 판정할 수 없고 SNR sanity만 가능하다.
- subpixel profile 보간은 golden API에 없으므로 profile 입력은 정수 좌표/nearest로 제한한다.

## 확정 결정

- 일곱 action과 accumulator session 전부를 GUI command와 typed handler로 제공한다.
- shot log, target 진행률, target frame, current 결과를 session provenance와 함께 보존한다.
- SAMPLE은 SNR-only sanity로 표시하고 사용자 제공 duplex/IQI 입력은 별도 evidence grade로 실행한다.
- JSON 리포트는 필수, CSV는 선택이며 GUI-E2E는 `XDET-TC-144~151` 전체를 사용한다.

## v0.5 초기 문서 통제 재검토

- v0.5 초기 검토는 이 문서가 기록한 Python golden 사실이나 알고리즘 의미를 바꾸지 않는다.
- 구현 전제는 `../SPEC-XGUI-MASTER/baseline-control.md` G0, 요구사항·TC·증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다.
- 사용자 승인과 기준선 동결 전에는 이 조사 결과를 근거로 소스·XAML·테스트 구현을 시작하지 않는다.
