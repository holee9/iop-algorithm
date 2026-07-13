---
id: SPEC-XGUI-LAG
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
labels: [xgui, lag, sequence, wpf]
---

# SPEC-XGUI-LAG — 구현 계획

## 0. 구현 착수 전제

이 계획은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 마스터 plan M0.5를 상속한다. 사용자 승인 기록, 기준선 동결, `implementation_authorized=true`가 모두 존재하기 전에는 아래 마일스톤의 소스·XAML·테스트·패키지 변경을 시작하지 않는다. 내부 감사 통과나 기술적 구현 가능성만으로 이 전제를 충족했다고 보지 않는다.

진입 증거는 승인된 v0.5.1 기준선, 요구사항-인수-TC 추적 차이 0, 미결정 임계 0, 현재 worktree/commit을 가리키는 최종 감사 기록이다. 규범 변경이 발생하면 작업을 멈추고 기준선 재승인을 수행한다.

구현 루트는 `apps/xdet-console/`이다.

## 기술 방향

Lag는 프레임 단위 모듈이 아니라 상태형 시퀀스 기능이다. WPF는 정렬된 프레임 목록과 ROI만 전달하며, IRF 피팅·상태 진행·lag 지표는 Python 엔진이 담당한다. 시퀀스마다 새 `LagCorrector`를 만드는 경계도 어댑터가 보장한다.

## 마일스톤

### M1 — 시퀀스 입력과 IRF Build (High)

- 상주 폴더 브라우저가 형제 raw를 자연 순서로 묶어 시퀀스로 제안한다.
- 합성 다중 노출 step-response를 `fit_lag_irf`에 전달해 `CalibSet(LAG)`를 만든다.
- 단일 노출·비수렴·결손 IRF 오류를 그대로 표면화한다.

### M2 — Apply와 상태 격리 (High)

- WPF는 `IXdetEngine.RunSequence(SequenceRunRequest)`를 한 번 호출하고 PythonNet adapter가 `run_sequence`와 fresh registry를 소유한다.
- 포화 픽셀 보존, 프레임 간 상태 전달, 시퀀스 간 상태 초기화를 검증한다.
- 탭은 standalone lag 시퀀스에 집중하고 상류 조합은 마스터 Pipeline 실행 화면에 둔다.

### M3 — 시퀀스 검증 화면 (Medium)

- frame scrubber, engine-returned first-frame lag, ghost CNR, 엔진 통계 신호 곡선을 표시한다.
- float32/float64 진단 차이를 엔진 반환값으로 나란히 표시한다.
- 잘못된 ROI와 정착 tail 부재를 명시 오류로 안내한다.

### M4 — 저장·검증 (High)

- 인덱스를 유지한 raw/JSON/mask 일괄 저장을 구현한다.
- `XDET-TC-104~111`으로 로딩·피팅·상태·지표·저장·SAMPLE sanity를 검증한다.

### M-STATE — 명시 상태 lifecycle

- fresh-run, snapshot, restore를 서로 다른 session command로 구현한다.
- `serialize_state/load_state`를 실제 호출하고 snapshot hash·source run·restore event를 manifest에 기록한다.
- first-frame lag, ghost CNR, IRF fit을 독립 typed action으로 노출한다.
- XDET-TC-104~111에 sequence, state, metrics, IRF, export, cancel/fidelity를 모두 배정한다.

## 변경 대상

- `Xdet.Engine.Contract`: sequence/IRF/lag result DTO
- `Xdet.Engine.PythonNet`: `fit_lag_irf`, `run_sequence`, metric 위임
- `Xdet.Console.App`: Lag 탭, scrubber, 곡선과 ROI 안내
- `Xdet.Engine.Tests`: `XDET-TC-104~111`

## 완료 게이트

- [ ] 시퀀스 간 상태 누출이 없다.
- [ ] UI에서 lag/ghost/곡선 값을 계산하지 않는다.
- [ ] 결손 IRF와 부적합 ROI가 무단 기본값 없이 거부된다.
- [ ] C-20과 QUARANTINE이 통과한다.
- [ ] sequence export는 frame artifact들과 ordered hash를 가진 run manifest를 생성한다.
- [ ] WPF/adapter의 Python `apps.gui` helper 직접 의존은 0건이다.
