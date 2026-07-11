---
id: SPEC-DQEDOC-001
version: 0.1.0
status: draft
created: 2026-07-11
updated: 2026-07-11
author: drake.lee
priority: medium
issue_number: 38
---

# SPEC-DQEDOC-001 — DQE 측정프로토콜 §1.4 공식 정정 + 코드/태그/추적성 정합

XDET 영상처리 SW P1의 **문서 교정 SPEC**. `metrics/dqe.py`는 이미 IEC 62220-1 형태 `DQE(f) = MTF²(f) / (q·Ka·NNPS(f))`(무차원)를 커밋 `41ec640`에서 올바르게 구현했으나, 구현 사양 문서 `docs/XDET_measurement_protocol_v1.0.md` §1.4는 여전히 차원 역전된 `DQE(f) = MTF²(f) · q · Ka / NPS(f)`를 명기한다. 본 SPEC은 **문서를 IEC 형태로 정정**하고, 그에 따라 해소 가능해진 `metrics/dqe.py`의 `@MX:WARN`/`@MX:REASON` 태그를 정리하며, 차원 정합 회귀 테스트를 보강하고, RTM/코드/문서의 추적성을 동기화한다. **코드의 산출 로직은 이미 정확하므로 변경하지 않는다.**

- 근거: `docs/XDET_measurement_protocol_v1.0.md` §1.4(DQE 측정 사양, 정정 대상) · IEC 62220-1(DQE 무차원 정의) · `metrics/dqe.py`(커밋 `41ec640`, 이미 IEC 형태 구현) · `docs/XDET_RTM_v1.1.md` MR-003/PR-CORE-001(EV-101, VV-001, TC-001~003)
- 완료 정의(DoD): 측정프로토콜 §1.4가 IEC 형태 + 무차원 주석으로 정정되고 문서 in-file 버전 v1.1 → **v1.2**(HISTORY에 issue #38 명기, 파일명 유지) · `metrics/dqe.py` `@MX:WARN`/`@MX:REASON` 제거(산출 로직·`@MX:ANCHOR` 불변) · 차원 정합 회귀 테스트(역전 형태 음성 대조 포함) 통과 · RTM/코드/문서가 단일 IEC 형태로 일치 · `uv run pytest tests/metrics/test_nps_dqe.py` green · **소스 공식 무변경**
- 선행/선례 SPEC: [SPEC-METRICS-001](../SPEC-METRICS-001/spec.md) — T1 지표 산출 엔진(DQE 엔진, status: implemented). 본 SPEC은 SPEC-METRICS-001 HISTORY v0.2.0이 "프로토콜 문서 v1.1 개정 필요(이슈 #2 기록)"로 이연한 §1.4 불일치를 정식으로 해소한다.
- 구현 계획: [plan.md](./plan.md) · 인수 기준: [acceptance.md](./acceptance.md)

## HISTORY

- **v0.1.0 (2026-07-11)** — 초안 생성. GitHub 이슈 #38. 5개 요구 그룹(DOC/TAG/TEST/TRACE/CONTRACT) EARS 구조 확정. 4개 산출물(문서 교정 · @MX 태그 정합 · 차원 정합 회귀 테스트 · 추적성 동기화)을 시험케이스 **XDET-TC-070~073**에 대응. 저작 시 검증·확정 사항: (a) 역전 공식은 `docs/XDET_measurement_protocol_v1.0.md` §1.4(라인 40)에만 존재 — `docs/XDET_SWR_spec_v1.2.md` SWR-000-10(라인 17)은 DQE를 서술적으로만 언급(공식 미기재)하므로 SWR 공식 편집 불필요, TRACE는 docs/ 전체에서 역전 공식 0건만 검증. (b) 차원 정합/선량 불변 회귀는 `tests/metrics/test_nps_dqe.py::test_scenario3_dqe_ideal_detector_is_unity`·`test_scenario3_dqe_is_dose_invariant`로 **이미 존재** — 본 SPEC은 그 커버리지를 보존하고 역전 형태 음성 대조(test-local)를 추가하는 방향으로 한정. (c) 문서 in-file 버전은 이미 v1.1(issue #34), 파일명 유지 규칙은 문서 자체 HISTORY에 명시됨 → v1.2로 승격. status: draft (run 단계 착수 전까지 유지).

## Environment / Assumptions

- 본 SPEC은 **T-스테이지가 아니다.** `CANONICAL_ORDER` 스테이지 추가·`process(XFrame,CalibSet,Params)->XFrame` 시그니처·신규 `CalibKind`·`_KIND_BY_STAGE` 변경이 전혀 없다. 문서 교정 + 코드 태그 정리 + 테스트 보강 + 추적성 동기화만 수행하는 정정성(correction) 작업이다.
- **[HARD] 소스 산출 로직 무변경.** `metrics/dqe.py`의 DQE 산출식(IEC 형태, 커밋 `41ec640`에서 이미 정확)·함수 시그니처·파라미터(`dqe_q`/`dqe_ka`/`dqe_nps_floor`)·0-나눗셈 가드는 손대지 않는다. 본 SPEC이 dqe.py에서 편집하는 유일 대상은 **모듈 docstring 내 `@MX:WARN` + 그 `@MX:REASON` 블록**(문서 정정으로 상충이 해소되어 obsolete)이며, IEC 형태 서술·`@MX:ANCHOR`(compute_dqe 공개 진입점)는 보존한다.
- 문서 정정 대상은 정확히 `docs/XDET_measurement_protocol_v1.0.md` §1.4(현재 라인 40: `DQE(f) = MTF²(f) · q · Ka / NPS(f)`)와 그 문서의 in-file 버전 문자열/HISTORY이다. **파일명 `XDET_measurement_protocol_v1.0.md`는 변경하지 않는다** — 문서 자체 HISTORY(v1.1, issue #34)가 "파일명은 유지(문서 맵·RTM 참조 보존)"를 규칙으로 명기하며, in-file 버전만 v1.1 → v1.2로 승격한다.
- **정확 형태(IEC 62220-1)**: `DQE(f) = MTF²(f) / (q · Ka · NNPS(f))`. 무차원 근거: q·Ka = 광자 fluence [1/mm²](q = 단위 air-kerma당 광자수 [1/(mm²·µGy)] [S], Ka = 검출기면 air kerma [µGy]), NNPS는 [mm²]를 가지므로 DQE(f)는 무차원. **역전 형태**(`MTF²·q·Ka/NPS`)는 무차원이 아니고 선량 증가에 대해 무한정 증가하여 참 DQE일 수 없다.
- 분모는 정규화된 NNPS(=NPS/대신호²)를 사용한다 — 측정프로토콜 §1.3이 이미 NNPS 정규화를 산출하며, dqe.py 서술도 NNPS를 사용한다(§1.4 정정은 이 상류와 정합).
- 측정=판정 분리 보존: 본 정정은 **측정 방법(공식) 텍스트**만 다루며 EV min/typ/max 판정 수치(EVAL v1.1)는 건드리지 않는다. RTM MR-003/PR-CORE-001의 DQE 매핑(FR-C001~C004 → EV-101 → VV-001 → TC-001~003)은 요구·EV·TC를 바꾸지 않고 측정 텍스트만 코드에 맞춘다.
- 환경: 저장소는 Python을 `uv run`으로만 실행한다. 회귀는 `uv run pytest tests/metrics/test_nps_dqe.py`, 의존 계층 정적검사는 `uv run lint-imports`로 확인한다.

## Requirements (EARS)

### REQ-DQEDOC-DOC — 측정프로토콜 §1.4 DQE 공식 정정 (측정프로토콜 §1.4, IEC 62220-1, XDET-TC-070)

- **REQ-DQEDOC-DOC-1 (Ubiquitous)** — `docs/XDET_measurement_protocol_v1.0.md` §1.4는 DQE를 IEC 62220-1 형태 `DQE(f) = MTF²(f) / (q · Ka · NNPS(f))`로 명기해야 하며, 기존 차원 역전 표현 `MTF²(f) · q · Ka / NPS(f)`를 대체해야 한다.
- **REQ-DQEDOC-DOC-2 (Ubiquitous)** — §1.4는 무차원 주석(q·Ka = 광자 fluence [1/mm²], NNPS = [mm²] → DQE 무차원; 역전 형태는 선량에 무한정 증가하여 참 DQE 불가)을 함께 명기하여 정정된 공식이 자기 설명적이어야 한다.
- **REQ-DQEDOC-DOC-3 (Event-Driven)** — WHEN §1.4가 정정되면, THEN 문서 in-file 버전은 v1.1 → v1.2로 승격되고 HISTORY에 issue #38을 인용한 항목(정정 내용 + `metrics/dqe.py`는 커밋 `41ec640`에서 이미 IEC 형태이므로 코드 무변경 명시)이 추가되어야 한다.
- **REQ-DQEDOC-DOC-4 (Unwanted)** — IF 정정이 파일 리네임을 유발하려 하면, THEN 시스템은 이를 거부해야 한다 — 파일명 `XDET_measurement_protocol_v1.0.md`는 유지하고 in-file 버전 문자열만 변경한다(문서 자체 HISTORY의 "파일명 유지" 규칙, 문서 맵·RTM 참조 보존).

### REQ-DQEDOC-TAG — metrics/dqe.py @MX 태그 정합 (mx-tag-protocol, XDET-TC-071)

- **REQ-DQEDOC-TAG-1 (Event-Driven)** — WHEN 측정프로토콜 §1.4가 IEC 형태로 정정되면, THEN `metrics/dqe.py` 모듈 docstring의 이제 obsolete가 된 `@MX:WARN`(프로토콜 §1.4 상충 경고)과 그 `@MX:REASON` 블록은 제거되어야 한다(상충이 해소되어 경고 근거 소멸).
- **REQ-DQEDOC-TAG-2 (Ubiquitous)** — `compute_dqe`의 `@MX:ANCHOR`(공개 DQE 진입점, fan_in 불변 계약)와 그 `@MX:REASON`은 유지되어야 한다 — 함수 fan_in·공개 경계가 변하지 않으므로 앵커는 보존한다(ANCHOR 자동 삭제 금지).
- **REQ-DQEDOC-TAG-3 (Unwanted)** — IF 태그 정리가 `metrics/dqe.py`를 편집하면서 DQE 산출식·함수 시그니처·파라미터·0-나눗셈 가드 중 하나라도 변경하면, THEN 이는 계약 위반으로 취급되어야 한다(편집 범위는 docstring의 WARN/REASON 서술 라인 제거로 한정, 수치 거동 불변).
- **REQ-DQEDOC-TAG-4 (Ubiquitous)** — WARN 제거 후에도 `metrics/dqe.py` 모듈 docstring은 정확한 IEC 형태 서술 + 무차원 설명을 유지하여 코드가 자기 설명적이어야 한다(이미 존재하는 서술 보존).

### REQ-DQEDOC-TEST — 차원 정합 회귀 테스트 (tests/metrics/test_nps_dqe.py, XDET-TC-072)

- **REQ-DQEDOC-TEST-1 (Ubiquitous)** — `tests/metrics/test_nps_dqe.py`는 이상적 양자제한 검출기의 DQE ≈ 1(무차원)과 DQE 선량 불변성을 검증하는 차원 정합 회귀를 유지해야 한다(기존 `test_scenario3_dqe_ideal_detector_is_unity`·`test_scenario3_dqe_is_dose_invariant` 커버리지 보존 — 본 SPEC은 이를 약화하지 않는다).
- **REQ-DQEDOC-TEST-2 (Event-Driven)** — WHEN 회귀 스위트가 실행되면, THEN 역전 §1.4 형태(`MTF²·q·Ka/NPS`)를 **test-local 참조 수식**으로 계산하여 그 값이 무차원 단위성(≈1)·선량 불변성을 만족하지 **않음**을 명시적으로 단언하는 음성 대조가 포함되어야 한다(역전 형태가 실제로 오답임을 고정 — IEC 형태가 load-bearing함을 증명). 역전 수식은 모듈 코드 경로가 아니라 테스트 내부에서만 계산한다.
- **REQ-DQEDOC-TEST-3 (State-Driven)** — WHILE `metrics/dqe.py`가 IEC 형태를 구현하는 동안, 회귀는 주입된 q·Ka·NNPS를 독립적으로 소비하여(모듈 표현식의 재계산이 아닌 비순환 방식) 모듈 출력이 기존 [T] 허용오차(`dqe_ideal_abs`) 내에서 무차원·선량 불변임을 단언해야 한다.
- **REQ-DQEDOC-TEST-4 (Unwanted)** — IF 역전 §1.4 형태가 `metrics/dqe.py`에 재도입되면, THEN 본 회귀(단위성·선량 불변 + 음성 대조)는 FAIL 해야 한다(테스트가 정정을 고정 — 재발 방지).

### REQ-DQEDOC-TRACE — 추적성 동기화 (RTM/코드/문서, XDET-TC-073)

- **REQ-DQEDOC-TRACE-1 (Ubiquitous)** — `docs/XDET_RTM_v1.1.md` MR-003/PR-CORE-001의 DQE 매핑(FR-C001~C004 → EV-101 → VV-001 → TC-001~003)은 정정 후에도 유효해야 한다 — 본 정정은 요구·EV·TC를 바꾸지 않고 측정 방법 텍스트를 이미 정확한 코드에 정합시킬 뿐이다(RTM 행·버전 불변).
- **REQ-DQEDOC-TRACE-2 (Event-Driven)** — WHEN 문서 정정이 완료되면, THEN 추적성 체인은 SPEC-DQEDOC-001(issue #38)을 SPEC-METRICS-001 v0.2.0이 이연한 §1.4 불일치의 해소로 기록해야 한다(dqe.py `@MX:WARN`가 인용하던 "issue #2" 경고의 종결).
- **REQ-DQEDOC-TRACE-3 (Unwanted)** — IF 정정 후에도 `docs/` 하위 어떤 문서(측정프로토콜 §1.4, SWR 사양, RTM)가 역전 형태 `MTF²·q·Ka/NPS` DQE 공식을 명기하고 있으면, THEN 추적성 검사는 FAIL 해야 한다(코드+문서+RTM에 걸쳐 단일 IEC 형태만 존재).
- **REQ-DQEDOC-TRACE-4 (State-Driven)** — WHILE 코드(`metrics/dqe.py`)·문서(측정프로토콜 §1.4)·RTM이 공존하는 동안, 세 아티팩트는 IEC DQE 형태에 대해 일치해야 한다(no-drift).

### REQ-DQEDOC-CONTRACT — 정정 계약: 무변경 불변식 · 범위 규율 (CLAUDE.md 금지·범위, XDET-TC-070~073 공통)

- **REQ-DQEDOC-CONTRACT-1 (Ubiquitous)** — 본 SPEC은 어떠한 소스 산출 로직도 변경해서는 안 된다 — `metrics/dqe.py::compute_dqe`의 수치 거동(IEC 형태, 커밋 `41ec640`에서 이미 정확)은 불변이며, 작업은 문서 + 태그 + 테스트 + 추적성으로 한정된다.
- **REQ-DQEDOC-CONTRACT-2 (Ubiquitous)** — 측정=판정 분리가 보존되어야 한다 — 정정은 측정 방법 공식 텍스트만 다루며 EV min/typ/max 판정 임계는 변경하지 않는다.
- **REQ-DQEDOC-CONTRACT-3 (Unwanted)** — IF run 단계가 4개 지정 대상(측정프로토콜 문서 §1.4/버전/HISTORY, `metrics/dqe.py` 태그, `tests/metrics/test_nps_dqe.py`, RTM/추적성 기록) 밖의 파일을 편집하면, THEN 이는 범위 위반으로 취급되어야 한다(scope discipline).
- **REQ-DQEDOC-CONTRACT-4 (Ubiquitous)** — 모든 시험·정적검사는 `uv run`으로 실행되어야 한다 — 회귀는 `uv run pytest tests/metrics/test_nps_dqe.py`로 green, 의존 계층은 `uv run lint-imports`로 clean을 유지해야 한다(uv 전용 환경).

## Exclusions (What NOT to Build)

- **소스 공식/알고리즘 변경 없음** — `metrics/dqe.py`의 DQE 산출식은 이미 IEC 형태로 정확(커밋 `41ec640`)하므로 손대지 않는다. 편집 대상은 obsolete `@MX:WARN`/`@MX:REASON` 서술뿐이며 `@MX:ANCHOR`·산출 로직·시그니처·가드는 불변.
- **EV 판정 임계/기준 변경 없음** — EVAL v1.1 EV min/typ/max, 합격 기준서는 건드리지 않는다. 측정 방법 텍스트만 정정한다.
- **파일 리네임 없음** — `XDET_measurement_protocol_v1.0.md` 파일명 유지(문서 맵·RTM 참조 보존). in-file 버전 문자열만 v1.1 → v1.2.
- **신규 T-스테이지/모듈/CalibKind 없음** — `CANONICAL_ORDER` 스테이지·`process(...)->XFrame` 시그니처·`_KIND_BY_STAGE`·신규 `CalibKind` 추가 없음. 본 SPEC은 정정성 작업이지 처리 WP가 아니다.
- **DQE 물리 재유도/IEC 재해석 없음** — 이미 구현된 무차원 형태를 문서에 반영할 뿐, IEC 62220-1 조항 재해석·조리개 위치 등 세부 수치 확정(측정프로토콜 §5 이연 항목)은 범위 밖.
- **문서 전면 개정 없음** — 측정프로토콜은 §1.4 + 버전 문자열 + HISTORY 항목만 편집한다. §1(빔질), §1b, §1.2/1.3 등 다른 절은 손대지 않는다(범위 규율).
- **신규 수치 파라미터 없음** — 정정은 기존 파라미터(`dqe_q`/`dqe_ka`/`dqe_nps_floor`)를 그대로 사용하며 새 Param/CalibSet 필드를 도입하지 않는다.
- **SWR 사양 DQE 공식 편집 없음** — `docs/XDET_SWR_spec_v1.2.md`는 DQE를 서술적으로만 언급(SWR-000-10, 공식 미기재)하므로 편집 대상이 아니다. TRACE는 SWR을 포함한 docs/ 전체에서 역전 공식 부재만 검증한다.

## 결정 필요/확인 사항

저작 시 대부분 확정되었으며, run 단계 착수 전 사용자 확인이 필요한 항목은 1건(추적성 기록 방식)이다. 어떤 항목도 실측[B] 대기가 아니므로 run 단계를 차단하지 않는다.

1. **[확정 — RESOLVED]** SWR 사양 DQE 참조 범위 — `docs/XDET_SWR_spec_v1.2.md` SWR-000-10(라인 17)은 DQE/MTF/NPS를 "계측 참조 빔질(RQA5)에서 측정" 서술로만 언급하며 **공식을 기재하지 않음**을 저작 시 검증. 따라서 SWR 공식 편집은 불필요하고, REQ-DQEDOC-TRACE-3의 docs/ 전체 검사는 현재 역전 공식이 유일하게 존재하는 §1.4만 대상이 된다. **rationale**: 역전 공식의 단일 출처는 측정프로토콜 §1.4이며, 코드는 이미 정확하므로 정정은 그 한 지점 + 파생 검증으로 수렴한다.

2. **[확인 필요]** 추적성 기록 방식(REQ-DQEDOC-TRACE-2) — SPEC-DQEDOC-001(#38)을 추적성 체인에 기록하는 방법. **가정 기본값**: (a) `docs/XDET_RTM_v1.1.md`에 MR-003 행·RTM 버전을 바꾸지 않고 한 줄 주석/HISTORY 노트(있으면)로 "§1.4 DQE 측정 텍스트 정정 = SPEC-DQEDOC-001/issue #38, SPEC-METRICS-001 §1.4 이연 해소"를 남기고, (b) 1차 기록은 본 SPEC 디렉터리 + 이슈 링크로 삼는다. **확인 대상**: RTM에 노트를 추가할지(그리고 RTM에 HISTORY 절이 없으면 어디에), 아니면 SPEC/커밋 트레일만으로 기록할지 사용자 선호. RTM 버전 승격(v1.1 → v1.2)은 기본 **미실시**(행·요구 불변, 측정프로토콜만 v1.2)로 가정.
