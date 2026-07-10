# SPEC Review Report: SPEC-VIEWER-001
Iteration: 2/3
Verdict: PASS
Overall Score: 0.94

> Reasoning context ignored per M1 Context Isolation. "저자가 전부 고쳤다"는 주장은 무시하고, `.moai/specs/SPEC-VIEWER-001/{spec.md(v0.1.1),plan.md(v0.1.1),acceptance.md}` 현재 파일과 코드 사실(`common/contract.py` L131~152, `pyproject.toml` L25/L31/L41~104, `tests/fixtures/badlayers/`, `tests/test_tc000.py` L86~113, `tests/test_tc_skeletons.py`), 기준 문서(`docs/GUI_CRITERIA.md` C-10/C-15 원문)만으로 재검증했다. PASS 임계: 0.90. 가중치(iter1과 동일): Clarity 0.30 · Completeness 0.25 · Testability 0.25 · Traceability 0.20.

## 회귀 검사 (Regression Check) — 이전 결함 D1~D10 전수 재검증

- **D1 (major) — RUN-1 `run_harness` 시그니처·반환 모순: [RESOLVED]** (단, 전파 누락 2개소를 신규 결함 N1로 등재). 코드 재확인: `common/contract.py:131-137` `run_harness(module, input_frame, calib, params, expected) -> MismatchReport` — `expected` 필수, L150-152에서 결과 프레임은 `_compare_output` 비교 후 폐기(출력 XFrame 미반환) — iter1 판정 재확증. v0.1.1 정합화 확인: spec.md:L95 RUN-1 본문이 "처리 계약 표면으로 직접 실행해 출력 XFrame을 산출"로 재정의되고 괄호에 "raw·fixture 두 입력 모두 `process` 직접 실행이 유일한 출력 산출 경로 … `run_harness`는 … 출력 XFrame을 반환하지 않으므로 시각화 산출 경로와 분리"를 명시. 파급 전 지점 수정 확인 — spec.md:L15("출력 XFrame은 `ProcessModule.process`가 직접 산출 … expected 골든이 동봉된 fixture에서만 `run_harness` 검증을 병행"), spec.md:L59(소비 계약: "`run_harness(...)->MismatchReport` = expected 필수·출력 프레임 미반환의 fixture 검증 전용"), acceptance.md:L28(Scenario 4 Given: "`ProcessModule.process`로 실행한 입력·출력 XFrame 쌍"), L35(Scenario 5 Then (a): "raw·fixture 공통 유일 산출 경로 … 이 하네스는 출력 프레임을 산출하지 않음"), L119(DoD), plan.md:L20(§1)·L51(§3 module_panel). iter1 권고("run_harness에 반환 프레임 추가 방향 금지, 코어 표면 불변 유지")대로 코어 무변경 방향으로 해소됨.
- **D2 (major) — #18 배치 "또는" 비결정: [RESOLVED]**. plan.md:L64 — "`common/synth_calibset.py` … common/ 단일 배치 — packages 목록 포함으로 배포 가능, REQ-VIEW-CORE-3"로 단일 확정, "또는" 분기 제거. spec.md:L134(결정 필요 2)에 "단일 확정 … `pyproject` `packages`=common/modules/pipeline/metrics가 apps 미포함 → 단일 답 강제"로 등재. plan.md:L81("코어에 추가되는 것은 additive 3건")과 내부 정합. pyproject.toml:L25 `packages = ["common","modules","pipeline","metrics"]` 재확인 — 근거 유효.
- **D3 — 카나리 심기 위치 자기모순: [RESOLVED]**. acceptance.md:L70-72 EC-2 — `tests/fixtures/badgui/`(`root_packages` 밖) 전용 픽스처 + 임시 import-linter 설정(`lint-imports --config <tmp>`) 실행 + `returncode≠0`·위반 출력 비어있지 않음 assert로 메커니즘 단일 확정. "코어 계층에 심되 프로덕션 트리 밖" 모순 문구 소거. 선례 검증: `tests/fixtures/badlayers/`(`__init__.py`/`high.py`/`low.py`) 실재, `tests/test_tc000.py:86-113` `test_tc000_B_import_linter_detects_violation`이 정확히 동일 패턴(임시 ini + `--config` + `returncode != 0`) + L43-45 vacuous-pass 가드까지 보유 — 인용된 음성대조 선례가 실행 가능한 실코드로 존재. spec.md:L136(결정 필요 4)·plan.md:L77-78/L139 삼면 정합.
- **D4 — EARS 라벨 2건: [RESOLVED]**. spec.md:L98 RUN-4가 Ubiquitous("시스템은 모든 지표 산출을 GUI 코드 경로에서 계산하지 않고 `metrics/` 엔진에 위임해야 한다")로 재라벨. spec.md:L91 COMPARE-7 Optional에서 THEN 키워드 제거("WHERE 로드된 XFrame이 처리 이력 체인을 가지면, 뷰어가 그 체인 … 을 표시해야 한다"). plan.md:L91 그룹 요약 라벨(`[Ubiquitous]`)도 동기화됨.
- **D5 — SPIKE-3/CORE-4 판정 주체 미귀속: [RESOLVED]**. acceptance.md:L7 자동 검출 목록에 "…전건 KEPT(CORE-4, Scenario 2(d) — 계약 서명·import-linter 실행으로 자동 검출)" 귀속, L8 코드리뷰 목록에 "Phase 게이트 순서(SPIKE-3: … 워크플로/마일스톤 게이트 리뷰 규칙, 자동 이진 판정 아님)" 귀속 — iter1 권고 문안 그대로.
- **D6 — 규범 본문 구현 식별자 3건: [RESOLVED]**. spec.md:L74 CORE-4 본문은 "기존 코어 처리 계약·오케스트레이터 실행 순서·기존 import-linter 계약"으로 일반화되고 `process(...)`·`CANONICAL_ORDER`는 괄호로 이동. L96 RUN-2 WHEN 본문에서 `CANONICAL_ORDER` 제거(괄호 이동). L110 ARCH-5 본문 "오프스크린으로 실행되어야 한다" + `QT_QPA_PLATFORM=offscreen` 괄호 이동.
- **D7 — ARCH 헤더 C-17 과대 표기: [RESOLVED]**. spec.md:L104 "C-11~C-16·C-18·C-19 … C-17은 SPIKE-1/SG-3 소관", plan.md:L92 동일 정정.
- **D8 — #19 처분 미확정: [RESOLVED]**. spec.md:L123 Exclusions에 "#19 인체공학 개선 별건(범위 밖)" 신설 + L21 인트로에 "(Exclusions 참조)" 연결.
- **D9 — 캡스톤 스캔 오등록 리스크: [RESOLVED]**. spec.md:L58(Environment)에 "GUI 테스트 소스는 Gen 1 TC id 문자열(`000`~`021`)을 포함하지 않아 … 오등록하지 않는다(캡스톤 무간섭의 성립 조건, D9)" 제약 추가, L137(결정 필요 5)·acceptance.md:L132(DoD 체크박스 "GUI 테스트 소스 Gen 1 TC id(000~021) 문자열 미포함") 등재. 코드 대조: `tests/test_tc_skeletons.py:99`는 `'XDET-TC-016'`과 `'TC-016'` 두 토큰 형태를 모두 매칭하므로 제약이 실질적으로 유효.
- **D10 — core-no-gui 수집 배제 공백: [RESOLVED]**. plan.md:L136 — "`pytest --ignore=tests/apps`로 … 수집·실행"(1차) + "각 GUI 테스트 모듈 상단 `pytest.importorskip("napari"/"qtpy")` 가드"(2차) 이중 메커니즘 명시, acceptance.md:L126 DoD에 반영. pyproject.toml:L31 `testpaths = ["tests"]` 재확인 — 배제 메커니즘 필요성·해법 정합.

**정체(stagnation) 결함: 0건.** 3회 연속 미해결 결함 없음.

## Must-Pass Results

- [PASS] **MP-1 REQ 번호 일관성**: 35개 전수 재계수 — SPIKE-1~3(spec.md:L65-67), CORE-1~4(L71-74), IMAGE-1~4(L78-81), COMPARE-1~7(L85-91), RUN-1~8(L95-102), ARCH-1~9(L106-114). 그룹별 순차, 갭 0건, 중복 0건. v0.1.1 편집으로 인한 번호 재배치·결번 없음.
- [PASS] **MP-2 EARS 형식 준수**: 35건 전수 재검사 — Event-Driven 20 · Ubiquitous 6(IMAGE-4, COMPARE-6, **RUN-4**, ARCH-1/5/9) · State-Driven 4(SPIKE-3, RUN-6, ARCH-6/7) · Unwanted 4(SPIKE-2, CORE-4, RUN-8, ARCH-4) · Optional 1(COMPARE-7) = 35. iter1 caveat 2건(RUN-4 라벨, COMPARE-7 THEN 혼합) 해소로 **caveat 없는 PASS로 격상**. 재작성된 RUN-1(L95)·RUN-4(L98)·COMPARE-7(L91)·CORE-4(L74)·RUN-2(L96)·ARCH-5(L110) 전건이 패턴 키워드-라벨 정합. 신규 EARS 위반 0건.
- [PASS] **MP-3 YAML 프론트매터 유효성**: spec.md:L1-11 — 8필드(id/version/status/created/updated/author/priority/issue_number)+labels 배열 전부 존재·타입 유효. **버전 동기화 확인**: spec.md:L3 `version: 0.1.1` = plan.md:L4 `version: 0.1.1`, HISTORY(spec.md:L28)에 v0.1.1 엔트리 존재 — 문서 간 버전/HISTORY 불일치 없음. acceptance.md 프론트매터 부재는 저장소 전체 관행(SPEC-TIER-001/SPEC-INFRA-001 acceptance.md 동일 형식 확인)으로 결함 아님.
- [N/A] **MP-4 언어 중립성**: Python 단일 언어 검증 도구 SPEC — N/A: single-language SPEC.

## 회귀 스윕 (신규 결함 탐색 — 수정이 부순 것)

- **교차 참조**: HISTORY의 D1~D10 서술(spec.md:L28-38) ↔ 실제 수정 지점 전건 대조 — 허위 주장 0건(주장된 수정 전부 실재). 결정 필요 2(L134)↔plan §3(L64), 결정 필요 4(L136)↔EC-2(acceptance L70-72)↔plan L78/L139, 결정 필요 5(L137)↔spec L58↔DoD L132 삼면 정합.
- **추적성 재검**: 35 REQ 전수가 Scenario 1~10 + DoD 체크리스트(acceptance.md:L104-133)에 ID 인용, 역방향 고아 0건, EC-1~6 인용 REQ 전건 실재. plan.md:L87-92 그룹 요약의 EARS 라벨이 spec 확정본과 전건 일치(RUN-4 `[Ubiquitous]` 동기화 포함).
- **잔존 구본(stale) 텍스트**: `run_harness` 전 출현 지점을 3개 파일 전수 grep — **plan.md 2개소에서 pre-D1 문구 잔존 발견(N1)**. 그 외 spec.md의 "하네스" 잔존 표현(RUN-6 L100 "하네스에 투입", ARCH-6 L111 "모듈/파이프라인 하네스 호출")은 기준 문서 원문 인용임을 확인 — GUI_CRITERIA.md:L70(C-10 "동일 경계를 하네스에 투입하면")·L81(C-15 "모듈·파이프라인 하네스 호출") 직인용이므로 왜곡·결함 아님.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.90 | 1.0 인접(요구 전건 단일 해석) − stale 2개소 감점 | iter1 D1/D2의 해석 분기 소멸(spec.md:L95 유일 산출 경로 명시, plan.md:L64 단일 배치). 잔존: N1(plan.md:L103/L129 구본 문구) — spec 규범 우선(plan.md:L16 "EARS 확정본은 spec.md")으로 합리적 구현자가 일관 해소 가능 |
| Completeness | 1.00 | 1.0 — 전 섹션·전 갭 해소 | HISTORY(L26-45)/Environment(L47-59)/Requirements(L61-114)/Exclusions 10건(L116-127, #19 신설 포함)/결정 필요 6건 전건 기본값 보유(L129-138). iter1 갭(D7/D8/D10) 전건 해소, 신규 갭 미발견 |
| Testability | 0.90 | 1.0 인접 − 귀속 미완 1건 | EC-2 메커니즘이 실코드 선례(test_tc000.py:L86-113)와 1:1 대응하는 실행 가능 사양으로 확정. SPIKE-3/CORE-4 분류표 귀속 완료(acceptance.md:L7-8). 잔존: N2(IMAGE-2 "무복사"의 판정 귀속 미완 — iter1 Testability 관찰 항목 중 D 번호 미부여로 미수정) |
| Traceability | 1.00 | 1.0 — 전건 양방향 | 35 REQ ↔ Scenario/DoD/EC 전수 재검 갭 0(위 회귀 스윕), XDET-TC-030~037 8블록 매핑(plan.md:L67-74 = spec 그룹 헤더) 유지 |

**가중 합계**: 0.30×0.90 + 0.25×1.00 + 0.25×0.90 + 0.20×1.00 = **0.945 → 0.94** (PASS 임계 0.90 이상)

## Defects Found (신규)

N1. plan.md:L129 (§7 Phase 1 마일스톤), plan.md:L103 (§5 fixture 표) — **pre-D1 구본 문구 잔존(전파 누락)**: L129 "파일 선택 → 모듈 1개 `run_harness` 실행 → 입력/출력/diff/마스크/이력 시각화", L103 "fixture → run_harness 출력 + MaskFlag 스택". v0.1.1 확정 모델(spec.md:L95 — `process`가 유일 출력 산출 경로, `run_harness`는 출력 프레임 미반환·expected 필수로 raw 경로 호출 불가)과 문면 모순. 같은 파일의 §1(L20)·§3(L51)과 spec·acceptance가 전부 올바른 모델을 명시하고 plan.md:L16이 spec을 규범 확정본으로 선언하므로 실질 위험은 낮으나, 마일스톤 §7은 구현자가 직접 실행하는 절이므로 정정 필요. — Severity: **minor**

N2. acceptance.md:L112 (DoD "줌/팬 무복사 연속 상호작용") vs L7-8 분류표 — IMAGE-2(spec.md:L79)의 "이벤트당 전체 프레임 재계산·배열 복사 없이" 중 **"무복사" 판정이 자동 검출(L7)에도 코드리뷰(L8 — "체감 연속성"만 등재)에도 완결 귀속되지 않음**. iter1 Testability 근거란에 지적됐으나 D 번호 미부여로 이번 수정에서 누락. 권장: L8에 "줌/팬 무복사 경로(C-02)는 코드리뷰(렌더 경로 검사)" 1줄 추가 또는 L7에 로직 레벨 근사 단정(콜백 내 배열 복사 부재) 귀속. — Severity: **minor**

미채점 관찰(trivial, 결함 아님): (a) plan.md:L59/L63 파일 트리에 `common/` 헤더가 이슈별로 2회 분리 표기 — 표기 관행 문제. (b) spec.md:L29 HISTORY의 "spec L15/L48" 인용은 v0.1.0 시점 행번호(현 L59) — 이력 기록으로 허용. (c) spec.md:L58 "Gen 1 TC id 문자열(`000`~`021`)"은 full-id(`XDET-TC-0NN`)와 단축형(`TC-0NN`) 두 토큰을 의미함이 캡스톤 스캔 코드(test_tc_skeletons.py:L99)로 확인되나 문면에 토큰 형태 명시가 없음 — run 단계에서 스캔 가드 구현 시 자연 해소.

## Chain-of-Verification Pass

Second-look findings: (1) 35개 REQ 전수 재독 — 재작성된 6건(RUN-1/RUN-4/COMPARE-7/CORE-4/RUN-2/ARCH-5)의 라벨-본문-패턴 키워드 정합을 개별 확인, 신규 EARS 위반 0건. (2) `run_harness` 출현 지점을 세 파일 전수 grep — 1차 패스에서 놓칠 뻔한 **N1(plan.md:L103/L129)을 2차 grep 스윕에서 확정**(D1의 열거 지점만 확인하고 통과 처리할 뻔함 — 열거 밖 지점 전수 스캔으로 검출). (3) spec의 잔존 "하네스" 표현 2건(RUN-6/ARCH-6)을 결함 후보로 올렸다가 GUI_CRITERIA.md:L70/L81 원문 직인용임을 확인하고 정확히 기각. (4) acceptance.md 프론트매터 부재를 결함 후보로 올렸다가 SPEC-TIER-001/SPEC-INFRA-001 동일 형식 확인으로 저장소 관행 판정. (5) iter1 Testability 근거란의 미번호 관찰(IMAGE-2 무복사 귀속)을 재대조 — 미수정 잔존 확인, N2로 승격. (6) 버전·HISTORY 동기화(spec 0.1.1 = plan 0.1.1, HISTORY v0.1.1 엔트리) 재확인. (7) 캡스톤 스캔 토큰 형태(L99)를 코드로 재확인해 D9 제약의 실효성 검증.

## Recommendation

**PASS — 종합 0.94 ≥ 0.90.** Must-Pass 4건 전부 통과(MP-2는 iter1 caveat 해소로 무조건부 PASS 격상), D1~D10 회귀 검사 전건 RESOLVED(코드 사실·선례 실코드 대조 포함). 신규 결함은 minor 2건(N1 구본 문구 2개소, N2 무복사 귀속)으로 PASS를 차단하지 않으나, run 착수 전 처리 권장:

1. **N1**: plan.md:L129를 "모듈 1개 `ProcessModule.process` 실행(+ expected 동봉 fixture 시 `run_harness` 검증 병행)"으로, L103을 "fixture → `process` 출력 + MaskFlag 스택"으로 정정(§1/§3과 동일 문구로 통일).
2. **N2**: acceptance.md:L8 코드리뷰 목록에 IMAGE-2 "무복사" 항목 1줄 귀속(또는 L7 로직 레벨 단정 귀속).

두 건 모두 1줄 편집 수준이며 요구 재설계 불요. iteration 3 재감사는 불필요하다 — 사용자 승인 전 위 2건을 v0.1.2 패치로 접는 것으로 충분하다.
