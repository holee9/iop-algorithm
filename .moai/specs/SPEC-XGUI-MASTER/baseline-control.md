---
id: SPEC-XGUI-MASTER-BASELINE
version: 0.5.1
status: planned
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-13
updated: 2026-07-13
author: drake.lee
priority: high
issue_number: 58
---

# SPEC-XGUI 구현 기준선 통제

## 1. 목적

이 문서는 문서의 기술적 정합성 통과와 실제 구현 착수 승인을 분리한다. 내부 감사의 `PASS`, 테스트의 기존 회귀 통과, 구현 가능성 판단은 사용자 승인과 같은 의미가 아니다. `apps/xdet-console/` 구현은 아래 G0 게이트가 `APPROVED_AND_FROZEN`이 되기 전에는 시작할 수 없다.

## 2. 현재 기준선 상태

| 항목 | 현재 값 |
|---|---|
| 기준선 후보 | `SPEC-XGUI v0.5.1` |
| 문서 내부 교차검토 | `PASS` — v0.5.1 반복 감사, 결함 0 |
| 사용자 명시 승인 | `PENDING_USER` |
| 기준선 동결 | `NO` |
| 구현 착수 허가 | `NO` |
| 구현 대상 | `apps/xdet-console/` .NET 9 WPF |
| 비구현 대상 | Qt/PySide/napari GUI, Python `apps/gui/`의 제품화 |

`PENDING_USER`, `NO`는 누락 표기가 아니라 현재의 통제 상태다. 사용자 승인 전에는 어떤 문서도 승인된 것으로 표기하지 않는다.

## 3. 권위와 충돌 해결

1. 제품 요구 권위: `docs/XDET_SWR_spec_v1.2.md`, `docs/XDET_measurement_protocol_v1.0.md`
2. 동결 알고리즘 권위: `common/`, `modules/`, `pipeline/`, `metrics/`
3. GUI 전체 범위 권위: `spec.md`, `foundation.md`, `algorithm-catalog.md`
4. seam 권위: `SPEC-XSEAM-002`
5. 그룹별 동작 권위: 8개 `SPEC-XGUI-*`의 `spec.md`
6. 관찰 가능한 완료 권위: 각 `acceptance.md`, `traceability-matrix.md`, `test-plan.md`, `eval-methodology.md`
7. 순서와 착수 통제 권위: `plan.md`, 본 문서

하위 문서가 상위 권위와 충돌하면 하위 문서를 수정한다. 과거 Qt/Python GUI 검토 문서는 역사 자료이며 규범이 아니다.

## 4. G0 — 구현 착수 게이트

다음 열두 조건을 모두 충족해야 한다.

1. MASTER, XSEAM, 8개 그룹의 `spec.md`, `plan.md`, `acceptance.md`, `research.md`가 동일 기준선 버전이다.
2. Python 공개 대상 64개와 허용 SAMPLE helper 3개는 `TARGET_OPERATION_SET+SAMPLE_HELPER_SET=67`, 공통 실행 기반 6개는 `COMMON_INFRASTRUCTURE_SET=6`으로 분리되고, 합집합 73개가 `algorithm-catalog.md`에 중복·누락 없이 qualified EntryPoint로 분류돼 있다.
3. 모든 ACTION/SESSION은 `FeatureId → EntryPoint → family DTO → Contract handler → GUI command/AutomationId → XDET-TC` 경로를 가진다.
4. 모든 EARS 요구사항은 `traceability-matrix.md`에서 관찰 가능한 인수기준과 시험 증거로 연결된다.
5. 중앙 GUI 시험 `XDET-TC-096~167` 72개가 중복 없이 배정되고 구현 전 상태는 모두 `PLANNED`로 유지된다.
6. GUI 정량 평가 기준에는 미정 임계·미완료 표지·의미가 열린 기본값이 없다. 알고리즘 Params의 provenance 등급 `[T]`는 Params/config가 권위이고 UI 하드코딩이 0일 때만 허용한다.
7. 입력·Params·CalibSet·출력·오류·provenance·evidence grade·저장/재열기 계약이 모든 실행 family에 정의돼 있다.
8. SAMPLE, SYNTHETIC, USER_SUPPLIED, GUIDING, GOLDEN 증거 등급이 알고리즘 구현 가능성과 분리돼 있다.
9. 모든 상대 링크가 존재하고 감사 보고서는 `.moai/reports/`에 있으며 규범 SPEC과 섞이지 않는다.
10. Markdown diff 검사, 요구사항/TC/operation 집합 검사, 금지된 Qt 및 UI DSP 경계 검사가 통과한다.
11. 내부 최종 감사가 결함 0건으로 종료되고 감사 결과가 현재 commit/worktree hash를 기록한다.
12. 사용자가 기준선 버전과 구현 범위를 명시적으로 승인한다.

조건 12는 자동화나 작성자의 판단으로 대체할 수 없다.

## 5. 승인 기록과 상태 전이

```text
UNDER_REVISION
  -> INTERNALLY_REVIEWED
  -> PENDING_USER
  -> APPROVED_AND_FROZEN
  -> IMPLEMENTATION_AUTHORIZED
```

| 버전 | 내부 감사 | 사용자 승인 | 동결 | 구현 허가 |
|---|---|---|---|---|
| 0.5.1 | `PASS` — 2026-07-13 | `PENDING_USER` | `NO` | `NO` |

사용자가 명시적으로 승인한 뒤에만 승인 일시와 승인된 버전을 이 표에 기록하고 모든 규범 문서의 `approval_state`와 `implementation_authorized`를 동기화한다.

## 6. 변경 통제

- 알고리즘 범위, DTO, 입력 종류, Params/CalibSet, 실행 순서, 수치 판정, TC 배정, 저장 포맷을 바꾸는 변경은 규범 변경이다. 기준선 버전을 올리고 G0 전체와 사용자 승인을 다시 수행한다.
- 오탈자, 링크, 표현만 고치며 의미가 바뀌지 않는 변경은 편집 변경이다. 감사 기록에 남기고 집합·링크 검사를 다시 수행한다.
- Python 공개 API나 SWR/측정 프로토콜이 바뀌면 기존 승인은 자동 만료된다. catalog, research, spec, acceptance, test-plan을 다시 교차검토한다.
- 구현 중 발견된 사양 결함은 코드에서 임의 해석하지 않는다. 문서를 먼저 수정하고 영향 TC와 승인 상태를 갱신한다.

## 7. 구현 금지선

G0가 닫히기 전에는 M1 이후의 소스 코드, XAML, 테스트 구현, 패키지 의존성, 빌드 설정을 변경하지 않는다. 현재 존재하는 부분 WPF 코드는 연구 기준선일 뿐 완료 증거가 아니며, 문서 승인 전 신규 구현의 출발점으로 사용하지 않는다.
