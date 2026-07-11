# SPEC-CALDOM-001 — 인수 기준 (Acceptance Criteria)

DoD: **XDET-TC-060~067 CI 통과** — CalibSet domain/beam_quality 서술자 스키마·후방호환 직렬화 왕복·교차도메인 게이트 거부(실행 증거)·무회귀·SAMPLE 라벨링·SWR-000-10 문서 동기화. 모든 기준은 관측 가능(테스트 출력·실 거부 발생·실 왕복 동등·구조 검사 결과)해야 하며, 공허한 통과("예외 안 남")는 불충분하다(L#1). 명령 예시는 `uv run`, Korean 출력은 `PYTHONIOENCODING=utf-8`(L#4).

## Given-When-Then 시나리오

### Scenario 1 — 서술자 스키마·기본값 (REQ-CALDOM-SCHEMA, XDET-TC-060)
- **Given** `common/calibset.py`에 `CalibDomain` str-enum(medical/ndt/unspecified)과 `CalibSet`의 전용 필드 `domain`(기본 `UNSPECIFIED`)·`beam_quality`(기본 `None`)가 존재한다.
- **When** 서술자를 지정하지 않고 기존 방식대로 `CalibSet(panel_id, resolution, valid_from, valid_until, kind, data, provenance)`를 생성하고 `validate()`를 호출한다.
- **Then** 생성이 성공하고 `domain == CalibDomain.UNSPECIFIED`, `beam_quality is None`이며 `validate()`가 통과한다. `domain=CalibDomain.MEDICAL, beam_quality="RQA5"`를 지정한 생성도 `validate()`를 통과한다.

### Scenario 2 — 후방호환 legacy 로드 (REQ-CALDOM-COMPAT-1, XDET-TC-061)
- **Given** 서술자 키(`domain`/`beam_quality`)가 없는 기존(legacy) JSON sidecar + npz 쌍이 디스크에 있다(신규 필드 도입 이전 포맷).
- **When** `CalibSet.load(path)`로 로드한다.
- **Then** 로드가 성공하고 `domain == CalibDomain.UNSPECIFIED`, `beam_quality is None`으로 채워지며 `validate()`를 통과한다. 무단 실패가 발생하지 않는다.

### Scenario 3 — 직렬화 왕복 보존 (REQ-CALDOM-COMPAT-2/3/4, XDET-TC-062)
- **Given** `domain=CalibDomain.NDT, beam_quality="E2597-classA"`를 지정한 `CalibSet`(payload ndarray 포함)이 있다.
- **When** `save()` 후 `load()`로 왕복한다.
- **Then** 복원된 CalibSet의 `domain`·`beam_quality`가 원본과 동일하고, npz 배열 payload와 기존 메타 필드(panel_id/resolution/valid_from/valid_until/kind/data_keys/provenance)가 모두 보존되며, `calibset_id` 문자열 포맷은 서술자 도입 전과 동일하다(서술자 미편입).

### Scenario 4 — 교차도메인 오적용 거부 (REQ-CALDOM-GATE-1/2, XDET-TC-063)
- **Given** `domain=CalibDomain.MEDICAL, beam_quality="RQA5"`인 gain CalibSet과, `run_pipeline(..., domain=CalibDomain.NDT)`로 지정된 NDT 파이프라인 문맥이 있다(해상도·panel_id·유효기간은 정합).
- **When** 진입 게이트가 실행된다.
- **Then** 시스템은 처리를 거부하고 위반 스테이지·CalibSet 도메인(medical)·기대 도메인(ndt)을 명시한 `CalibrationError`를 발생시킨다. **양성 대조**: 동일 CalibSet을 `domain=CalibDomain.MEDICAL` 문맥으로 실행하면 서술자 관련 거부 없이 게이트를 통과한다.

### Scenario 5 — SAMPLE CalibSet 라벨링·비권위 (REQ-CALDOM-SAMPLE, XDET-TC-066)
- **Given** `scripts/ingest_edrogi.py`의 샘플 빌더(offset/gain/defect)가 256² fixture 소스로부터 SAMPLE CalibSet을 생성한다(realdata 부재 시 fixture 소스는 committed 크롭 사용, 항시 실행 가능).
- **When** 샘플 CalibSet을 생성한다.
- **Then** 각 CalibSet의 `domain`이 명시 각인(기본안 `CalibDomain.MEDICAL`, 「결정 필요/확인 사항」 4)되고 `beam_quality is None`이며, 비권위 표식(`panel_id == "SAMPLE-EDROGI-16BIT"`, provenance note에 `sample=true`)이 불변이다. 도메인 라벨은 어떤 수치·임계로도 승격되지 않는다.

### Scenario 6 — SWR-000-10 문서 동기화 (REQ-CALDOM-DOC, XDET-TC-067)
- **Given** 본 SPEC이 구현되어 `common/calibset.py`에 `CalibDomain` 값·서술자 기본값이 확정되어 있다.
- **When** `docs/XDET_SWR_spec_v1.2.md` SWR-000-10 조항과 `CalibSet` docstring을 검사한다.
- **Then** 두 문서가 domain(medical/ndt/unspecified)·beam_quality(자유문자열, RQA5/E2597 예시) 서술자를 열거하고 2계층(§1/§1b) 근거를 담으며, 열거된 domain 값이 코드의 `CalibDomain` 멤버와 일치한다(표류 0건).

## Edge Cases (부정/경계 케이스)

### EC-1 — 스테이지 간 도메인 상호 불일치 (REQ-CALDOM-GATE-3, XDET-TC-064)
- **Given** 한 실행의 두 스테이지 CalibSet이 각각 `domain=MEDICAL`·`domain=NDT`로 모두 지정되어 있다(문맥 인자와 무관).
- **When** 진입 게이트가 실행된다.
- **Then** 게이트는 두 스테이지·도메인을 명시한 `CalibrationError`로 거부한다(기존 panel_id 상호일치 검사와 동일 정신).

### EC-2 — 스테이지 간 빔질 상호 불일치 (REQ-CALDOM-GATE-4, XDET-TC-064)
- **Given** 두 스테이지 CalibSet이 각각 `beam_quality="RQA5"`·`beam_quality="E2597-classA"`로 모두 비-None 지정되어 있다.
- **When** 진입 게이트가 실행된다.
- **Then** 게이트는 두 스테이지·빔질을 명시한 `CalibrationError`로 거부한다(RQA5 맵과 E2597 맵 혼용 차단).

### EC-3 — 서술자 미지정 무회귀 (REQ-CALDOM-GATE-5, XDET-TC-065)
- **Given** 모든 CalibSet의 `domain=UNSPECIFIED`·`beam_quality=None`이거나, `run_pipeline`에 `domain` 인자가 주어지지 않았다(문맥 None).
- **When** 진입 게이트가 실행된다.
- **Then** 서술자 관련 거부가 발생하지 않고, 기존 게이트 검사(존재·해상도·kind·panel_id·유효기간)의 동작·거부 조건이 서술자 도입 전과 동일하다. 기존 게이트 테스트가 전건 green으로 유지된다.

### EC-4 — legacy 로드 후 재저장 왕복 (REQ-CALDOM-COMPAT-1/2)
- **Given** legacy JSON(서술자 키 부재)을 `load()`하여 `domain=UNSPECIFIED`로 채운 CalibSet이 있다.
- **When** 이를 `save()` 후 다시 `load()`한다.
- **Then** `domain=UNSPECIFIED`, `beam_quality=None`이 안정 유지되고 payload·기존 메타가 보존된다(기본값 왕복 무손실).

### EC-5 — 잘못된 서술자 값 검출 (REQ-CALDOM-SCHEMA-2)
- **Given** `domain`이 `CalibDomain` 멤버가 아니거나, `beam_quality`가 빈 문자열인 CalibSet을 구성한다.
- **When** `validate()`가 실행된다.
- **Then** `CalibSchemaError`(기존 스키마 오류 계열)로 검출되어 실패한다. 기존 필드 검사 동작은 불변이다.

## 품질 게이트 / Definition of Done

- [ ] `CalibDomain` str-enum(medical/ndt/unspecified) 신규 + `CalibSet`에 `domain`(기본 UNSPECIFIED)·`beam_quality`(기본 None) 전용 필드 추가
- [ ] `validate()` 서술자 구조 검사 가산(domain=CalibDomain 멤버, beam_quality=None|비어있지않은str), 기존 검사 불변
- [ ] `save()`/`load()`가 서술자를 JSON 메타 신규 키로 왕복 보존, legacy JSON(키 부재)은 기본값으로 로드, `calibset_id` 포맷 불변
- [ ] `run_pipeline`에 `domain: CalibDomain | None = None` kwarg 추가 → `_calibration_gate` 전달(기존 panel_id/timestamp 패턴 동형)
- [ ] `_calibration_gate` 가산 검사: 교차문맥 도메인 거부 + 스테이지 간 도메인 상호 거부 + 스테이지 간 빔질 상호 거부, 미지정/문맥 None 생략(무회귀)
- [ ] `scripts/ingest_edrogi.py` 샘플 빌더가 도메인 서술자 명시 각인(기본안 medical, 사용자 확인)·비권위 표식 불변
- [ ] `docs/XDET_SWR_spec_v1.2.md` SWR-000-10 + `CalibSet` docstring 서술자 열거·코드 일치(PR #35 이연분 소유)
- [ ] Scenario 1~6 통과, EC-1~5 정상 거부/검출, 실 실행 증거(실 왕복 동등·실 게이트 거부/통과) 확인
- [ ] 기존 T0 게이트 검사·기존 CalibSet/orchestrator/ingest 테스트 전건 유지(무회귀)
- [ ] 신규 TC-060~067 테스트 소스는 타 블록 id 문자열(000~021 등)을 포함하지 않는다(캡스톤 스캔 무간섭, D9 선례)
- [ ] `load()` 경로의 미인식 domain 문자열은 명시적 실패(ValueError 또는 CalibSchemaError)로 처리하며 무단 기본화하지 않는다(EC-5 확장)
- [ ] **XDET-TC-060~067 CI PASS** — DoD
