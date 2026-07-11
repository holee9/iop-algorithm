---
id: SPEC-DQEDOC-001
title: DQE 측정프로토콜 §1.4 공식 정정 + 코드/태그/추적성 정합
version: 0.1.0
status: draft
created: 2026-07-11
updated: 2026-07-11
author: drake.lee
priority: medium
issue_number: 38
---

# SPEC-DQEDOC-001 구현 계획 (초안) — DQE §1.4 문서 교정

> 상태: **draft** (run 단계 착수 전까지 유지). EARS 확정본은 [spec.md](./spec.md), 인수 기준은 [acceptance.md](./acceptance.md). 선례는 [SPEC-METRICS-001](../SPEC-METRICS-001/spec.md).

## 1. 개요

`metrics/dqe.py`는 IEC 62220-1 형태 `DQE(f) = MTF²(f) / (q·Ka·NNPS(f))`(무차원)를 커밋 `41ec640`에서 **이미 정확히 구현**했으나, 구현 사양 문서 `docs/XDET_measurement_protocol_v1.0.md` §1.4는 차원 역전된 `DQE(f) = MTF²(f) · q · Ka / NPS(f)`를 명기한다. 본 정정성 작업은 문서를 코드에 정합시키고(문서 교정), 그로써 obsolete가 된 코드 태그를 정리하며(태그 정합), 차원 정합 회귀를 보강하고(회귀 테스트), RTM/코드/문서 추적성을 동기화한다(추적성). **코드 산출 로직은 정확하므로 변경하지 않는다.**

## 2. run 단계에서 편집하는 파일 (정확히 4개 대상)

| # | 파일 | 편집 내용 | 대응 REQ | 편집 성격 |
|---|---|---|---|---|
| 1 | `docs/XDET_measurement_protocol_v1.0.md` | §1.4 DQE 공식을 IEC 형태로 정정 + 무차원 주석 추가; in-file 버전 v1.1 → **v1.2**; HISTORY에 issue #38 항목 추가; **파일명 유지** | DOC-1~4, TRACE-4 | 문서 텍스트 |
| 2 | `metrics/dqe.py` | 모듈 docstring의 obsolete `@MX:WARN` + `@MX:REASON` 블록 제거; IEC 서술·`@MX:ANCHOR`·산출 로직·시그니처·가드 **전부 보존** | TAG-1~4, CONTRACT-1 | 주석(docstring)만 |
| 3 | `tests/metrics/test_nps_dqe.py` | 기존 단위성/선량 불변 회귀 **보존** + 역전 §1.4 형태 test-local 음성 대조 추가 | TEST-1~4 | 테스트 추가 |
| 4 | `docs/XDET_RTM_v1.1.md`(추적성 기록) | MR-003/PR-CORE-001 DQE 매핑 유효성 확인 + SPEC-DQEDOC-001(#38) 해소 기록(방식은 「결정 필요/확인 사항」 2) | TRACE-1~3 | 노트/확인 |

**이 4개 밖의 파일은 편집하지 않는다**(REQ-DQEDOC-CONTRACT-3). 특히 `docs/XDET_SWR_spec_v1.2.md`는 DQE 공식을 기재하지 않으므로(SWR-000-10 서술만) 편집 대상이 아니며, TRACE 검사의 docs/-전체 grep 범위에만 포함된다.

## 3. 정정 상세 (측정프로토콜 §1.4)

- **현재(라인 40, 역전)**: `DQE(f) = MTF²(f) · q · Ka / NPS(f). q(RQA5 광자 fluence 계수)는 IEC 표 값 사용.`
- **정정(IEC 형태)**: `DQE(f) = MTF²(f) / (q · Ka · NNPS(f))` + 무차원 주석 — q·Ka = 광자 fluence [1/mm²](q = 단위 air-kerma당 광자수 [1/(mm²·µGy)] [S], Ka = 검출기면 air kerma [µGy]), NNPS = [mm²] → DQE 무차원. 역전 형태는 선량에 무한정 증가하여 참 DQE 불가.
- **HISTORY 추가(형식은 문서 기존 항목 준수)**: `- v1.2 (issue #38): §1.4 DQE 공식을 IEC 62220-1 형태 DQE(f)=MTF²(f)/(q·Ka·NNPS(f))로 정정(무차원 주석 추가). v1.1까지의 'MTF²·q·Ka/NPS'는 차원 역전 오기. metrics/dqe.py(커밋 41ec640)는 이미 IEC 형태로 구현되어 있어 코드 무변경. 파일명 유지.` + in-file 버전 문자열 v1.1 → v1.2.

## 4. 실행 순서

1. **문서 교정 우선** (대상 1): §1.4 정정 → v1.2 → HISTORY. 다른 모든 산출물의 논리적 전제(태그 제거의 근거·회귀의 pin·추적성 일치가 모두 이 정정에 매인다).
2. **태그 정합** (대상 2): 문서 상충이 해소된 뒤 dqe.py의 `@MX:WARN`/`@MX:REASON` 제거. 산출 로직·ANCHOR 불변 확인.
3. **회귀 테스트** (대상 3): 기존 단위성/선량 불변 회귀 보존 확인 + 역전 형태 음성 대조 추가. `uv run pytest tests/metrics/test_nps_dqe.py` green.
4. **추적성 동기화** (대상 4): RTM MR-003/PR-CORE-001 DQE 매핑 유효성 확인 + docs/ 전체 역전 공식 0건 검증 + SPEC-DQEDOC-001 해소 기록.

## 5. 리스크 분석 (요약)

| 리스크 | 완화 | 우선순위 |
|---|---|---|
| 문서 정정 중 소스 공식 무단 변경 유입 | CONTRACT-1 [HARD] 소스 무변경; dqe.py 편집은 docstring WARN/REASON 라인 제거로 한정; DQE 회귀 green으로 거동 불변 확인 | High |
| ANCHOR 무단 삭제(공개 진입점 계약 손실) | TAG-2 ANCHOR 보존; XDET-TC-071에서 `@MX:ANCHOR` 존재 grep 확인 | High |
| 역전 공식 잔존(다른 docs/ 지점) | TRACE-3 docs/ 전체 역전 형태 grep 0건; SWR은 서술만이므로 §1.4 단일 지점으로 수렴 | Medium |
| 회귀 중복(기존 커버리지 재작성 낭비) | TEST-1 기존 테스트 보존·비약화; 신규는 역전 형태 음성 대조로 한정 | Medium |
| 파일 리네임으로 문서 맵/RTM 참조 깨짐 | DOC-4 파일명 유지(문서 자체 규칙); in-file 버전만 승격 | Medium |
| 범위 이탈(인접 절/파일 정리) | CONTRACT-3 4개 대상 밖 편집 금지 | Medium |

## 6. 마일스톤 (우선순위 기반, 시간 추정 없음)

- **Priority High — M1 문서 교정**: 측정프로토콜 §1.4 IEC 형태 정정 + 차원 주석 + v1.2 HISTORY(issue #38) + 파일명 유지. 나머지 산출물의 전제.
- **Priority High — M2 태그 정합**: dqe.py `@MX:WARN`/`@MX:REASON` 제거, ANCHOR·산출 로직 불변. M1 완료 후.
- **Priority Medium — M3 회귀 테스트**: 단위성/선량 불변 회귀 보존 + 역전 형태 음성 대조 추가. `uv run pytest` green.
- **Priority Medium — M4 추적성 동기화**: RTM 매핑 확인 + docs/ 역전 공식 0건 + SPEC-DQEDOC-001 해소 기록.
- 순서 원칙: M1(문서 교정) 확정 후 M2~M4 착수. M3·M4는 상호 독립 병행 가능.

## 7. 검증 전략 — 관측 가능 판정

- **문서 상태 grep**: §1.4에 IEC 형태 문자열 존재 + 역전 형태 문자열 부재 + v1.2 HISTORY(issue #38) 존재 + 파일명 불변(XDET-TC-070).
- **태그 grep**: `metrics/dqe.py`의 `@MX:WARN` 개수 == 0 + `@MX:ANCHOR` 존재 + IEC 서술 보존; DQE 회귀 green으로 산출 거동 불변(XDET-TC-071).
- **회귀 실행**: `uv run pytest tests/metrics/test_nps_dqe.py` green — 단위성/선량 불변 통과 + 역전 형태 음성 대조가 오답을 잡음(XDET-TC-072).
- **추적성**: RTM MR-003/PR-CORE-001 DQE 매핑 유효 + docs/ 전체 역전 공식 0건 + SPEC-DQEDOC-001 기록(XDET-TC-073).
- **의존 계층**: `uv run lint-imports` clean 유지(CONTRACT-4) — 편집이 계층 계약을 건드리지 않음.
- **DoD**: 4개 산출물이 각 XDET-TC(070~073)로 관측 가능하게 통과 + 소스 공식 무변경.

## 8. DoD (Definition of Done)

- [ ] 측정프로토콜 §1.4가 IEC 형태 + 무차원 주석으로 정정, in-file 버전 v1.1 → v1.2, HISTORY에 issue #38 항목, 파일명 유지 (DOC-1~4)
- [ ] `metrics/dqe.py` `@MX:WARN`/`@MX:REASON` 제거, `@MX:ANCHOR`·IEC 서술·산출 로직 불변 (TAG-1~4)
- [ ] `tests/metrics/test_nps_dqe.py` 단위성/선량 불변 회귀 보존 + 역전 형태 음성 대조 추가, `uv run pytest tests/metrics/test_nps_dqe.py` green (TEST-1~4)
- [ ] RTM MR-003/PR-CORE-001 DQE 매핑 유효 + docs/ 전체 역전 공식 0건 + SPEC-DQEDOC-001 해소 기록 (TRACE-1~4)
- [ ] 소스 산출 로직 무변경, EV 임계 무변경, 4개 대상 밖 파일 무편집, `uv run lint-imports` clean (CONTRACT-1~4)
