---
id: SPEC-CALDOM-001
title: CalibSet 도메인·빔질 서술자 + 교차도메인 게이트
version: 0.1.0
status: draft
created: 2026-07-11
updated: 2026-07-11
author: drake.lee
issue_number: 36
---

# SPEC-CALDOM-001 구현 계획 (초안) — CalibSet domain/beam_quality 서술자 + 교차도메인 게이트

> 상태: **draft** (run 단계 착수 전까지 유지). EARS 확정본은 [spec.md](./spec.md), 인수 기준은 [acceptance.md](./acceptance.md) 참조.

## 0. 확정된 설계 결정 (상세 근거는 spec.md 「결정 필요/확인 사항」)

1. **서술자 배치 = CalibSet 전용 필드** — `domain: CalibDomain(신규 str-enum)`, `beam_quality: str | None`. provenance 확장 아님. (확정)
2. **파이프라인 도메인 문맥 = `run_pipeline` 신규 `domain` kwarg** — 기존 `panel_id`/`timestamp` 패턴 동형, 기본 None = 검사 생략. (확정)
3. **게이트 확장 = 결정론·가산** — 교차문맥/스테이지-상호 도메인·빔질 불일치 = 거부, 미지정 = 생략(무회귀). (확정)
4. **SAMPLE 라벨링** — ingest 샘플 빌더가 도메인 명시 각인, 비권위 유지. 기본 라벨 `medical`은 사용자 **확인 대상**(대안 `unspecified`). (확인)

## 1. 개요

PR #35(issue #34)로 확정된 빔질 2계층 계층화(계측 RQA5 — 도메인 독립 / 응용 — 도메인별)의 코드 측 후속. `common/calibset.py::CalibSet`에 domain/beam_quality 서술자를 가산하고, `pipeline/orchestrator.py::_calibration_gate`가 교차도메인 오적용을 거부하도록 확장하며, PR #35가 이연한 SWR-000-10 스키마 문서 갱신을 소유한다. 완료 정의: **XDET-TC-060~067 CI 통과** + 기존 T0 게이트·기존 테스트 전건 유지. 성격: T0 핵심 계약(CalibSet·게이트)에 대한 **가산·동작보존** 확장.

## 2. 기술 스택

| 항목 | 선택 | 근거 |
|---|---|---|
| 언어/런타임 | Python 3.11+ | tech.md |
| 대상 파일 | `common/calibset.py`(서술자·직렬화), `pipeline/orchestrator.py`(게이트·kwarg), `scripts/ingest_edrogi.py`(SAMPLE 라벨), `docs/XDET_SWR_spec_v1.2.md`(SWR-000-10) | spec.md |
| enum 선례 | `CalibKind` str-enum → `CalibDomain` str-enum | 기존 코드 |
| 자유문자열 선례 | `metrics/result.py::MetricCondition.beam_quality: str | None` | 기존 코드 |
| 직렬화 | 기존 npz + JSON sidecar([P]) 유지, JSON 메타에 신규 키만 추가 | SWR-000-10, COMPAT |
| 시험 프레임워크 | pytest, `uv run`(L#4), Korean 출력 `PYTHONIOENCODING=utf-8` | tech.md |

원칙: **가산·동작보존**. 기존 게이트 5검사·기존 직렬화 포맷·기존 `CalibKind`·`calibset_id` 포맷 불변. 서술자는 값이 아니라 라벨이므로 하드코딩 금지 대상 아님.

## 3. 작업 분해 (요구 그룹 6)

### M1 — CalibSet 서술자 스키마 (REQ-CALDOM-SCHEMA)
- 신규 `class CalibDomain(str, Enum)`: `MEDICAL="medical"` / `NDT="ndt"` / `UNSPECIFIED="unspecified"`.
- `CalibSet`에 전용 필드 추가: `domain: CalibDomain = CalibDomain.UNSPECIFIED`, `beam_quality: str | None = None` (data/provenance 뒤, 기본값 있으므로 위치 안전).
- `validate()`에 서술자 구조 검사 가산: domain이 `CalibDomain` 멤버, beam_quality가 None 또는 비어있지 않은 str. 기존 검사 불변.
- provenance는 손대지 않음(적용 가능성 서술자 ≠ 생성 이력).

### M2 — 후방호환 직렬화 (REQ-CALDOM-COMPAT)
- `save()`: meta dict에 `"domain": self.domain.value`, `"beam_quality": self.beam_quality` 신규 키 추가. 기존 키·npz 구조 불변.
- `load()`: `CalibDomain(meta.get("domain", "unspecified"))`, `meta.get("beam_quality")`로 복원 → legacy JSON(키 부재) 자동 기본화.
- `calibset_id` 포맷 불변(서술자 미편입).
- 왕복 보존: 지정 서술자 save→load 동등.

### M3 — 교차도메인 진입 게이트 (REQ-CALDOM-GATE)
- `run_pipeline` 시그니처에 `domain: CalibDomain | None = None` 선택 키워드 인자 추가 → `_calibration_gate(..., domain=domain)`로 전달(기존 `panel_id`/`timestamp` 전달 라인과 동형).
- `_calibration_gate` 루프에 가산 검사(기존 5검사 뒤):
  - 교차문맥: `domain is not None and calib.domain != UNSPECIFIED and calib.domain != domain` → `CalibrationError`.
  - 스테이지 상호(도메인): 직전까지 관측된 지정 도메인과 현재 지정 도메인 불일치 → `CalibrationError`(panel_id 상호검사 `seen_panel` 패턴 재사용, `seen_domain` 추가).
  - 스테이지 상호(빔질): 관측된 비-None beam_quality와 현재 비-None beam_quality 불일치 → `CalibrationError`(`seen_beam` 추가).
- 미지정(UNSPECIFIED/None)·문맥 None → 해당 검사 생략(무회귀). 기존 5검사 순서·의미 불변.

### M4 — SAMPLE CalibSet 라벨링 (REQ-CALDOM-SAMPLE)
- `scripts/ingest_edrogi.py`의 `build_offset_calibset`/`build_gain_calibset`/`build_defect_calibset`가 `domain=<확정 라벨>`(기본안 `CalibDomain.MEDICAL`, 사용자 확인 대상)로 CalibSet 생성. `beam_quality`는 미설정(None).
- 비권위 표식(panel_id SAMPLE·provenance sample=true) 불변. 도메인 라벨은 범주형 메타 — REQ-REALDATA-VALIDATE-4 수치 가드 비대상.

### M5 — 스키마 문서 갱신 (REQ-CALDOM-DOC)
- `docs/XDET_SWR_spec_v1.2.md` SWR-000-10 조항: CalibSet 스키마 열거에 domain(medical/ndt/unspecified)·beam_quality(자유문자열, RQA5/E2597 예시) 서술자와 2계층 근거(§1/§1b) 추가. PR #35 이연분 소유.
- `common/calibset.py` `CalibSet` docstring: 서술자 필드 문서화. 코드↔문서 일치(표류 금지).

### M6 — 검증 (REQ-CALDOM-VALIDATE)
- XDET-TC-060~067 pytest 케이스: 스키마·후방호환·왕복·교차도메인 거부·상호 불일치 거부·무회귀·SAMPLE·문서동기화. 전부 실제 실행 증거(실 왕복·실 거부·실 통과), 공허한 통과 금지(L#1).

## 4. EARS 구조 설계 (확정본은 spec.md)

6개 그룹: **SCHEMA**(서술자 필드·validate) / **COMPAT**(legacy 로드·왕복·포맷 불변·calibset_id 불변) / **GATE**(kwarg 문맥 원천·교차문맥 거부·상호 도메인 거부·상호 빔질 거부·미지정 통과) / **SAMPLE**(ingest 라벨·비권위) / **DOC**(SWR-000-10 문서·코드 일치) / **VALIDATE**(TC-060~067). Unwanted REQ는 전부 결정론(지정+불일치=거부, 미지정=생략) — 분기 없음.

## 5. 리스크 분석

| 리스크 | 완화 | 우선순위 |
|---|---|---|
| 핵심 계약(CalibSet @MX:ANCHOR) 변경이 전 소비자 파급 | 서술자는 기본값 있는 전용 필드 — 기존 생성/직렬화/게이트 전건 무변경, 신규 검사는 지정+문맥 있을 때만 발화 | High |
| legacy 직렬화 payload 로드 실패 | `load()`가 `meta.get(..., 기본)`로 키 부재 흡수, XDET-TC-061이 실 legacy JSON 로드로 증명 | High |
| 게이트 무회귀 위반(기존 테스트 깨짐) | 신규 검사는 기존 5검사 뒤 가산·미지정 생략, 기존 게이트 테스트 전건 유지(XDET-TC-065) | High |
| QUARANTINE 위반(샘플 라벨이 권위화) | 라벨은 범주형 메타(수치 아님), 비권위 표식·수치 가드 불변, 라벨의 수치-비도출 명시 | Medium |
| beam_quality→domain 취약 유추 유입 | Exclusion 명시 — beam_quality는 상호일치만, domain 유추 금지 | Medium |
| 코드↔문서 표류 | REQ-CALDOM-DOC-2 단일 출처 일관성 + XDET-TC-067 구조 검사 | Medium |

## 6. 마일스톤 (우선순위 기반, 시간 추정 없음)

- **Priority High**: M1(스키마) → M2(직렬화) → M3(게이트). 이 순서가 교차도메인 거부(핵심 가치)의 전제.
- **Priority Medium**: M4(SAMPLE 라벨) — M1 완료 후 가능. M5(문서) — M1/M2 확정 후.
- **Priority Medium**: M6(검증) — M1~M5 통합 후 XDET-TC-060~067 CI 실동작으로 DoD 판정.
- 순서 원칙: 서술자 스키마(M1) 확정 후 나머지 착수. 문서(M5)는 코드 값 확정 후.

## 7. 검증 전략 — XDET-TC-060~067

- **TC-060 스키마**: 서술자 기본값(UNSPECIFIED/None) + 기존 생성 무변경.
- **TC-061 legacy 로드**: 신규 키 없는 JSON → domain=unspecified/beam_quality=None 로드·validate 통과.
- **TC-062 왕복**: 지정 서술자 save→load 동등 + npz/기존 메타 보존.
- **TC-063 교차도메인**: medical CalibSet + ndt 문맥 → `CalibrationError`(음성); 일치 문맥 → 통과(양성).
- **TC-064 상호 불일치**: 스테이지 간 지정 도메인 불일치 → 거부; 스테이지 간 지정 beam_quality 불일치 → 거부.
- **TC-065 무회귀**: 서술자 미지정/문맥 None → 통과, 기존 게이트 테스트 전건 green.
- **TC-066 SAMPLE**: ingest 샘플 CalibSet 도메인 각인 + 비권위(panel_id SAMPLE, beam_quality None).
- **TC-067 문서 동기화**: SWR-000-10 문서·docstring이 서술자 열거 + 코드 값 일치(구조 검사).
- **DoD**: TC-060~067 CI 자동 통과 + 기존 T0 게이트·기존 테스트 전건 유지. acceptance.md에 Given-When-Then(S1~S6)·엣지 케이스(EC)·품질 게이트 상세.
- 명령 예시는 전부 `uv run`, Korean 출력 `PYTHONIOENCODING=utf-8`(L#4).
