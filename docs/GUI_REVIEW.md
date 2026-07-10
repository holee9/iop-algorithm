# GUI 검토 메모 — 단위 모듈/파이프라인 검증 도구

> 이 문서는 **SPEC이 아니다.** P1 완료 후 사용자와의 논의를 기록해 향후 상세 설계·SPEC 작성(manager-spec 위임)의 출발점으로 삼기 위한 검토 메모다. 범위가 확정되면 정식 EARS SPEC으로 재작성한다.

관련 이슈: #14

## 1. 배경

P1(11개 SPEC, T0~T10)은 `common/ modules/ pipeline/ metrics/` 4계층 순수 라이브러리로 완료되었고, 검증 수단은 pytest(465 passed)뿐이다. 사용자가 raw 파일을 직접 열어 보정 전/후 결과를 눈으로 확인하거나 비교할 방법이 현재 없다는 문제가 제기되어 검토를 시작했다.

## 2. 현재 상태 (확인됨)

- `pyproject.toml`에 CLI/서버/GUI 엔트리포인트(`scripts`/`entry-points`) 없음
- `scripts/`에는 `test.ps1`/`test.sh` — 테스트 러너뿐
- `streamlit|PyQt|PySide|tkinter|gradio|flask|fastapi` 등 GUI/서버 관련 의존성·코드 전무
- 유일한 "실행" 경로는 pytest와 세션 scratchpad의 임시 데모 스크립트(`run_demo.py`, 저장소 밖) — 저장소에는 재현 가능한 사용자용 진입점이 없다

## 3. 아키텍처 정합성 — "순수 라이브러리가 깨진다"는 우려는 부정확

초기 검토에서 GUI 도입이 "순수 라이브러리 성격을 깨뜨린다"고 판단했으나, 재검토 결과 이는 부정확한 우려였다.

- `common/modules/pipeline/metrics`의 순수함수 계약(SWR-000-6~12: `process(XFrame, CalibSet, Params) -> XFrame`, 사이드채널 금지)은 GUI 존재 여부와 무관하게 그대로 유지 가능
- GUI를 `common/modules/pipeline/metrics`를 **import만 하는 일방향 소비자**로 두면, import-linter 계약(`module → common` 단방향, 모듈 간 직접 호출 금지)에 영향이 없다 — `tests/`, 세션 데모 스크립트와 동일한 위치의 소비자일 뿐
- `common/contract.py`의 `ProcessModule` 프로토콜과 `run_harness()` / `check_process_contract()`는 이미 "모듈 하나 + fixture 하나 → 입출력 검증"이라는 단위 검증 하네스를 제공한다. T0 DoD("모듈마다 fixture 동봉 단위시험")와도 직접 연결됨
- 따라서 GUI는 새로운 개념이 아니라 **기존 하네스의 시각화 확장**으로 볼 수 있다 — fixture/raw 파일 선택 → 모듈(또는 파이프라인) 실행 → 입력/출력/마스크 diff/지표를 화면에 표시

결론: GUI 도입 자체가 아키텍처 원칙과 충돌하지 않는다. 실질적 트레이드오프는 순수성이 아니라 **새 의존성 추가 + 유지보수 표면 증가 + 범위를 어디까지 잡을지**의 문제다.

## 4. 후보 범위 (사용자 확정 대기)

| 옵션 | 내용 | 장점 | 단점 |
|---|---|---|---|
| A. 단위 모듈 검증기 | fixture/raw 파일 선택 → 모듈 1개(offset/gain/defect/...) 실행 → 입력·출력·마스크 diff 시각화 | `ProcessModule`/`run_harness`와 직결, 구현 리스크 최소, 빠르게 착수 가능 | 파이프라인 전체 흐름은 못 봄 |
| B. 전체 파이프라인 비교 뷰어 | raw+CalibSet 입력 → `CANONICAL_ORDER` 전체 실행 → 스테이지별 전/후 이미지 + 최종 지표(MTF/NPS/DQE 등) 비교 | 사용자 체감 가치 큼(실사용 시나리오와 가장 가까움) | CalibSet 준비 UX, 지표 시각화까지 한 번에 설계해야 해서 범위가 넓음 |
| C. A+B 통합(탭 전환) | 하나의 앱에서 모듈 검증/파이프라인 비교를 탭으로 제공 | 완성도 가장 높음 | SPEC/구현 범위가 가장 크고 1차 완료까지 시간이 더 걸림 |
| D. 미정 | 범위를 아직 정하지 않고 SPEC 작성 단계에서 manager-spec과 함께 논의 | — | — |

*(2026-07-10 논의 시점 사용자 응답: "다시 디테일하게 작업할 예정" — 위 표는 그 시점까지의 검토 결과이며 옵션 선택은 아직 확정되지 않음)*

## 4.5 운영 형태 결정 — 서브 프로젝트 확정 (2026-07-10)

별도 프로젝트(독립 저장소) 분리 여부를 검토한 결과, **이 저장소 내 서브 프로젝트(`apps/gui/` + optional extras)로 확정**한다. 별도 프로젝트 분리는 기각.

기각 사유:

1. **코어 계약 종속**: GUI는 `ProcessModule`/`run_harness()`/`CANONICAL_ORDER`/XFrame 마스크 구조를 직접 소비하는 검증 하네스의 시각화 확장이며, 소비자가 xdet 하나뿐이다. TBD-[B] 9건·TBD-[T] 11건이 미확정이라 코어 계약이 계속 변하는 시기이므로, 분리 시 크로스 레포 버전 동기화 비용만 발생하고 이득이 없다
2. **격리는 저장소 내부에서 해결 가능**: 분리의 유일한 실질 논거인 "순수 라이브러리 오염"은 (a) `[project.optional-dependencies] gui` 의존성 격리, (b) import-linter forbidden 계약 추가(코어 4계층 → `apps.gui` 역참조 금지), (c) `tool.setuptools.packages` 목록 제외로 배포물 격리 — 세 가지 정적 장치로 전부 차단된다
3. **fixture·데이터·추적 체계 공유**: 합성 팬텀 fixture(`tests/fixtures`), 골든 데이터(`data/`, LFS), SPEC/RTM 추적이 모두 이 저장소에 있어 분리 시 복제 또는 크로스 레포 계약이 필요하다 (단일 출처 원칙 위반)

분리 재검토 조건 (해당 전까지는 재논의하지 않음): GUI가 xdet 외 파이프라인을 지원하는 범용 도구로 성장하거나, P2 이후 독자 릴리스 주기·사용자층을 갖게 될 때. 단방향 의존이므로 그 시점에 저장소 분리 비용은 낮다.

## 5. 기술적 고려사항 (범위 확정 시 SPEC에 반영할 항목)

- **UI 프레임워크**: Streamlit(빠른 착수, 로컬 전용) vs Jupyter 기반 뷰어(추가 서버 불필요, 대화형 탐색에 강함) vs 데스크톱(Tkinter/PyQt, 배포 단순하나 개발 비용 큼) — 트레이드오프 비교가 필요
- **입력 포맷**: raw 16-bit + 메타데이터 JSON(기존 데이터 규약)을 그대로 재사용
- **CalibSet 준비 UX**: 실측 CalibSet이 없는 경우 합성 팬텀 fixture로 대체 가능해야 함(현재 T1~T10 테스트가 이미 이 패턴을 사용)
- **의존성 정책**: GUI 전용 의존성(streamlit 등)을 core 라이브러리 의존성과 분리 — `pyproject.toml`에 optional extras(`[gui]`)로 격리해 "순수 라이브러리로서의 설치"를 계속 지원
- **배치 위치**: `apps/gui/`로 확정 (§4.5 운영 형태 결정 참조) — `common/modules/pipeline/metrics`를 참조는 하되 역참조는 없어야 하며, import-linter forbidden 계약을 SPEC에 포함해 CI에서 강제

## 6. 다음 단계

1. 사용자가 §4 범위(A/B/C/D)를 확정
2. 확정되면 `manager-spec`에 위임해 EARS 형식 정식 SPEC 작성(예: `SPEC-VIEWER-001`)
3. 이후 절차는 기존 11개 SPEC과 동일: plan-audit → TDD 구현 → 독립 코드 리뷰 → sync → merge

## 참고

- 관련 코드: `common/contract.py`(`ProcessModule`, `run_harness`, `check_process_contract`), `pipeline/orchestrator.py`(`CANONICAL_ORDER`, `run_pipeline`)
- 관련 이슈: #14
- 관련 문서: [`docs/P1_COMPLETION_REPORT.md`](P1_COMPLETION_REPORT.md), [`../README.md`](../README.md)
