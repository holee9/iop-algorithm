---
id: SPEC-CALDOM-001
title: CalibSet 도메인·빔질 서술자 + 교차도메인 게이트
version: 0.1.0
status: implemented
created: 2026-07-11
updated: 2026-07-11
author: drake.lee
priority: high
issue_number: 36
labels: [calibset, calibration-gate, domain, beam-quality, additive, quarantine]
---

# SPEC-CALDOM-001 — CalibSet 도메인·빔질 서술자(descriptor) + 교차도메인 게이트

`common/calibset.py::CalibSet`에 **도메인(domain)** 과 **빔질(beam_quality)** 서술자를 가산(additive)으로 추가하고, 오케스트레이터 진입 게이트(`pipeline/orchestrator.py::_calibration_gate`)가 이를 근거로 **교차도메인 오적용**(예: 의료 RQA5 gain 맵이 NDT 파이프라인에 투입)을 거부하도록 확장한다. PR #35(issue #34)로 확정된 **빔질 2계층 계층화**(계측 RQA5 — 도메인 독립 DQE/MTF/NPS / 응용 — 도메인별 offset·gain·에너지 응답)의 코드 측 후속 작업이며, 그 PR이 이 SPEC으로 명시 이연한 **CalibSet 공통 스키마 문서(SWR-000-10) 갱신**을 함께 소유한다.

- 근거: SWR-000-10(CalibSet 공통 스키마), SWR-000-8(오케스트레이터 단독 조합 권한), SWR-000-5(무단 기본값 대체 금지). 측정 프로토콜 §1(계측 RQA5)·§1b(NDT 응용 E2597)·§5(도메인·빔질 필수 메타). EV-101(DQE@RQA5 계측)·EV-301(dSNRn NDT 응용).
- 완료 정의(DoD): **XDET-TC-060~067 CI 통과** — 서술자 스키마·후방호환 직렬화 왕복·교차도메인 게이트 거부(실행 증거)·무회귀·SAMPLE 라벨링·문서 동기화. 기존 T0 게이트 검사(존재·해상도·kind·panel_id·유효기간)와 기존 테스트 전건 유지.
- 성격: **T0 핵심 계약(CalibSet·오케스트레이터 게이트)에 대한 가산·동작보존 확장**. 새 `CANONICAL_ORDER` 스테이지·새 `CalibKind`·새 `_KIND_BY_STAGE` 배선은 없다.

## HISTORY

- **v0.1.0 (2026-07-11)** — 초안 생성. 6개 요구 그룹(SCHEMA/COMPAT/GATE/SAMPLE/DOC/VALIDATE) EARS 구조 확정. 착수 전 확정 설계 결정:
  1. **서술자 배치 = CalibSet 데이터클래스 전용 필드**(provenance 확장 아님). `domain: CalibDomain = UNSPECIFIED`(신규 str-enum, `CalibKind` enum 선례), `beam_quality: str | None = None`(자유 문자열, `metrics/result.py::MetricCondition.beam_quality` 선례). 근거는 「결정 필요/확인 사항」 1.
  2. **파이프라인 도메인 문맥 원천 = `run_pipeline`의 신규 `domain` 키워드 인자**(기존 `panel_id`/`timestamp` 선택 인자와 동일 패턴, 기본 None). 근거는 「결정 필요/확인 사항」 2.
  3. **게이트 확장은 결정론적·가산**: 교차문맥 도메인 불일치 = 거부, 스테이지 간 지정 도메인 상호 불일치 = 거부, 스테이지 간 지정 beam_quality 상호 불일치 = 거부. 서술자 미지정(UNSPECIFIED/None) 또는 문맥 None = 검사 생략(무회귀).
  4. **SAMPLE CalibSet 라벨링**(issue #29 QUARANTINE 정합): `scripts/ingest_edrogi.py` 샘플 빌더가 도메인 서술자를 명시 각인하되 비권위(non-authoritative) 유지. 기본 라벨은 「결정 필요/확인 사항」 4.
  - status: draft (run 단계 착수 전까지 유지)

## Environment / Assumptions

- Python 3.11+, numpy/scipy float 골든 모델(tech.md). 속도 최적화 금지 — 정확도 단일 목표.
- **기존 코드 사실(작성 전 확인 완료)**:
  - `common/calibset.py`: `CalibSet`는 frozen dataclass, 필드 `panel_id / resolution / valid_from / valid_until / kind / data / provenance`. `validate()`(구조 검사), `save()`(npz + JSON sidecar, meta dict 기록), `load()`(meta 키 복원 후 `validate()`). `CalibKind = {OFFSET, GAIN, DEFECT, LAG, LINE_NOISE, NOISE, SCATTER, OTHER}`. `@MX:ANCHOR` — 전 스테이지가 읽는 고fan-in 핵심 계약(SWR-000-10).
  - `pipeline/orchestrator.py::_calibration_gate`(@178, `run_pipeline`@262에서 호출): 스테이지별 **존재 → `validate()` → `matches_resolution` → kind-스테이지 배선 → 기대 panel_id → 스테이지 간 panel_id 상호일치 → 유효기간(timestamp)** 순 검사. `run_pipeline`은 이미 `panel_id`/`timestamp` 선택 키워드 인자를 가지며, None이면 해당 검사를 생략한다. **본 SPEC의 도메인 검사는 이 위에 동일 정신으로 가산된다.**
  - `metrics/result.py::MetricCondition.beam_quality: str | None`(=`"RQA5"` 예시)가 이미 존재하고 mtf/nps/dqe/lag/ndt 엔진이 `params.get("beam_quality")`로 채운다 → CalibSet의 `beam_quality`는 **같은 이름·같은 타입(자유 문자열)** 을 사용해 계측/캘리브레이션 계층 간 서술자 표기를 일치시킨다.
- **빔질 2계층 (측정 프로토콜 §1/§1b, EV-101/EV-301)**:
  - **domain 허용값**: `medical`(의료, 측정 프로토콜 §1 계열) / `ndt`(측정 프로토콜 §1b, ASTM E2597) / `unspecified`(기본). 닫힌 집합이므로 `CalibDomain` str-enum으로 표현.
  - **beam_quality 값**: 자유 문자열 — `"RQA5"`(계측 참조 빔질, 도메인 독립), `"E2597-..."`(NDT 응용 빔질) 등. 다중 에너지·빔질을 열거 불가하므로 enum이 아닌 자유 문자열(측정 프로토콜 §1b.2).
  - **계층 원칙**: 계측(metrology) 지표(DQE/MTF/NPS)는 고정 RQA5에서 측정해 도메인 무관 비교성을 확보(EV-101), 응용(application) offset/gain·에너지 응답은 도메인별로 다름(EV-301). 본 파이프라인은 응용 계층(offset/gain/…)이므로 domain 서술자가 오적용 방화벽의 1차 근거이다.
- **기본값 = 후방호환의 근간**: `domain=CalibDomain.UNSPECIFIED`, `beam_quality=None`. 기존 직렬화 payload(신규 키 없는 JSON)는 이 기본값으로 로드되어 **모든 기존 CalibSet이 유효**하게 유지된다.
- **QUARANTINE(issue #29) 정합**: 도메인·빔질 서술자는 **메타/라벨 전용**이며 에드로지 샘플 세트로부터 어떤 [B]/[T]/[P] 수치도 역산·피팅하지 않는다. `scripts/ingest_edrogi.py`가 만드는 SAMPLE CalibSet(`panel_id="SAMPLE-EDROGI-16BIT"`)은 도메인 라벨을 받되 비권위로 유지된다(권위 취득 세트는 issue #33). 도메인 라벨은 범주형 라벨이지 수치가 아니므로 REQ-REALDATA-VALIDATE-4 수치-출처 가드의 대상이 아니다.
- **파라미터 정책(HARD)**: 서술자는 CalibSet에 각인되는 캘리브레이션 메타이지 모듈 Params 알고리즘 노브가 아니다. 하드코딩 금지 대상이 아니며(값이 아니라 데이터 라벨), 서술자 자체는 CalibSet 생성 시점(빌더/취득 메타)에 결정된다.

## Requirements (EARS)

### REQ-CALDOM-SCHEMA — CalibSet 서술자 스키마 (SWR-000-10)

- **REQ-CALDOM-SCHEMA-1 (Ubiquitous)** — `CalibSet`은 도메인 서술자 `domain`(신규 `CalibDomain` str-enum, 값 `medical`/`ndt`/`unspecified`)과 빔질 서술자 `beam_quality`(`str | None`)를 **전용 선택 필드**로 보유해야 하며, 기본값은 각각 `CalibDomain.UNSPECIFIED`와 `None`이어야 한다. 이 기본값으로 인해 서술자를 지정하지 않는 기존 호출부의 `CalibSet` 생성은 변경 없이 유효해야 한다. (근거: 측정 프로토콜 §5 도메인·빔질 필수 메타 / 「결정 필요/확인 사항」 1)
- **REQ-CALDOM-SCHEMA-2 (Ubiquitous)** — `CalibSet.validate()`는 구조 검사에 서술자 검사를 가산해야 한다: `domain`은 `CalibDomain` 멤버여야 하고, `beam_quality`는 `None`이거나 비어있지 않은 문자열이어야 한다. 기존 검사(panel_id·resolution·validity·kind·data ndarray)는 그대로 유지한다.
- **REQ-CALDOM-SCHEMA-3 (Ubiquitous)** — 서술자는 CalibSet의 **적용 가능성(applicability) 서술자**로서 `panel_id`/`resolution`과 동일 계열에 놓이며, 생성 이력(`provenance`, 언제·누가 만들었나)과 개념적으로 분리되어야 한다. `provenance`는 확장하지 않는다.

### REQ-CALDOM-COMPAT — 후방호환 + 직렬화 왕복 (SWR-000-10)

- **REQ-CALDOM-COMPAT-1 (Event-Driven)** — WHEN `CalibSet.load()`가 서술자 키(`domain`/`beam_quality`)가 없는 기존(legacy) JSON sidecar를 로드하면, THEN 시스템은 `domain=CalibDomain.UNSPECIFIED`, `beam_quality=None`으로 채워 로드하고 `validate()`를 통과시켜야 한다(무단 실패 금지).
- **REQ-CALDOM-COMPAT-2 (Event-Driven)** — WHEN `domain`/`beam_quality`가 지정된 `CalibSet`이 `save()` 후 `load()`로 왕복되면, THEN 복원된 CalibSet의 `domain`·`beam_quality`는 원본과 동일해야 한다(npz 배열 payload·기존 메타 필드 보존은 불변).
- **REQ-CALDOM-COMPAT-3 (Unwanted)** — IF 서술자 추가가 기존 payload(npz + JSON)의 저장 포맷 또는 기존 메타 키(panel_id/resolution/valid_from/valid_until/kind/data_keys/provenance)의 의미를 바꾸려 하면, THEN 그 변경은 계약 위반으로 거부되어야 한다. 서술자는 meta dict에 신규 키로만 추가되며 기존 키·npz 구조는 불변이다.
- **REQ-CALDOM-COMPAT-4 (Ubiquitous)** — `calibset_id` 문자열 포맷(`panel_id:kind:res:valid_from`)은 변경하지 않는다 — 서술자를 ID에 편입하지 않음으로써 기존 XFrame 이력 엔트리(DATA-4)의 추적 문자열을 안정 유지한다. (근거: 「결정 필요/확인 사항」 3)

### REQ-CALDOM-GATE — 교차도메인 진입 게이트 (SWR-000-8, SWR-000-5)

- **REQ-CALDOM-GATE-1 (Ubiquitous)** — `run_pipeline`은 파이프라인의 **기대 도메인 문맥**을 전달받는 선택 키워드 인자 `domain: CalibDomain | None = None`을 제공해야 하며, 이 인자는 기존 `panel_id`/`timestamp`와 동일하게 `_calibration_gate`로 전달되어 게이트의 교차문맥 도메인 검사의 유일한 입력 원천이 된다. `domain=None`이면 교차문맥 검사를 생략한다(기존 호출부 무회귀). (근거: 「결정 필요/확인 사항」 2)
- **REQ-CALDOM-GATE-2 (Unwanted)** — IF 파이프라인 도메인 문맥이 지정(비-None)되고 어느 스테이지의 CalibSet `domain`이 지정(≠`UNSPECIFIED`)이면서 그 문맥과 다르면, THEN 게이트는 처리를 거부하고 위반 스테이지·CalibSet 도메인·기대 도메인을 명시한 `CalibrationError`를 발생시켜야 한다(무단 기본값 대체 금지). — 의료 RQA5 gain 맵이 NDT 파이프라인에 투입되는 오적용의 방화벽.
- **REQ-CALDOM-GATE-3 (Unwanted)** — IF 서로 다른 두 스테이지의 CalibSet이 모두 도메인을 지정(≠`UNSPECIFIED`)했고 그 값이 상호 불일치하면, THEN 게이트는 처리를 거부하고 두 스테이지·도메인을 명시한 `CalibrationError`를 발생시켜야 한다(기존 panel_id 상호일치 검사와 동일 정신).
- **REQ-CALDOM-GATE-4 (Unwanted)** — IF 서로 다른 두 스테이지의 CalibSet이 모두 `beam_quality`를 지정(비-None)했고 그 값이 상호 불일치하면, THEN 게이트는 처리를 거부하고 두 스테이지·빔질을 명시한 `CalibrationError`를 발생시켜야 한다(예: 한 실행에서 RQA5 맵과 E2597 맵 혼용 차단).
- **REQ-CALDOM-GATE-5 (State-Driven)** — WHILE 어느 CalibSet의 `domain`이 `UNSPECIFIED`이거나 `beam_quality`가 `None`인 동안, 게이트는 그 스테이지를 해당 서술자에 대해 도메인-무관(domain-agnostic)으로 취급하여 서술자 관련 거부 없이 통과시켜야 한다. 기존 게이트 검사(존재·해상도·kind·panel_id·유효기간)의 동작은 서술자 유무와 무관하게 불변이어야 한다(무회귀).

### REQ-CALDOM-SAMPLE — SAMPLE CalibSet 라벨링 (issue #29 QUARANTINE 정합)

- **REQ-CALDOM-SAMPLE-1 (Event-Driven)** — WHEN `scripts/ingest_edrogi.py`의 샘플 CalibSet 빌더(offset/gain/defect)가 CalibSet을 생성하면, THEN 각 CalibSet은 도메인 서술자를 명시 각인해야 한다(무설정 기본값에 의존하지 않고 명시). 빔질은 검증된 계측 근거가 없으므로 `beam_quality=None`으로 둔다. (근거: 「결정 필요/확인 사항」 4)
- **REQ-CALDOM-SAMPLE-2 (Unwanted)** — IF SAMPLE CalibSet의 도메인 라벨이 그 CalibSet을 권위(authoritative)로 승격하거나, 어떤 [B]/[T]/[P] 수치·임계·보정상수의 근거로 사용되면, THEN 이는 QUARANTINE 위반이다. 도메인 라벨은 범주형 메타일 뿐이며 비권위 상태는 `panel_id="SAMPLE-EDROGI-16BIT"` + provenance `sample=true` + REQ-REALDATA-VALIDATE-4 수치-출처 가드로 계속 강제된다.

### REQ-CALDOM-DOC — CalibSet 공통 스키마 문서 갱신 (SWR-000-10, PR #35 이연분 소유)

- **REQ-CALDOM-DOC-1 (Event-Driven)** — WHEN 본 SPEC이 구현되면, THEN CalibSet 공통 스키마 문서(`docs/XDET_SWR_spec_v1.2.md` SWR-000-10 조항) 및 `CalibSet` 데이터클래스 docstring이 도메인·빔질 서술자를 열거하도록 갱신되어야 한다: 필드명·허용값(`medical`/`ndt`/`unspecified`; beam_quality 자유 문자열, RQA5/E2597-class 예시)·기본값·2계층(계측 RQA5 대 응용 E2597) 근거(측정 프로토콜 §1/§1b). 이는 PR #35(issue #34)가 본 SPEC으로 명시 이연한 스키마 문서 변경분이다.
- **REQ-CALDOM-DOC-2 (Ubiquitous)** — 문서의 서술자 정의는 코드(`common/calibset.py`의 `CalibDomain` 값·필드 기본값)와 일치해야 하며, 어느 한쪽만 갱신되어 표류하지 않아야 한다(단일 출처 일관성).

### REQ-CALDOM-VALIDATE — 검증 (XDET-TC-060~067)

- **REQ-CALDOM-VALIDATE-1 (Event-Driven)** — WHEN 스키마·후방호환 시험이 실행되면, THEN 시스템은 서술자 기본값(XDET-TC-060)·legacy JSON 로드 기본화(XDET-TC-061)·지정 서술자 save/load 왕복 보존(XDET-TC-062)을 **실제 실행 증거**(실 구성·실 왕복 후 필드 동등)로 통과시켜야 한다.
- **REQ-CALDOM-VALIDATE-2 (Event-Driven)** — WHEN 게이트 시험이 실행되면, THEN 시스템은 교차도메인 거부(medical CalibSet + ndt 문맥 → `CalibrationError`; 일치 문맥 → 통과, XDET-TC-063)·스테이지 간 도메인/빔질 상호 불일치 거부(XDET-TC-064)·서술자 미지정/문맥 None 무회귀 통과(XDET-TC-065)를 **실제 게이트 실행**(실 거부 발생·실 통과)으로 통과시켜야 한다(공허한 통과 금지).
- **REQ-CALDOM-VALIDATE-3 (Event-Driven)** — WHEN SAMPLE·문서 시험이 실행되면, THEN 시스템은 ingest 샘플 CalibSet의 도메인 서술자 각인 + 비권위 유지(`panel_id="SAMPLE-EDROGI-16BIT"`, `beam_quality=None`, XDET-TC-066)와 SWR-000-10 스키마 문서·docstring의 서술자 열거·코드 일치(XDET-TC-067)를 구조적으로 통과시켜야 한다.

## Exclusions (What NOT to Build)

- **새 파이프라인 스테이지 없음** — 서술자·게이트 확장은 기존 `CalibSet`·`_calibration_gate`에 가산될 뿐, `CANONICAL_ORDER`에 스테이지를 추가하지 않는다.
- **새 `CalibKind`/`_KIND_BY_STAGE` 배선 없음** — domain/beam_quality는 kind와 직교하는 서술자이며 kind-스테이지 배선을 건드리지 않는다.
- **beam_quality→domain 도출 없음** — 게이트는 beam_quality로부터 domain을 유추하지 않는다(취약·비결정 회피). beam_quality는 스테이지 간 상호일치만 결정론적으로 검사하고 그 외에는 기록/추적용 서술자다.
- **파이프라인 beam_quality 문맥 인자 없음** — `run_pipeline`에는 도메인 문맥(`domain`)만 추가한다. beam_quality 단위의 파이프라인 문맥 검사는 도입하지 않는다(파이프라인 문맥의 본질은 도메인).
- **`calibset_id` 포맷 변경 없음** — 서술자를 ID에 편입하지 않아 기존 이력 추적 문자열을 안정 유지한다(REQ-CALDOM-COMPAT-4).
- **모듈 알고리즘 변경 없음** — offset/gain/defect/… 모듈의 수치 처리 로직은 불변. 서술자는 진입 게이트 단계에서만 소비된다.
- **권위 취득 세트 수치 작업 없음** — issue #33 유도 취득 세트의 실측 domain/beam_quality 값 확정·[B] 해소는 별도 SPEC(run/후속). 본 SPEC은 서술자 배관과 게이트 기계장치만 확립한다.
- **직렬화 포맷 교체 없음** — npz + JSON sidecar 규약([P]) 유지. 서술자는 JSON 메타에 신규 키로만 추가.

## 결정 필요/확인 사항

아래 1~3은 **[확정]**(설계 근거 확립, run에서 그대로 구현), 4는 **[확인]**(사용자 오버라이드 여지)이다. run 착수 전 4에 대한 사용자 확인을 권장한다.

1. **[확정] 서술자 배치 = CalibSet 전용 필드 (provenance 아님).** `domain: CalibDomain = UNSPECIFIED` + `beam_quality: str | None = None`을 dataclass 전용 필드로 추가한다.
   - **rationale**: (a) 게이트 검사성 — 전용 필드는 항상 존재하므로 게이트가 `calib.domain`/`calib.beam_quality`를 nested None-guard 없이 읽는다(provenance는 Optional이라 `provenance.domain`은 None일 때 붕괴). (b) 개념 분리 — provenance는 "언제·누가 만들었나"(생성 이력)이고 서술자는 "어디에 적용되나"(적용 가능성)로 `panel_id`/`resolution`과 동일 계열. (c) 선례 — domain은 닫힌 집합이므로 `CalibKind` str-enum 선례를 따른 `CalibDomain`, beam_quality는 열거 불가한 자유 문자열이므로 `metrics/result.py::MetricCondition.beam_quality: str | None` 선례를 따름. (d) 기본값이 기존 CalibSet을 전건 유효 유지.
2. **[확정] 파이프라인 도메인 문맥 원천 = `run_pipeline` 신규 `domain` 키워드 인자.** 기존 `panel_id`/`timestamp` 선택 인자와 동일 패턴으로 `_calibration_gate`에 전달, 기본 None = 검사 생략.
   - **대안 기각**: (a) Params 키 — Params는 스테이지별 모듈 알고리즘 노브이며 실행 단위(run-level) 도메인 문맥을 스테이지별 Params에 싣는 것은 부자연·네임스페이스 오염. (b) `PipelineDefinition` 필드 — PipelineDefinition은 frozen `stages`(순서 단독 권한)이며 취득 문맥을 순서 권한과 혼합하고 `full()` classmethod가 도메인을 알 수 없음. (c) 채택안(kwarg)이 `panel_id`(실행 단위 기대 패널)·`timestamp`(실행 단위 기대 시각)와 정확히 동형이며 최소·일관.
3. **[확정] `calibset_id`·게이트 결정론.** calibset_id 포맷 불변(추적 안정). 게이트 신규 검사는 전부 결정론(지정+불일치=거부 / 미지정=생략) — "경고 또는 거부" 류 분기 없음(house 규칙).
4. **[확인] SAMPLE CalibSet 도메인 라벨의 기본값.** 기본안 = **`medical`**. 근거: 샘플 취득이 아크릴(PMMA) 팬텀·nps·ghost·최소선량선형 등 **의료/IEC 계열** 셋업이고(측정 프로토콜 §1, `_CATEGORY_BY_FOLDER`의 `아크릴`), 도메인 라벨은 범주형 메타이지 수치가 아니라 QUARANTINE(수치 가드) 대상이 아니며, `medical` 라벨은 샘플 fixture로 교차도메인 게이트 거부(TC-063)를 실제로 시연 가능하게 한다. **대안 = `unspecified`**(가장 보수적 — 샘플을 도메인 게이팅에서 완전 배제, "아무것도 주장하지 않음"). 어느 쪽이든 `beam_quality=None`(검증된 RQA5 근거 없음)·비권위 상태 불변. run 착수 전 사용자 선택 필요.
