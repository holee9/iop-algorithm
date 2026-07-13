> **대체됨:** 이 v0.5 감사의 `67개 전체 callable` 및 `284개 요구사항` 집계는 v0.5.1 재감사에서 각각 `67개 대상 + 6개 공통 인프라 = 73개 callable`, `287개 요구사항`으로 정정됐다. 현재 판정은 [audit-v0.5.1-final.md](./audit-v0.5.1-final.md)를 사용한다.

# SPEC-XGUI v0.5 최종 문서 준비도 감사

Date: 2026-07-13
Repository HEAD: `1f7bbe0644913bc7bd910c4467d995807cf25375`
Worktree: Markdown 67개 + HTML 1개 = 문서 변경 68개, 비문서 변경 0
Audit scope: MASTER + XSEAM + 8개 그룹 + GUI 기준 + 중앙 TestSpec + Python/WPF source

## 판정

**문서 내용과 내부 교차검증: PASS / INTERNALLY_REVIEWED**

**사용자 승인: PENDING_USER**

**구현 착수: NOT AUTHORIZED**

G0는 내부 조건 1~11을 통과했고 조건 12 사용자 명시 승인만 남았다. 이 PASS는 코드 구현 완료나 구현 착수 허가가 아니다.

## 1. 문서 세트

| 검사 | 결과 |
|---|---:|
| 규범 세트 | MASTER + XSEAM + 8그룹 = 10 |
| 필수 4파일 | 40/40 |
| 기준선 버전 | 0.5.0 일치 |
| document status | `internally_reviewed` 일치 |
| approval state | `pending_user` 일치 |
| implementation authorized | `false` 일치 |
| SPEC 디렉터리의 audit report | 0 |

## 2. 요구사항·시험·operation 완결성

| 검사 | 결과 |
|---|---:|
| 정규 EARS 요구사항 | 284/284 acceptance 추적 |
| 그룹 GUI TC | 64/64, 그룹 간 교차오염 0 |
| 중앙 GUI TC | XDET-TC-096~167 = 72/72 |
| catalog target EntryPoint | 67/67 source symbol 존재 |
| FeatureId | 51/51 고유 |
| 실행 family | 9/9 |
| 공개 Python 예외형 | 17/17 typed error 매핑 |
| Params authority key | 106/106 문서 존재 |
| Calib payload key | 16/16 문서 존재 |

`DERIVED`/`INFRASTRUCTURE`를 포함한 67개 EntryPoint는 모두 source에서 해석됐다. 독립 실행 surface인 51개 FeatureId는 중복 없이 입력 family, 결과, Params/Calib 권위, GUI/TC를 갖는다.

## 3. 실제 사용·검증 가능성

- 각 그룹은 input/input-set, Params, CalibSet, 실행, result/error, evidence, artifact/reopen 경로를 모두 정의한다.
- 등록 fixture 부재는 알고리즘 비활성으로 평탄화하지 않는다. strict 사용자 입력은 실행하고 승인 전 `USER_SUPPLIED_UNVERIFIED`로 유지한다.
- SAMPLE은 유한·비퇴화·구조 sanity만, SYNTHETIC은 승인된 합성 oracle만 판정하며 무단 `GOLDEN_APPROVED` 승격은 금지한다.
- pipeline order, DSP, metric, DQE, tier, calibration, Lag/NDT state는 Python golden 소유다. WPF/UI 재계산은 금지한다.
- DQE는 `NPS_BINS_WITHIN_MTF_SUPPORT_V1`, `mtf_value_at`→`compute_dqe`, support 밖 bin 제외를 강제한다.
- mask는 `numpy.uint8` bitfield로 보존하고 frame artifact와 분리한다.

## 4. 정량 평가 기준

| 항목 | 기준 |
|---|---|
| W/L | 100회 p95 100 ms 이하, 최대 200 ms 이하 |
| cold start | 새 프로세스 5회 각각 10 s 이하 |
| peak RSS | 2 GiB 이하 |
| cache | full-frame 8, thumbnail 256, 50-frame 2회차 증가 64 MiB 이하 |
| responsiveness | heartbeat gap 200 ms 이하, Canceled 250 ms 이하, late commit 0 |
| normalized artifact | 재열기 절대오차 0.5/65535 이하 |
| determinism | 동일 실행 3회 result/hash bit-identical |
| 반복 안정성 | 20회 RSS 기울기 1 MiB/run 이하, handle/thread 단조 증가 0 |

GUI 평가 문서에는 미정 임계와 임시 평가 표지가 없다. 알고리즘 `[T]`는 외부 Params/config가 권위인 튜닝 provenance 등급으로만 유지한다.

## 5. 정적 무결성

| 검사 | 결과 |
|---|---:|
| 상대 링크(변경 Markdown 67개, 코드 스팬·펜스 제외) | 95/95 |
| literal `\\n` 형식 오류 | 0 |
| Requirement ID 중복 | 0 |
| FeatureId 중복 | 0 |
| 미완료 표지 | 0 |
| 현재 규범의 v0.4 혼입 | 0 — 변경 이력만 보존 |
| `git diff --check` | PASS |
| 비문서 변경 | 0 |

## 6. 프레임워크와 구현 순서

- 제품 GUI는 `.NET 9 WPF` 하나다.
- Qt/PySide/napari는 과거 비교 자료이며 제품 프레임워크나 WPF 실행 경계로 도입하지 않는다.
- 순서는 `M0 문서 → M0.5 내부 감사·사용자 승인·동결 → M1 공통 셸 → M2 전체 seam → M3 그룹 → M4 저장/재열기 → M5 검증`이다.
- 현재는 M0.5의 사용자 승인 전이므로 M1에 진입하지 않는다.

## 7. G0 상태

| 조건 | 상태 |
|---|---|
| 1~11 문서·집합·정량·링크·감사 | PASS |
| 12 사용자 명시 승인 | PENDING |
| 기준선 동결 | NO |
| 구현 허가 | NO |

사용자가 v0.5.0 범위와 문서를 승인하면 `baseline-control.md`에 승인 버전·일시·범위를 기록하고 모든 규범 문서의 승인 상태를 동기화해야 한다. 그 전에는 구현하지 않는다.
