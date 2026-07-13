---
id: SPEC-XGUI-MASTER
version: 0.5.1
status: completed
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
priority: high
issue_number: 58
labels: [xgui, research, source-audit, exhaustive-coverage]
---

# SPEC-XGUI-MASTER 리서치 기록

## 조사 범위

- `modules/`, `metrics/`, `pipeline/`의 공개 실행 함수·메서드·상태 속성
- `common/xframe.py`, `common/calibset.py`, 등록 데이터 manifest와 실제 파일
- 현재 C# Contract·PythonNet·WPF 구현과 Python golden API 사이의 차이
- XGUI 그룹 사양, XSEAM-002, GUI 기준, 중앙 시험 레지스트리

## 확인된 사실

- 현재 WPF 앱은 Viewer, 고정 offset→gain 파이프라인, 실영상, 합성 MTF의 부분 구현이며 전체 알고리즘용 generic seam은 아직 없다.
- Python golden에는 단일 프레임 처리뿐 아니라 pipeline, sequence, calibration builder, metric series, NDT session, tier/state 작업이 있다. 따라서 단일 `RunPipeline` DTO만으로는 전체 GUI 사용·검증이 불가능하다.
- 등록 edrogi 자료는 `usage=sample-plumbing`인 SAMPLE/QUARANTINE 자료다. 실행 sanity 근거로는 쓸 수 있지만 수치 정답 golden으로 승격할 수 없다.
- `XFrame.MASK_DTYPE`은 `numpy.uint8`이고 bit는 DEFECT=1, SATURATION=2, INTERPOLATION=4, SATURATION_BAND=8이다.
- `metrics.mtf.mtf_value_at()`이 공개되어 있고 `metrics.dqe.compute_dqe()`는 동일 shape의 freq/MTF/NNPS를 받는다. 따라서 DQE는 UI 보간 없이 엔진에서 두 golden 함수를 조합해 실행할 수 있다.
- tier 공개 API는 `decide_tier`, `select_pipeline`, `run_tier`, `time_tier`이며 강제 upgrade 거부와 강제 downgrade 허용이 계약의 일부다.

## 확정 결정

- 구현 대상은 저장소 공개 API 중 사용자 가치가 있는 ACTION·SESSION·DERIVED 작업 전체다. 단순 data carrier와 내부 helper는 카탈로그에서 SUPPORTING/INFRASTRUCTURE로 구분한다.
- seam은 9개 typed family(FRAME_PROCESS, PIPELINE, SEQUENCE, STACK_METRIC, PROFILE_METRIC, CALIBRATION_BUILD, METRIC_SERIES, NDT_SESSION, TIER)를 제공한다.
- 알고리즘 실행 가능 상태와 증거 등급은 서로 다른 축으로 관리한다. 등록 golden 부재가 알고리즘 실행 자체를 막지 않으며, 엄격 검증된 사용자 입력은 실행할 수 있다.
- DQE 축 정책은 `NPS_BINS_WITHIN_MTF_SUPPORT_V1`로 고정한다. MTF 범위를 벗어난 NPS bin은 제외하며 외삽이나 끝점 clamp를 하지 않는다.
- 중앙 GUI 시험 블록은 `XDET-TC-096~167`이다. 앞 64개는 그룹별 작업을, 마지막 8개는 공통 전수성·seam·tier·DQE를 검증한다.
- raw 영상과 결과 mask를 분리하고 mask는 `uint8` bitmask로 보존한다.

## 근거 문서

- [foundation](./foundation.md)
- [algorithm catalog](./algorithm-catalog.md)
- [viewer redesign](../../../apps/xdet-console/docs/viewer-redesign.html)
- [XSEAM-002](../SPEC-XSEAM-002/spec.md)
- [VIEWER-001](../SPEC-VIEWER-001/spec.md)
- [GUI criteria](../../../docs/GUI_CRITERIA.md)

## v0.5 재점검 결과

1. 기존 v0.4는 operation 67/67과 중앙 TC 72개를 닫았지만 사용자 승인·기준선 동결·구현 착수 차단 상태를 문서화하지 않았다. 내부 `PASS`가 구현 허가처럼 읽힐 수 있어 G0를 별도 통제 계약으로 추가했다.
2. MASTER와 그룹 acceptance는 관찰 가능한 시나리오를 보유했지만 모든 개별 EARS ID를 중앙 TC와 증거에 전개하는 단일 매트릭스가 없었다. `traceability-matrix.md`를 추가하고 각 acceptance에 요구사항 범위 표를 추가했다.
3. Calibration 102~103, Denoise 124~127, NDT 150~151은 범위 블록으로만 나타나 개별 실행 의도가 약했다. builder 전수성, selector/NOISE/오류/evidence, NDT 7-action/state/report 시나리오로 각각 고정했다.
4. source에는 공개 예외형 17개가 존재하지만 catalog에 폐쇄형 매핑이 없었다. `CalibSchemaError`부터 `TierDecisionError`까지 typed `EngineError` code와 UI 동작을 정의했다.
5. GUI 성능 기준의 임시 표지를 제거했다. 3072² float32 한 장은 약 36 MiB이므로 active before/after/diff와 mask·bitmap, full-frame LRU 8장을 포함해도 2 GiB 상한 안에서 검증 가능하다. full-frame LRU 8, thumbnail LRU 256, W/L p95 100 ms, heartbeat 200 ms, cancel 표시 250 ms를 측정 가능한 기준으로 고정했다.
6. SPEC 디렉터리에 있던 `audit-r1.md`와 이전 최종 감사는 현재 상태를 분석하는 보고서이므로 `.moai/reports/SPEC-XGUI-DOCUMENT-AUDIT-2026-07-13/`로 이동했다.

## v0.5 통제 결정

- 문서의 기술적 완결성, 사용자 승인, 구현 완료를 세 상태로 분리한다.
- 현재 기준선 후보는 내부 검토 중이고 사용자 승인은 대기 상태다. `implementation_authorized=false`는 의도적인 차단 상태다.
- 사용자 승인 전에는 코드·XAML·신규 테스트·패키지·빌드 설정을 변경하지 않는다.
- 승인 뒤 규범 변경은 코드에서 임의 해석하지 않고 문서 버전 상승, 영향 TC 재검토, 사용자 재승인을 선행한다.
- 구현 평가는 direct-golden transport fidelity와 알고리즘 품질 oracle을 분리한다. GUI는 기존 알고리즘 임계를 새로 만들지 않는다.

추가 권위 문서: [baseline control](./baseline-control.md), [traceability matrix](./traceability-matrix.md), [evaluation methodology](./eval-methodology.md), [test plan](./test-plan.md).

## v0.5.1 최종 재점검 보완

1. v0.5 감사의 “67개 operation”은 공개 대상 64개와 SAMPLE helper 3개를 뜻했지만, catalog에 별도 매핑된 common infrastructure까지 포함한 전체 수처럼 서술돼 경계가 모호했다. `TARGET_OPERATION_SET=64`, `SAMPLE_HELPER_SET=3`, `COMMON_INFRASTRUCTURE_SET=6`, 합집합 `CATALOG_CALLABLE_SET=73`으로 분리했다.
2. `calib.schema`가 `CalibSet.validate`만 qualified name으로 쓰고 `load/save`는 축약해 자동 집합 검사가 두 호출을 놓칠 수 있었다. 세 메서드를 모두 qualified EntryPoint로 고정했다.
3. README의 역사적 `.NET 8/SPEC-XSEAM-001` 로드맵과 현재 `.NET 9/SPEC-XSEAM-002` 기준이 한 문서에서 충돌했다. XSEAM-001은 구현된 얇은 수직 슬라이스 기록, XSEAM-002와 XGUI v0.5.1은 전체 확장 규범으로 분리했다.
4. 프로젝트 코드맵이 Python Qt 검증 GUI만 유일한 앱으로 표시해 현재 WPF 제품 앱을 누락했다. 두 실행 앱의 목적과 호출 경계를 각각 기록했다.
5. 전체 WPF build는 오류 0이지만 `ScottPlot.WPF` 전이 의존성에서 `NU1701` 1건이 재현됐다. 이를 M1 종료 전 해소해야 하는 패키지 호환성·실제 UI smoke 게이트로 승격했다.
