---
id: SPEC-XGUI-DENOISE
version: 0.5.1
status: completed
document_status: internally_reviewed
approval_state: pending_user
implementation_authorized: false
created: 2026-07-12
updated: 2026-07-13
author: drake.lee
---

# SPEC-XGUI-DENOISE 리서치 기록

## 조사 범위와 사실

- `modules.denoise.required_params`는 선택한 method에 따라 필수 Params를 동적으로 반환한다.
- `modules.denoise.process`는 각 method의 Params와 NOISE CalibSet을 소비한다.
- BM3D와 NLM은 서로 다른 고급 파라미터 집합을 가지므로 고정 공통 폼만으로는 유효한 요청을 만들 수 없다.
- `metrics.noise_model.fit_noise_model`, `metrics.nps.compute_nps`, `metrics.ndt.compute_snr`는 독립 golden 작업이다.
- 공개 API에는 denoiser-bypass VST 진단이 없으므로 GUI가 해당 수학을 새로 만들지 않는다.

## 확정 결정

- method selector 변경 시 `required_params` 결과로 입력 schema와 validation을 재구성한다.
- 사용자 선택 NOISE CalibSet과 provenance를 요청에 명시한다.
- NPS·SNR·noise model은 engine 결과만 표시하고 UI에서 재계산하지 않는다.
- BM3D, NLM, noise model fit, 사용자 입력/오류 흐름까지 `XDET-TC-120~127` 전체로 검증한다.

## v0.5 초기 문서 통제 재검토

- v0.5 초기 검토는 이 문서가 기록한 Python golden 사실이나 알고리즘 의미를 바꾸지 않는다.
- 구현 전제는 `../SPEC-XGUI-MASTER/baseline-control.md` G0, 요구사항·TC·증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다.
- 사용자 승인과 기준선 동결 전에는 이 조사 결과를 근거로 소스·XAML·테스트 구현을 시작하지 않는다.
