---
id: SPEC-XGUI-CALIB
version: 0.5.1
status: planned
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
priority: high
issue_number: 58
labels: [xgui, calibration, wpf, verification]
---

# SPEC-XGUI-CALIB — 구현 계획

## 0. 구현 착수 전제

이 계획은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 마스터 plan M0.5를 상속한다. 사용자 승인 기록, 기준선 동결, `implementation_authorized=true`가 모두 존재하기 전에는 아래 마일스톤의 소스·XAML·테스트·패키지 변경을 시작하지 않는다. 내부 감사 통과나 기술적 구현 가능성만으로 이 전제를 충족했다고 보지 않는다.

진입 증거는 승인된 v0.5.1 기준선, 요구사항-인수-TC 추적 차이 0, 미결정 임계 0, 현재 worktree/commit을 가리키는 최종 감사 기록이다. 규범 변경이 발생하면 작업을 멈추고 기준선 재승인을 수행한다.

## 기술 방향

구현 대상은 `apps/xdet-console/` C# WPF 앱이다. WPF는 입력과 파라미터를 DTO로 전달하고, `Xdet.Engine.PythonNet`이 동결 Python 빌더·오케스트레이터를 호출한다. OC/GC/BPM 계산, 스테이지 순서, 차이 영상과 통계는 UI에서 계산하지 않는다.

## 마일스톤

### M1 — Build 계약 (High)

- Offset·Gain·Defect 입력 스택과 식별 메타데이터를 Contract DTO로 정의한다.
- PythonNet 어댑터가 범용 `metrics.defect_map.build_defect_map`과 catalog의 lag/noise/scatter builder를 호출한다. `scripts.ingest_edrogi.build_offset_calibset`, `scripts.ingest_edrogi.build_gain_calibset`, `scripts.ingest_edrogi.build_defect_calibset`은 등록 edrogi SAMPLE preset에서만 별도 호출하며 외부 사용자 입력에는 사용하지 않는다.
- 스택 기반 BPM은 전용 고급 패널에서 임계값을 받고 반환 직후 `CalibSet.validate()`를 수행한다.

### M2 — Apply와 비교 (High)

- WPF는 Offset→Gain→Defect 전체 또는 정렬된 부분수열을 오직 `IXdetEngine.RunPipeline(PipelineRunRequest)`으로 실행한다.
- before/after/diff, 누적 mask, probe, 엔진 진단을 공통 비교 화면에 바인딩한다.
- `validation_mode` 중간 프레임을 각 스테이지별 fidelity 대조에 사용한다.

### M3 — 저장과 재열기 (Medium)

- frame artifact, mask artifact, run manifest를 사용자 폴더에 저장하고 hash/round-trip을 검증한다.
- mask가 있으면 `<name>_result_mask.raw`를 함께 저장하고 uint8 flag map을 JSON에 기록한다.
- C-20 거부와 raw 재열기 픽셀 동일성을 검증한다.

### M4 — 검증 (High)

- `XDET-TC-096~103`을 Contract·adapter·ViewModel·WPF E2E 계층에 배치한다.
- 등록 SAMPLE은 전체 offset→gain→defect 실행 sanity만 수행하며 수치 골든으로 승격하지 않는다.

### M-COVERAGE — 전체 builder/import 구현

- defect map, lag IRF, noise model, scatter parametric/sample-fit를 기능별 typed service로 구현한다.
- offset/gain/geometry는 CalibSet import/validate workflow를 제공하고 존재하지 않는 builder를 창작하지 않는다.
- 모든 builder source를 `xdet.input-set/1.0` calibration-series로 hash하고 populated payload/fit diagnostics를 비교한다.
- XDET-TC-096~103을 모두 사용해 builder 6연산, import, apply/fidelity, export/guard를 검증한다.

## 변경 대상

- `apps/xdet-console/src/Xdet.Engine.Contract/`: calibration DTO와 build/apply 결과 계약
- `apps/xdet-console/src/Xdet.Engine.PythonNet/`: 동결 Python 호출 어댑터
- `apps/xdet-console/src/Xdet.Console.App/`: Calibration 탭과 공통 비교 화면
- `apps/xdet-console/tests/Xdet.Engine.Tests/`: `XDET-TC-096~103`

## 완료 게이트

- [ ] Build 3종과 전체 조합이 engine seam을 통해서만 실행된다.
- [ ] 중간 프레임까지 Python 직접 결과와 fidelity가 일치한다.
- [ ] UI/Contract/PythonNet에 보정 산술이 없다.
- [ ] C-20·QUARANTINE·mask export 계약이 통과한다.
