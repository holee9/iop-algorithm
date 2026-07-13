# SPEC-XGUI v0.5.1 최종 반복 감사

Date: 2026-07-13
Repository HEAD: `1f7bbe0644913bc7bd910c4467d995807cf25375`
Audited input manifest: 이 보고서 자체를 제외한 변경 문서 74개(Markdown 73, HTML 1)
Audited input SHA-256: `803c2ff75e3efe78a93a725a07d843c2f39c30f949b92392792728f89f6090fe`
Audit scope: MASTER + XSEAM-002 + 8개 목적 그룹 + GUI 기준/TestSpec + Python golden + 현재 WPF 기준선

## 판정

**문서 내용과 내부 교차검증: PASS / INTERNALLY_REVIEWED**

**실제 GUI 구현 가능성: YES — 사용자 승인 후 M1부터 구현 가능**

**사용자 승인: PENDING_USER**

**구현 착수: NOT AUTHORIZED**

문서는 전체 대상 알고리즘의 실제 호출·표시·거부·저장·재현을 구현할 수 있는 수준으로 닫혔다. 다만 G0 조건 12인 사용자 명시 승인과 기준선 동결 전에는 신규 코드·XAML·시험·패키지 변경을 시작하지 않는다. 현재 WPF는 역사적 부분 vertical slice이며 전체 XGUI 완료 증거가 아니다.

## 1. 이번 반복에서 정정한 결함

1. `67개 operation`을 전체 callable처럼 읽을 수 있던 경계를 `TARGET_OPERATION_SET=64`, `SAMPLE_HELPER_SET=3`, `COMMON_INFRASTRUCTURE_SET=6`, 합집합 `CATALOG_CALLABLE_SET=73`으로 분리했다.
2. `CalibSet.load/save`를 축약명이 아닌 `common.calibset.CalibSet.load/save` qualified EntryPoint로 고정했다.
3. README·CLAUDE·XSEAM-001 역사 문서에서 과거 `.NET 8/XSEAM-001`과 현재 `.NET 9/XGUI v0.5.1/XSEAM-002`의 권위를 분리했다.
4. 코드맵에서 현재 제품 WPF와 역사적 Python Qt 검증 GUI의 역할을 분리하고 실제 파일 수를 정정했다.
5. 축약 범위 때문에 누락됐던 7개 단일 요구사항 ID를 정확한 acceptance ID로 고쳤다.
6. 현재 규범 메타데이터와 본문 기준선 표기를 v0.5.1로 동기화했다.
7. WPF 전체 빌드의 `NU1701`을 숨기지 않고 M1 종료 전 반드시 해소할 패키지 호환성 게이트로 추가했다.

## 2. 문서 세트와 통제 상태

| 검사 | 결과 |
|---|---:|
| 규범 세트 | MASTER + XSEAM-002 + 8그룹 = 10 |
| 필수 `spec/plan/acceptance/research` | 40/40 |
| 통제 Markdown | 48 |
| 메타데이터 보유 문서 | 46/46 v0.5.1 일치 |
| `document_status` | 46/46 `internally_reviewed` |
| `approval_state` | 46/46 `pending_user` |
| `implementation_authorized` | 46/46 `false` |

## 3. 요구사항·시험·연산 완결성

| 검사 | 결과 |
|---|---:|
| 정규 EARS 요구사항 | 287/287 acceptance 추적 |
| 그룹 GUI TC | 64/64, 그룹 간 교차오염 0 |
| 공통 GUI TC | 8/8, 소유 문서 추적 |
| 중앙 GUI TC | `XDET-TC-096~167` = 72/72 |
| 대상 연산 | modules 22 + metrics 30 + pipeline 12 = 64 |
| SAMPLE helper | scripts 3 |
| 제품 대상 합계 | 64 + 3 = 67 |
| 공통 인프라 | equivalence 2 + raw load 1 + CalibSet validate/load/save 3 = 6 |
| catalog callable 합집합 | 73/73 source symbol 해석 |
| FeatureId | 51/51 고유 |
| 실행 family | 9/9 |
| 공개 Python 예외형 | 17/17 typed error 매핑 |
| Params authority 값 | 106/106 문서 계약 존재 |
| Calib payload 값 | 16/16 문서 계약 존재 |

각 FeatureId는 실제 Python EntryPoint, typed request/result family, Params/Calib 권위, GUI surface와 TC를 갖는다. 등록 데이터 부재와 알고리즘 구현 부재는 별도 상태이며, strict 사용자 입력은 `USER_SUPPLIED_UNVERIFIED` evidence로 실제 실행할 수 있다.

## 4. 실제 사용·검증 계약

- 제품 GUI는 `.NET 9 WPF` 하나이며 Qt/PySide 앱은 역사적 검증 선례다.
- WPF는 DSP·지표·파이프라인 순서·캘리브레이션 판정을 재구현하지 않고 `IXdetEngine`/PythonNet seam을 통해 Python golden을 호출한다.
- 단일 프레임, ordered stack/sequence, profile, calibration series, metric series 입력과 Params/CalibSet 검증이 정의돼 있다.
- before/after/diff/mask/history, typed error, evidence grade, artifact/run-manifest 저장과 재열기 경로가 정의돼 있다.
- DQE는 `mtf_value_at` 후 `compute_dqe`를 실제 호출하고 MTF support 밖 bin을 제외한다. UI 보간·외삽·수치 재계산은 금지한다.
- SAMPLE은 구조 sanity, SYNTHETIC은 승인된 합성 oracle, 실측은 별도 evidence로 평가해 알고리즘 실행 가능성과 성능 승인 주장을 분리한다.

따라서 문서만으로 전체 GUI 구현을 시작할 수 있지만, 실제 실측 성능 승인은 등록 또는 사용자 제공 실측 데이터와 실행 증거가 생긴 뒤에만 가능하다.

## 5. 정적 무결성

| 검사 | 결과 |
|---|---:|
| 현재 권위 문서의 오래된 v0.5 표기 | 0 — 연구 이력만 초기 v0.5로 명시 |
| 상대 링크 | 110/110 |
| Requirement ID 누락 | 0 |
| FeatureId 중복 | 0 |
| EntryPoint 중복/누락 | 0/0 |
| `TBD`/`TODO`/literal `\\n` | 0/0/0 |
| `git diff --check` | PASS |
| 비문서 변경 | 0 |

## 6. 회귀·빌드 증거와 열린 구현 게이트

| 실행 | 결과 |
|---|---:|
| `uv run pytest -q` | 632 passed |
| `uv run lint-imports` | 7 kept, 0 broken |
| `dotnet test apps/xdet-console/Xdet.sln --no-restore` | 21 passed, 0 failed, 0 skipped |
| `dotnet build apps/xdet-console/Xdet.sln --no-restore` | error 0, warning 1 |

유일한 빌드 경고는 `ScottPlot.WPF 5.1.59`의 전이 의존성 `SkiaSharp.Views.WPF 3.119.0`이 `net9.0-windows`에서 .NET Framework 자산으로 복원됐다는 `NU1701`이다. 이는 문서 완결성 실패는 아니지만 제품 구현 품질 게이트다. M1에서 호환 패키지 조합으로 해소하고 전체 solution warning 0 및 실제 WPF UI Automation smoke를 통과하기 전에는 M2로 진행할 수 없다.

## 7. G0와 다음 단계

| 조건 | 상태 |
|---|---|
| 1~11 문서·집합·정량·링크·감사 | PASS |
| 12 사용자 명시 승인 | PENDING |
| 기준선 동결 | NO |
| 구현 허가 | NO |

사용자가 v0.5.1 범위와 문서를 명시 승인하면 [baseline control](../../specs/SPEC-XGUI-MASTER/baseline-control.md)에 승인 버전·일시·범위를 기록하고 모든 통제 문서 상태를 동기화한다. 이후 [implementation plan](../../specs/SPEC-XGUI-MASTER/plan.md)의 M1부터 순차 구현한다.
