# SPEC-XGUI v0.5.1 구현 핸드오프 — 승인 대기

## 현재 결론

사용자 목표는 일부 알고리즘 데모가 아니라 저장소 알고리즘 전체를 WPF GUI에서 실제 사용·검증하는 것이다. 구현 대상은 `apps/xdet-console/` .NET 9 WPF이며 Python `apps/gui/`는 역사적 동작·시험 선례다.

현재 WPF 코드는 Viewer, 고정 offset→gain Pipeline, Real Image, 합성 MTF의 부분 구현이다. 따라서 애플리케이션 구현 완료가 아니며, v0.5.1 문서는 이 격차를 구현자가 추측 없이 닫을 수 있도록 전체 실행 계약을 정의한다.

현재 상태는 `approval_state=pending_user`, `implementation_authorized=false`다. 내부 문서 감사가 통과해도 사용자 승인과 기준선 동결 전에는 아래 구현 순서를 실행하지 않는다.

## v0.5.1 기준선 후보에서 확정한 범위

- `algorithm-catalog.md`가 `modules/`, `metrics/`, `pipeline/` 대상 public operation을 ACTION/SESSION/DERIVED/INFRASTRUCTURE로 분류한다.
- ACTION/SESSION 전부를 9개 typed family(FRAME_PROCESS, PIPELINE, SEQUENCE, STACK_METRIC, PROFILE_METRIC, CALIBRATION_BUILD, METRIC_SERIES, NDT_SESSION, TIER)에 매핑한다.
- catalog→manifest→Contract handler→GUI command→`XDET-TC-096~167` 추적을 자동 시험으로 강제한다.
- operation 집합은 target 67(공개 대상 64 + SAMPLE helper 3), common infrastructure 6, catalog qualified callable 합계 73으로 분리한다.
- `AlgorithmAvailability`와 `EvidenceGrade`를 분리한다. 등록 fixture 부재는 알고리즘 영구 비활성 사유가 아니며 strict 사용자 입력은 실행 가능하다.
- DQE는 `NPS_BINS_WITHIN_MTF_SUPPORT_V1`에 따라 engine이 `metrics.mtf.mtf_value_at`과 `metrics.dqe.compute_dqe`를 실제 호출한다. UI 보간·외삽·clamp는 금지한다.
- calibration builder/import, lag state snapshot/restore, NDT accumulator, tier 결정·선택·실행·계측을 명시 실행 경로로 포함한다.
- frame 결과는 domain별 uint16 encoding, XFrame mask는 `uint8` bitmask로 저장한다.

## 권위 문서

1. `baseline-control.md`: G0, 사용자 승인, 기준선 동결, 변경 통제
2. `foundation.md`와 `algorithm-catalog.md`: 소스 사실, 전체 범위, 상태·증거·typed error 규칙
3. `spec.md`, `plan.md`, `acceptance.md`: 마스터 요구·순서·관찰 가능한 완료 조건
4. `traceability-matrix.md`: EARS 요구사항→인수기준→TC→증거 연결
5. `SPEC-XSEAM-002`: 9 family Contract/PythonNet 경계
6. 8개 `SPEC-XGUI-*` 그룹의 spec/plan/acceptance/research
7. `test-plan.md`, `eval-methodology.md`, `docs/XDET_TestSpec_v1.0.md`

감사 기록은 `.moai/reports/SPEC-XGUI-DOCUMENT-AUDIT-2026-07-13/`에 분리돼 있으며 규범이 아니다. `SPEC-VIEWER-001`, `docs/GUI_REVIEW.md`의 과거 Qt/Python GUI 결정도 현재 규범이 아니다.

## 구현 순서

0. G0 12/12, 사용자 명시 승인, v0.5.1 기준선 동결, `implementation_authorized=true`
1. catalog manifest와 9 family Contract, typed error, input/evidence envelope
2. PythonNet handler, RunCoordinator, artifact/run-manifest, catalog coverage tests
3. generic pipeline/sequence, calibration/session/tier/DQE shared 실행 경로
4. Calibration부터 Metrics까지 8개 목적 그룹 GUI command/view
5. `XDET-TC-096~167` xUnit/integration/ViewModel/UIA 증거 등록

PLANNED TC는 구현·자동화 증거가 없으므로 통과로 보고하지 않는다. 실제 코드 구현은 문서 내부 감사와도 별도이며, 승인 여부는 `baseline-control.md`, 최신 감사 결과는 `.moai/reports/`의 현재 기준선 보고서를 따른다.
