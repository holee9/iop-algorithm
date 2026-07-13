---
id: SPEC-XSEAM-002
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
labels: [xseam, research, exhaustive-contract, pythonnet]
---

# SPEC-XSEAM-002 리서치 기록

## 조사 범위

- `pipeline/orchestrator.py`, `pipeline/sequence.py`, `pipeline/tier.py`
- `modules/registry.py`, 각 module의 `required_params`와 상태 API
- `metrics/`의 frame·profile·series·session·builder API
- C# Contract, PythonNet adapter, WPF ViewModel의 현재 호출 경계

## 확인된 사실

- Python `run_pipeline`은 ordered stage subset, calibration gate, params, validation intermediates를 지원한다.
- 현재 C# `IXdetEngine.RunPipeline`은 offset→gain 고정 DTO인 부분 구현이므로 전 알고리즘 seam이 아니다.
- lag는 동일 `LagCorrector` 인스턴스를 sequence 동안 재사용해야 하며 snapshot/restore는 `serialize_state`와 `load_state`를 사용한다.
- calibration builder, DQE series composition, NDT accumulator, tier 결정·실행·계측은 단일-frame pipeline으로 표현할 수 없다.

## 확정 결정

- Contract는 9개 typed family와 공통 request/result envelope를 제공한다.
- Python qualified EntryPoint, canonical FeatureId, ParamSchema, InputSet, provenance, availability, evidence grade를 manifest에 함께 기록한다.
- ordered pipeline의 순서·calibration 대체·DSP 계산·DQE 보간은 Python engine이 소유한다. C#은 입력 검증·직렬화·표시를 담당한다.
- final과 validation intermediate는 stage-by-stage fidelity로 비교한다.
- user-supplied 입력은 등록 데이터 부재와 독립적으로 실행하며 결과 증거 등급을 `USER_SUPPLIED_UNVERIFIED`로 시작한다.
- catalog↔manifest↔Contract handler↔GUI command↔TC의 집합 차이는 자동 시험에서 0이어야 한다.

## v0.5 초기 문서 통제 재검토

- v0.5 초기 검토는 이 문서가 기록한 Python golden 사실이나 알고리즘 의미를 바꾸지 않는다.
- 구현 전제는 `../SPEC-XGUI-MASTER/baseline-control.md` G0, 요구사항·TC·증거 연결은 `../SPEC-XGUI-MASTER/traceability-matrix.md`를 따른다.
- 사용자 승인과 기준선 동결 전에는 이 조사 결과를 근거로 소스·XAML·테스트 구현을 시작하지 않는다.
