---
id: SPEC-XGUI-NDT
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
labels: [xgui, ndt, iqi, snrn, wpf]
---

# SPEC-XGUI-NDT — 구현 계획

## 0. 구현 착수 전제

이 계획은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 마스터 plan M0.5를 상속한다. 사용자 승인 기록, 기준선 동결, `implementation_authorized=true`가 모두 존재하기 전에는 아래 마일스톤의 소스·XAML·테스트·패키지 변경을 시작하지 않는다. 내부 감사 통과나 기술적 구현 가능성만으로 이 전제를 충족했다고 보지 않는다.

진입 증거는 승인된 v0.5.1 기준선, 요구사항-인수-TC 추적 차이 0, 미결정 임계 0, 현재 worktree/commit을 가리키는 최종 감사 기록이다. 규범 변경이 발생하면 작업을 멈추고 기준선 재승인을 수행한다.

구현 루트는 `apps/xdet-console/`이다.

## 기술 방향

NDT는 pipeline stage가 아니라 metrics engine 소비 탭이다. WPF는 dedicated `IXdetEngine` methods로 frame/ROI/profile/metadata를 전달하고 SRb, SNR, SNRn, IQI, thickness 결과만 표시한다. PythonNet adapter만 `metrics.ndt`를 호출한다.

## 마일스톤

### M1 — 입력과 프로필 계약 (High)

- 상주 폴더 브라우저와 sequence 입력을 연결한다.
- line profile은 정수 좌표/nearest sampling만 허용한다.
- subpixel interpolation은 engine-owned 공개 계약이 생길 때까지 제외한다.

### M2 — SNR/SNRn와 IQI (High)

- `compute_snr`, `SNRnAccumulator`, duplex/single-wire IQI 진입점을 seam으로 노출한다.
- typed surface는 `ComputeNdtSnr(NdtSnrRequest)`, `StartNdtSession(NdtSessionRequest)`, `UpdateNdtSession(NdtShotRequest)`, `CloseNdtSession(session_id)`, `ReadDuplexIqi`, `ReadSingleWireIqi`, `CorrectThickness`, `BuildNdtReport`로 고정한다.
- session 결과는 `session_id`, shot_index, frame_count, snr, snrn, srb_um, target_reached, warnings를 보존하고 거부 shot은 상태를 바꾸지 않는다.
- SAMPLE nps_flat은 SNR-only sanity로 제한한다. SRb 또는 SNRn을 꾸며내지 않는다.
- 정본 SRb 입력이 있을 때만 SNRn을 활성화한다.

### M3 — 두께·리포트 (Medium)

- thickness correction과 IQI report를 엔진 반환값으로 표시한다.
- JSON을 정본 리포트로, CSV를 선택 산출물로 저장한다.
- flattened frame이 있을 때만 raw/JSON frame export를 수행한다.
- `xdet.ndt-report/1.0`과 `xdet.run-manifest/1.0`을 저장하고 input/params/output hash를 연결한다.

### M4 — 검증 (High)

- 기존 알고리즘 증거 `XDET-TC-018/019`를 보존하고 GUI-E2E는 `XDET-TC-144~151` 전체를 사용한다.

### M-COVERAGE — 7개 action + accumulator session

- duplex SRb, SNR, SNRn, thickness, single-wire, IQI report를 각각 dedicated engine method로 구현한다.
- accumulator update/current/shot log/target transition을 session DTO로 구현하고 rejected-shot state no-op를 시험한다.
- XDET-TC-144~151 전체를 사용해 action, session, report/export, error/cancel/evidence를 검증한다.

## 변경 대상

- `Xdet.Engine.Contract`: NDT input/profile/result/report DTO
- `Xdet.Engine.PythonNet`: `metrics.ndt` 공개 API 위임
- `Xdet.Console.App`: NDT 탭과 shot timeline
- `Xdet.Engine.Tests`: `XDET-TC-144~151`

## 완료 게이트

- [ ] SAMPLE에서 SNRn/SRb를 생성하지 않는다.
- [ ] 프로필 보간 산술이 UI에 없다.
- [ ] JSON 리포트와 선택 CSV가 C-20을 통과하고 run manifest hash로 연결된다.
- [ ] WPF/adapter에서 Python `apps.gui` helper 직접 의존이 0건이다.
- [ ] core TC와 GUI-E2E TC의 역할이 구별된다.
