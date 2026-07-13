---
id: SPEC-XGUI-METRICS
version: 0.5.1
status: planned
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
priority: medium
issue_number: 58
labels: [xgui, metrics, mtf, nps, dqe, defect, wpf]
---

# SPEC-XGUI-METRICS — 구현 계획

## 0. 구현 착수 전제

이 계획은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 마스터 plan M0.5를 상속한다. 사용자 승인 기록, 기준선 동결, `implementation_authorized=true`가 모두 존재하기 전에는 아래 마일스톤의 소스·XAML·테스트·패키지 변경을 시작하지 않는다. 내부 감사 통과나 기술적 구현 가능성만으로 이 전제를 충족했다고 보지 않는다.

진입 증거는 승인된 v0.5.1 기준선, 요구사항-인수-TC 추적 차이 0, 미결정 임계 0, 현재 worktree/commit을 가리키는 최종 감사 기록이다. 규범 변경이 발생하면 작업을 멈추고 기준선 재승인을 수행한다.

구현 루트는 `apps/xdet-console/`이다.

## 기술 방향

Metrics 탭은 서로 다른 입력 계약을 가진 MTF·NPS·line-noise·DQE·Defect 하위도구를 한 목적 탭에 배치한다. 지표 값, curve, histogram, warning은 모두 Python metrics engine 반환 DTO를 사용한다. DQE 축 정렬은 `NPS_BINS_WITHIN_MTF_SUPPORT_V1`에 따라 engine이 골든 `mtf_value_at`과 `compute_dqe`를 조합해 수행한다.

## 마일스톤

### M1 — 지표별 입력 (High)

- MTF frame/ROI, NPS flat sequence, Defect dark/flat/truth-map 입력 위젯을 분리한다.
- 입력 source와 `EvidenceGrade`를 각 결과에 기록한다.

### M2 — 계산과 시각화 (High)

- `ComputeMtf`, `ComputeNps`, `DetectLineNoise`, `ComposeDqe`, `ClassifyDefects`를 typed `IXdetEngine`/PythonNet seam으로 노출한다.
- 공통 `MetricResultEnvelope`는 axes, series, scalars, warnings, condition, source hashes를 보존한다.
- 곡선·스칼라·warning·condition과 defect histogram/class-map을 렌더한다.
- EV pass/fail 또는 새로운 sanity 수치 임계값은 만들지 않는다.

### M3 — DQE engine composition (High)

- `DqeComposeRequest`가 MTF/NPS series와 source/run/hash/pixel-pitch/domain metadata를 운반한다.
- engine은 `NPS_BINS_WITHIN_MTF_SUPPORT_V1`로 target bin을 선택하고 각 bin에서 골든 `mtf_value_at`을 호출한 뒤 `compute_dqe`를 호출한다.
- support 밖 bin은 제외하고 endpoint clamp·외삽하지 않는다. UI/ViewModel에는 interpolation 코드가 없어야 한다.
- 합성 MTF/NPS와 축·metadata 오류 음성 대조로 fidelity/거부를 검증한다.

### M4 — 리포트·검증 (Medium)

- `xdet.metrics-report/1.0` JSON과 `xdet.run-manifest/1.0`을 필수, 단위 헤더가 있는 CSV를 선택 산출물로 저장한다.
- `XDET-TC-152~159`와 공통 `XDET-TC-164/166`으로 source, MTF, NPS, line-noise, defect, DQE 실행, export, evidence, invariant를 검증한다.

## 변경 대상

- `Xdet.Engine.Contract`: metric input/result/condition DTO
- `Xdet.Engine.PythonNet`: MTF/NPS/line-noise/defect 위임과 DQE composition service
- `Xdet.Console.App`: 지표별 source panel과 curve/histogram 뷰
- `Xdet.Engine.Tests`: `XDET-TC-152~159`

## 완료 게이트

- [ ] 지표별 입력 source가 분리된다.
- [ ] UI에서 interpolation·지표·판정을 계산하지 않는다.
- [ ] DQE가 골든 `mtf_value_at`+`compute_dqe`로 실행되고 support 밖 외삽이 0건이다.
- [ ] 사용자 제공 실측 MTF/NPS는 strict schema로 실행되고 승인 전 `USER_SUPPLIED_UNVERIFIED`다.
- [ ] JSON/CSV export가 C-20을 통과하고 manifest hash로 source/result가 연결된다.
- [ ] WPF/adapter의 Python `apps.gui` helper 직접 의존이 0건이다.
