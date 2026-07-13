---
id: SPEC-XGUI-DENOISE
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
labels: [xgui, denoise, noise-model, wpf]
---

# SPEC-XGUI-DENOISE — 구현 계획

## 0. 구현 착수 전제

이 계획은 `../SPEC-XGUI-MASTER/baseline-control.md`의 G0와 마스터 plan M0.5를 상속한다. 사용자 승인 기록, 기준선 동결, `implementation_authorized=true`가 모두 존재하기 전에는 아래 마일스톤의 소스·XAML·테스트·패키지 변경을 시작하지 않는다. 내부 감사 통과나 기술적 구현 가능성만으로 이 전제를 충족했다고 보지 않는다.

진입 증거는 승인된 v0.5.1 기준선, 요구사항-인수-TC 추적 차이 0, 미결정 임계 0, 현재 worktree/commit을 가리키는 최종 감사 기록이다. 규범 변경이 발생하면 작업을 멈추고 기준선 재승인을 수행한다.

구현 루트는 `apps/xdet-console/`이다.

## 기술 방향

Denoise 탭은 채워진 `CalibSet(NOISE)`와 프레임을 C# seam으로 전달한다. VST, BM3D/NLM, 역변환, NPS, SNR은 모두 Python 엔진을 호출하며 UI에는 계산 코드를 두지 않는다.

## 마일스톤

### M1 — Noise 모델 조달 (High)

- 정본 경로는 다중 선량 flat을 `fit_noise_model`에 전달한다.
- 선언 alpha/sigma는 test/demo용 DTO 패키징으로만 허용한다.
- 빈 NOISE CalibSet은 실행 전에 명시적으로 거부한다.

### M2 — Denoise 실행과 뷰 (High)

- `required_params(params)` 결과로 method-dependent form을 구성한다.
- before/after/diff, mask, resolved alpha/sigma, method, clamp rate를 엔진 반환값에서 표시한다.
- in-GUI denoiser bypass 또는 bias-vs-lambda 계산은 구현하지 않는다.

### M3 — 지표·조합·저장 (Medium)

- NPS와 SNR을 metrics engine에 위임한다.
- 상류·하류 조합은 generic pipeline seam으로 실행하고 NOISE CalibSet을 명시 주입한다.
- frame/mask artifact와 run manifest를 저장하고 hash/round-trip을 검증한다.

### M4 — 검증 (High)

- `XDET-TC-120~127`로 method schema, BM3D/NLM, noise gate, 실행/진단, metrics, user-input/evidence, export/guard를 검증한다.

### M-COVERAGE — BM3D/NLM과 noise calibration

- selector 변경마다 golden `required_params` 결과로 form을 갱신한다.
- BM3D와 NLM을 각각 golden-direct fidelity로 검증하고 124~127을 method/negative/evidence 시나리오로 사용한다.
- `fit_noise_model` builder와 strict 외부 NOISE CalibSet import를 동일 typed calibration 경계로 연결한다.

## 변경 대상

- `Xdet.Engine.Contract`: NoiseCalib·DenoiseParams·diagnostic DTO
- `Xdet.Engine.PythonNet`: noise model/denoise/metric 위임
- `Xdet.Console.App`: Denoise 탭
- `Xdet.Engine.Tests`: `XDET-TC-120~127`

## 완료 게이트

- [ ] alpha/sigma 결여가 무단 기본값 없이 거부된다.
- [ ] UI에는 VST·NPS·SNR 산술이 없다.
- [ ] 포화 픽셀과 mask 의미가 보존된다.
- [ ] QUARANTINE과 C-20이 통과한다.
- [ ] WPF/adapter의 Python `apps.gui` helper 직접 의존이 0건이다.
