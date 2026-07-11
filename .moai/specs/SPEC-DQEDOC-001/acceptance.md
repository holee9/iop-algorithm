# SPEC-DQEDOC-001 — 인수 기준 (Acceptance Criteria)

DoD: 측정프로토콜 §1.4가 IEC 형태로 정정되고(v1.2, 파일명 유지) · `metrics/dqe.py` obsolete `@MX:WARN` 제거(산출 로직·ANCHOR 불변) · 차원 정합 회귀(역전 형태 음성 대조 포함) 통과 · RTM/코드/문서가 단일 IEC 형태로 일치. **모든 기준은 관측 가능**해야 한다 — 문서 문자열 grep 상태 · `@MX:WARN` 개수 · pytest 통과/실패 · `uv run lint-imports` clean. 소스 산출 로직은 변경하지 않는다(측정=판정 분리 보존).

정확 형태(IEC 62220-1): `DQE(f) = MTF²(f) / (q · Ka · NNPS(f))` · 역전 형태(오기): `DQE(f) = MTF²(f) · q · Ka / NPS(f)`.

## Given-When-Then 시나리오

### Scenario 1 — 측정프로토콜 §1.4 IEC 형태 정정 (REQ-DQEDOC-DOC, XDET-TC-070)
- **Given** `docs/XDET_measurement_protocol_v1.0.md` §1.4가 현재 역전 형태 `DQE(f) = MTF²(f) · q · Ka / NPS(f)`를 명기하고 있다(in-file 버전 v1.1).
- **When** run 단계가 §1.4를 정정한다.
- **Then** §1.4는 IEC 형태 `DQE(f) = MTF²(f) / (q · Ka · NNPS(f))` 문자열을 포함하고(grep 존재), 무차원 주석(q·Ka=광자 fluence [1/mm²], NNPS=[mm²] → 무차원)을 포함하며, in-file 버전 문자열이 v1.2로 승격되고, HISTORY에 issue #38을 인용한 항목이 존재한다. 파일명 `XDET_measurement_protocol_v1.0.md`는 변경되지 않는다(grep + 파일 존재 확인).

### Scenario 2 — metrics/dqe.py @MX 태그 정합 (REQ-DQEDOC-TAG, XDET-TC-071)
- **Given** `metrics/dqe.py` 모듈 docstring이 프로토콜 §1.4 상충을 경고하는 `@MX:WARN` + `@MX:REASON` 블록과 `compute_dqe`의 `@MX:ANCHOR` + `@MX:REASON`을 담고 있다.
- **When** 문서 정정(Scenario 1) 후 run 단계가 태그를 정합한다.
- **Then** `metrics/dqe.py`의 `@MX:WARN` 발생 개수가 0이고(grep count == 0), `@MX:ANCHOR`(compute_dqe)와 그 `@MX:REASON`은 존재하며(grep), 모듈 docstring의 IEC 형태 서술·무차원 설명은 보존된다. DQE 산출식·`compute_dqe` 시그니처·파라미터·0-나눗셈 가드는 변경되지 않는다(Scenario 3 회귀 green으로 거동 불변 확인).

### Scenario 3 — 차원 정합 회귀 + 역전 형태 음성 대조 (REQ-DQEDOC-TEST, XDET-TC-072)
- **Given** `tests/metrics/test_nps_dqe.py`에 이상적 양자제한 검출기 DQE≈1 및 선량 불변 회귀(기존)와, 역전 §1.4 형태를 test-local로 계산하는 음성 대조(신규)가 있다.
- **When** `uv run pytest tests/metrics/test_nps_dqe.py`를 실행한다.
- **Then** 단위성(DQE≈1, `dqe_ideal_abs` 허용오차 내)과 선량 불변(2× 선량에서도 DQE 불변) 단언이 통과하고, 역전 형태(`MTF²·q·Ka/NPS`, 테스트 내부 계산)가 단위성·선량 불변을 만족하지 **않음**을 단언하는 음성 대조가 통과한다(역전 형태가 실제로 오답임이 고정된다). 모듈은 주입된 q·Ka·NNPS를 독립 소비하여 비순환으로 판정된다.

### Scenario 4 — RTM/코드/문서 추적성 일치 (REQ-DQEDOC-TRACE, XDET-TC-073)
- **Given** 정정 완료 후 코드(`metrics/dqe.py`)·문서(측정프로토콜 §1.4)·RTM(`docs/XDET_RTM_v1.1.md`)이 공존한다.
- **When** run 단계가 추적성을 검사한다.
- **Then** RTM MR-003/PR-CORE-001의 DQE 매핑(FR-C001~C004 → EV-101 → VV-001 → TC-001~003)이 유효하게 유지되고(행·버전 불변), `docs/` 전체에서 역전 형태 `MTF²·q·Ka/NPS`의 발생 개수가 0이며(grep, SWR 포함), SPEC-DQEDOC-001(issue #38)이 SPEC-METRICS-001 §1.4 이연의 해소로 기록된다(기록 방식은 spec.md 「결정 필요/확인 사항」 2).

## Edge Cases (부정/경계 케이스)

### EC-1 — 소스 산출 로직 무변경 가드 (REQ-DQEDOC-CONTRACT-1, REQ-DQEDOC-TAG-3)
- **Given** run 단계가 `metrics/dqe.py`를 편집한다(태그 제거).
- **When** DQE 회귀(Scenario 3)와 기존 DQE 시나리오(EC-3 0-나눗셈 등)를 재실행한다.
- **Then** 모든 DQE 산출 거동이 정정 전과 동일하게 통과한다(산출식·시그니처·가드 불변). 편집 diff는 docstring의 WARN/REASON 라인 제거로 한정된다.

### EC-2 — 파일 리네임 거부 (REQ-DQEDOC-DOC-4)
- **Given** 정정이 파일명을 `XDET_measurement_protocol_v1.2.md` 등으로 바꾸려는 유혹이 있다.
- **When** run 단계가 문서를 저장한다.
- **Then** 파일명은 `XDET_measurement_protocol_v1.0.md`로 유지되고(문서 존재 확인), in-file 버전 문자열만 v1.2로 바뀐다(문서 맵·RTM 참조 보존).

### EC-3 — 역전 형태 재도입 방지 (REQ-DQEDOC-TEST-4, REQ-DQEDOC-TRACE-3)
- **Given** 가상으로 역전 §1.4 형태가 `metrics/dqe.py`에 재도입되거나 docs/에 재등장한 상태.
- **When** 회귀(Scenario 3)와 추적성 검사(Scenario 4)를 실행한다.
- **Then** 음성 대조·단위성·선량 불변 회귀가 FAIL 하고, docs/ 역전 형태 grep이 0을 초과하여 추적성 검사가 FAIL 한다(정정이 고정되어 재발이 차단된다).

### EC-4 — 범위 이탈 가드 (REQ-DQEDOC-CONTRACT-3)
- **Given** 4개 지정 대상(측정프로토콜 문서, `metrics/dqe.py` 태그, `tests/metrics/test_nps_dqe.py`, RTM/추적성 기록) 밖의 파일 편집 시도.
- **When** run 단계의 변경 집합을 검토한다.
- **Then** 4개 대상 밖 파일 편집이 없음이 확인되고(diff 범위 검토), `uv run lint-imports`가 clean을 유지한다(의존 계층 계약 불변).

## 품질 게이트 / Definition of Done

- [ ] 측정프로토콜 §1.4 = IEC 형태 `DQE(f)=MTF²(f)/(q·Ka·NNPS(f))` 문자열 존재 + 무차원 주석 존재 (Scenario 1, XDET-TC-070)
- [ ] 측정프로토콜 §1.4에서 역전 형태 `MTF²·q·Ka/NPS` 문자열 부재 (Scenario 1 / Scenario 4)
- [ ] 측정프로토콜 in-file 버전 v1.1 → v1.2 + HISTORY에 issue #38 항목 + 파일명 `XDET_measurement_protocol_v1.0.md` 유지 (Scenario 1, EC-2)
- [ ] `metrics/dqe.py` `@MX:WARN` 개수 == 0 (Scenario 2, XDET-TC-071)
- [ ] `metrics/dqe.py` `compute_dqe` `@MX:ANCHOR` 존재 + IEC 서술 보존 (Scenario 2)
- [ ] `metrics/dqe.py` 산출식·시그니처·파라미터·가드 무변경 (EC-1, CONTRACT-1)
- [ ] `tests/metrics/test_nps_dqe.py` 단위성/선량 불변 회귀 보존(비약화) (Scenario 3, XDET-TC-072)
- [ ] `tests/metrics/test_nps_dqe.py` 역전 §1.4 형태 test-local 음성 대조 추가·통과 (Scenario 3)
- [ ] `uv run pytest tests/metrics/test_nps_dqe.py` green (Scenario 3, EC-1)
- [ ] RTM MR-003/PR-CORE-001 DQE 매핑 유효 + RTM 행·버전 불변 (Scenario 4, XDET-TC-073)
- [ ] `docs/` 전체(SWR 포함) 역전 형태 `MTF²·q·Ka/NPS` 발생 0건 (Scenario 4, EC-3)
- [ ] SPEC-DQEDOC-001(issue #38) 추적성 체인 기록 (Scenario 4)
- [ ] 4개 지정 대상 밖 파일 무편집 + `uv run lint-imports` clean (EC-4, CONTRACT-3·4)
- [ ] **소스 공식 무변경 · 단일 IEC 형태로 코드+문서+RTM 일치 — DoD**
