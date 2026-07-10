# SPEC Review Report: SPEC-VIEWER-001
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.72

> Reasoning context ignored per M1 Context Isolation. 본 감사는 `.moai/specs/SPEC-VIEWER-001/{spec.md,plan.md,acceptance.md}`, 기준 문서(`docs/GUI_CRITERIA.md` C-01~C-20/SG-1~3/§4/§5, `docs/GUI_REVIEW.md` §4.5/§5), 코드 사실(`common/contract.py`, `common/xframe.py`, `pipeline/orchestrator.py`, `common/calibset.py`, `pyproject.toml` import-linter 계약 L41-104, `tests/test_tc_skeletons.py`)만을 근거로 수행했다. PASS 임계: 0.90.

## Must-Pass Results

- [PASS] **MP-1 REQ 번호 일관성**: 총 35개 REQ 전수 확인 — SPIKE-1~3 (spec.md:L54-56), CORE-1~4 (L60-63), IMAGE-1~4 (L67-70), COMPARE-1~7 (L74-80), RUN-1~8 (L84-91), ARCH-1~9 (L95-103). 그룹별 순차, 갭 0건, 중복 0건. 그룹형 `REQ-VIEW-{GROUP}-{N}` 체계는 SPEC-TIER-001/SPEC-INFRA-001과 동일한 확립 관행.
- [PASS, with caveat] **MP-2 EARS 형식 준수**: 35건 전수 재검사. 모든 REQ가 명시 패턴 태그(Event-Driven 20 · Ubiquitous 5(IMAGE-4, COMPARE-6, ARCH-1/5/9) · State-Driven 4(SPIKE-3, RUN-6, ARCH-6/7) · Unwanted 5(SPIKE-2, CORE-4, RUN-4/8, ARCH-4) · Optional 1(COMPARE-7) = 35)와 양태 술어("해야 한다"/"않아야 한다")를 갖추고, SPEC-TIER-001에서 지적된 **후행 비양태 문장 잔존 0건**(전부 괄호 인용으로 격리 — §5 준수사항 반영 확인). **Caveat**: RUN-4(L87)의 Unwanted 트리거가 undesired condition이 아닌 정상 조건이고(D4), COMPARE-7(L80)이 Optional인데 "WHERE …, THEN …"으로 패턴 키워드를 혼합(D4) — 형식 구조 자체는 성립하므로 MP-2 FAIL로 격상하지 않되 결함으로 기록.
- [PASS, with caveat] **MP-3 YAML 프론트매터 유효성**: spec.md:L1-11 — GUI_CRITERIA §5가 요구하는 8필드(id/version/status/created/updated/author/priority/issue_number) 전부 존재 + labels 배열(L10). 타입 전부 유효, `id: SPEC-VIEWER-001` 패턴 부합. `created` vs `created_at` 명명은 저장소 전체 관행(SPEC-TIER-001 review-1 D5에서 체계적·선례 있음으로 판정)이므로 FAIL로 격상하지 않음.
- [N/A] **MP-4 언어 중립성**: Python 단일 언어 검증 도구 SPEC — N/A: single-language SPEC.

## Ground-Truth Cross-Verification (독립 재검증)

- **C-01~C-20 전수 매핑 확인**: C-01→IMAGE-1, C-02→IMAGE-2, C-03→IMAGE-3, C-04→IMAGE-4/CORE-1, C-05→COMPARE-1/2, C-06→COMPARE-3/4, C-07→COMPARE-5/6, C-08→COMPARE-7, C-09→RUN-3/4, C-10→RUN-5/6, C-11→ARCH-1/2, C-12→ARCH-3, C-13→ARCH-4, C-14→ARCH-5, C-15→ARCH-6, C-16→ARCH-7, C-17→SPIKE-1(SG-3 실측)+PARTIAL(acceptance.md:L97 — 기준 문서 C-17 자체가 "스파이크 SG-3에서 실측"으로 정의하므로 충실), C-18→ARCH-9, C-19→ARCH-8, C-20→RUN-7/8+Exclusions. **누락·왜곡된 C-NN 인용 0건**(SG-3 폴백 트리거를 기준 문서의 모호한 "크게 초과 시"에서 "미충족 시"로 단일화한 것은 §2.3 헤더와 정합하는 결정론화 — 왜곡 아님). 미세 관찰: C-18의 "마스크 3장" 수량이 ARCH-9(L103) 괄호에서 "마스크"로 축약되고 "이하"가 "이하 목표"로 완화됐으나, PARTIAL(acceptance.md:L96-97)이 구조 게이트+`[T]` 처리를 명시 선언하므로 왜곡으로 보지 않음.
- **`[T]` 수치 정책**: 100ms/10s/2GB/200ms/±max|diff| 전부 `[T]` 태그+괄호 인용으로만 등장(spec.md:L46, L67, L76, L102-103), 규범 본문 하드코딩 0건. 측정=판정 분리(acceptance.md:L7-8 자동 검출 vs 코드리뷰 분류표) 준수.
- **MaskFlag 4종 검증**: common/xframe.py:L61-72 — DEFECT=1/SATURATION=2/INTERPOLATION=4/SATURATION_BAND=8, spec.md:L48/L78 인용과 정확 일치.
- **HistoryEntry 필드 검증**: common/xframe.py:L98-101 — module_name/module_version/params_hash/calibset_id, spec.md:L48/L80 인용과 정확 일치.
- **오케스트레이터 표면 검증**: pipeline/orchestrator.py — `CANONICAL_ORDER`(L30), `_calibration_gate`(L165), `run_pipeline`(L221) 실재. spec.md:L48 인용 정확.
- **캡스톤 스캔 검증**: tests/test_tc_skeletons.py:L80 `_GEN1_TC_RANGE = range(0, 22)` — spec.md:L34/L47 인용 정확. 신규 030~037 id 문자열은 000~021 부분문자열 매칭을 유발하지 않음(3자리 고정 패딩 확인) — TC 블록 분리 자체는 성립. 단, 스캔이 `tests_root.rglob("*.py")`(L103-105)로 `tests/apps/gui/`를 포함하는 데서 잔여 리스크 발견(D9).
- **run_harness 시그니처 검증**: common/contract.py:L131-137 — `run_harness(module, input_frame, calib, params, expected) -> MismatchReport`. **`expected` XFrame이 필수 인자이고 반환값은 MismatchReport(passed, violations)로서 출력 XFrame을 반환하지 않음**(L146-152: 결과 프레임은 `_compare_output` 비교 후 폐기). REQ-VIEW-RUN-1의 "하네스로 실행해 입력·출력 XFrame을 산출"과 정면 모순 — D1 (major).
- **import-linter additive-KEPT 실행 가능성 검증**: pyproject.toml 계약 6건(L44-104) 대조 — (a) #16 `common/io.py`: contract 3(common→상위 금지, L61-65)은 common 내부 추가에 무영향, KEPT 성립. (b) #15 `modules/registry.py`: independence 계약(L67-85)은 12개 보정 모듈만 열거하므로 registry가 이들을 등록용으로 import해도 계약 목록 변경 불필요, layers 계약은 동일 계층 내 import를 제약하지 않음 — KEPT 성립. (c) #18 `common/` 배치 시 KEPT 성립. 즉 "additive-only, 전 계약 KEPT" 주장 자체는 코드 검증상 실행 가능 — PROCEED. 단, 신규 forbidden(코어→apps.gui) 추가에는 `root_packages`에 apps 추가 또는 `include_external_packages` 설정이 필요(기존 계약 의미에는 무영향인 구현 세부 — 결함 아님, plan.md HOW 보강 권장).
- **카나리 설계의 헛통과 검출력**: 위반을 심고 lint FAIL을 assert하는 구조(ARCH-2, EC-2)는 lesson #1(vacuous pass — CLI가 실행 없이 exit 0)의 원인과 무관하게 헛통과를 검출한다 — 메커니즘 방향은 옳음. 단 EC-2의 심기 위치 서술이 자기모순(D3).
- **GUI_REVIEW §4.5 정합**: `apps/gui/` 서브 프로젝트 + `[gui]` extras + forbidden 계약 + 배포물 격리(packages 목록 제외) — spec.md:L39/L43과 정합. pyproject.toml:L25 `packages = ["common","modules","pipeline","metrics"]` 확인(apps 미포함) — 이것이 D2의 근거가 됨.
- **선행 이슈 표(§4) 대조**: #15/#16/#18 load-bearing Phase 1 ✓(spec.md:L21/L44), #17 축소판 Phase 2 ✓(RUN-7, 결정 필요 3), #19는 언급만 있고 처분 미확정(D8).

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.50 | 0.50 — 복수 요구에서 합리적 구현자가 서로 다르게 구현 | D1(spec.md:L84 — run_harness 시그니처·반환 모순으로 구현 경로 3분기: 코어 변경/직접 process 호출/더미 expected), D2(plan.md:L63-64 — #18 배치 "또는" 2분기, 한 분기는 REQ 위반). 그 외 요구는 단일 해석으로 매우 명확 |
| Completeness | 0.75 | 0.75 — 비치명 갭 수건 | 전 섹션 존재(HISTORY L26-34, Environment L36-48, Requirements L50-103, Exclusions L105-115 구체 9건, 결정 필요 L117-126 전건 기본값 보유). 갭: C-17 헤더 과대 표기(D7), #19 처분 미확정(D8), core-no-gui 수집 배제 메커니즘 미지정(D10) |
| Testability | 0.75 | 0.75 — 소수 AC가 판정 방법 미확정 | 자동 검출 vs 코드리뷰 분리(acceptance.md:L7-8)가 모범적. 갭: SPIKE-3/CORE-4 프로세스 요구의 자동 판정 불가+분류표 미등재(D5), EC-2 설정 자기모순(D3), IMAGE-2/C-02 DoD 체크박스(L112)의 검증 메커니즘이 L7 자동 검출 목록에도 L8 리뷰 목록("체감 연속성"만)에도 완결 귀속되지 않음 |
| Traceability | 1.00 | 1.0 — 전건 양방향 | 35 REQ 전수가 Scenario 1~10 + DoD(L104-133)에 ID 인용(SPIKE S1, CORE S2, IMAGE S3, COMPARE-1~6 S4/COMPARE-7 S10, RUN-1·3~6 S5/RUN-2 S6/RUN-7·8 S7, ARCH-1~4 S8/ARCH-5·6·8·9 S9/ARCH-7 S6). 역방향 고아 0건(EC-1~6 인용 전부 실재 REQ). 산출물 WHEN 트리거 생산자 명시(COMPARE-3→RUN-1/2, RUN-6→RUN-3, EC-1→SPIKE-1 리포트). XDET-TC-030~037 8블록 완전 매핑(plan.md:L67-74 = spec 그룹 헤더) |

## Defects Found

D1. spec.md:L84 (REQ-VIEW-RUN-1; 파급 spec.md:L15/L48, acceptance.md:L28/L34-35/L119, plan.md:L20/L51) — **"하네스로 실행해 입력·출력 XFrame을 산출"·"`run_harness` 직결"이 코드 현실과 모순**: `run_harness(module, input_frame, calib, params, expected)`는 (a) `expected` XFrame이 **필수 인자**여서 골든 expected가 없는 raw 입력 경로(REQ 트리거가 명시하는 "fixture **또는 raw** 입력")에서는 호출 자체가 불가하고, (b) 반환값이 `MismatchReport`(passed/violations)로서 **출력 XFrame을 산출·반환하지 않는다**(common/contract.py:L131-152). 그대로 구현하려면 run_harness 변경(스스로 금지한 "소비 대상 계약 변경 없음" L23/L48 위반) 또는 `module.process` 직접 호출(REQ 문언 이탈)의 양자택일이 강제된다. spec.md:L48이 시그니처를 정확히 인용하면서도 그 함의를 RUN-1에 반영하지 않았다. — Severity: **critical~major → major** (문서 전반의 핵심 실행 경로 서술이며 Scenario 4 Given·Scenario 5 Then (a)·DoD L119까지 연쇄)

D2. plan.md:L63-64 — **#18 합성 CalibSet 팩토리 배치가 "`common/ 또는 apps/gui/fixtures/`"로 비결정**("또는" — GUI_CRITERIA §5 "결정론 규칙에 또는 금지" 위반). 한 분기(apps/gui/fixtures)는 REQ-VIEW-CORE-3(spec.md:L62)의 "**배포 가능한** 합성 CalibSet 팩토리" 및 "배포 코드 승격"(spec.md:L21/L31)과 모순 — pyproject.toml:L25 `packages`에 apps가 없으므로(GUI_REVIEW §4.5 배포물 격리 설계상 의도적) apps/gui 하위는 배포 불가. plan.md:L79 자신도 "코어에 추가되는 것은 additive 3건"이라며 #18을 코어 추가로 열거해 L63-64와 내부 모순. 「결정 필요/확인 사항」에도 이 배치 질문은 미등재. — Severity: **major**

D3. acceptance.md:L70 (EC-2 Given; spec.md:L124 결정 필요 4 동반) — 카나리 심기 위치 서술 자기모순: "위반을 **코어 계층에** 임시로 심은 상태(테스트 로컬, **프로덕션 트리 밖**)". import-linter는 `root_packages` 패키지 트리만 그래프에 올리므로 프로덕션 트리 **밖**의 위반은 forbidden 계약을 실패시킬 수 없다 — 문언 그대로면 카나리가 구조적으로 성립 불가(구현 시 시끄럽게 실패하므로 침묵 리스크는 아니나, 사양으로서 모순). 임시 복제 패키지 트리에서 lint 실행 또는 패키지 내 임시 파일 생성+정리 중 하나로 메커니즘을 확정해야 함. — Severity: minor

D4. spec.md:L87 (RUN-4), L80 (COMPARE-7) — EARS 라벨 정합성 2건: RUN-4는 Unwanted인데 트리거 "IF 어떤 지표 값이 필요하면"이 undesired condition이 아닌 정상 운용 조건(금지 불변식이므로 Ubiquitous "시스템은 GUI 코드 경로에서 지표를 계산하지 않아야 한다"가 정형). COMPARE-7은 Optional인데 "WHERE …, THEN …"으로 THEN 키워드 혼합(정형 Optional은 "WHERE …, 뷰어가 …해야 한다"; 아울러 런타임 조건이므로 State/Event 계열이 더 정확). — Severity: minor

D5. spec.md:L56 (SPIKE-3), L63 (CORE-4) — 시스템 요구가 아닌 프로세스/메타 요구: SPIKE-3 "Phase 1 구현 착수를 진행하지 않아야 한다"는 워크플로 게이트로 자동 이진 판정 불가, CORE-4의 트리거 "구현이 …변경하려 하면"은 관측 가능한 시스템 이벤트가 아님(검증 가능한 실체는 "Phase 0.5 이후 계약 전건 KEPT" 불변식 — Scenario 2 (d)가 실질 판정). 두 건 모두 acceptance.md:L7(자동 검출)/L8(코드리뷰) 분류표 어느 쪽에도 귀속되지 않아 판정 주체가 미확정. — Severity: minor

D6. spec.md:L63 (CORE-4: `process(XFrame,CalibSet,Params)->XFrame`·`CANONICAL_ORDER`), L85 (RUN-2: WHEN 본문 내 `CANONICAL_ORDER`), L99 (ARCH-5: 본문 내 `QT_QPA_PLATFORM=offscreen`) — 규범 REQ 본문 내 구현 식별자(HOW) 누출, GUI_CRITERIA §5 "규범 REQ 본문에 파일/클래스 식별자 금지 — plan.md/괄호로 이동" 위반. 대다수 REQ는 괄호 인용으로 격리했으나 이 3건은 본문 잔존. SPEC-TIER-001 D2와 동일 계열의 체계적·선례 있는 약점. — Severity: minor

D7. spec.md:L93, plan.md:L90 — REQ-VIEW-ARCH 그룹 헤더가 "C-11~C-19"를 표방하나 ARCH-1~9는 C-11/12/13/14/15/16/19/18만 커버 — **C-17은 ARCH 그룹에 부재**(SPIKE-1의 SG-3 실측+PARTIAL로 처리됨 — 처리 자체는 기준 문서 정합이므로 탈락은 아니나 헤더 범위 표기가 과대). — Severity: minor

D8. spec.md:L21 — 이슈 **#19(인체공학: 재수출/`REQUIRED_PARAMS`/Params 검증/반환형 통일)의 범위 처분 미확정**: "병행 가능"이라는 GUI_CRITERIA §4 표의 문구만 재인용하고, 본 SPEC의 in-scope(어느 Phase)인지 out-of-scope(Exclusions)인지 어디에도 확정하지 않았으며 「결정 필요/확인 사항」에도 미등재. — Severity: minor

D9. spec.md:L47, acceptance.md:L132 ("캡스톤 스캔 무간섭" 주장) vs tests/test_tc_skeletons.py:L103-108 — 캡스톤 스캔은 `tests/` 전체 `rglob("*.py")`이므로 신규 `tests/apps/gui/*.py`도 corpus에 포함된다. 030~037 id 자체는 무간섭이 맞으나, GUI 테스트 소스가 Gen 1 id 문자열(예: C-12 잡 설명 성격의 "XDET-TC-000~021" 언급 — plan.md:L134와 같은 표현이 테스트 docstring에 들어갈 경우)을 포함하면 해당 Gen 1 TC를 '살아있음'으로 오등록해 **향후 Gen 1 테스트 삭제를 마스킹**할 수 있다. "무간섭"을 성립시키려면 GUI 테스트 소스 내 Gen 1 id(000~021) 문자열 금지 제약 또는 스캔에서 `tests/apps/` 제외를 명시해야 함. — Severity: minor

D10. plan.md:L134 (core-no-gui 잡), pyproject.toml:L31 (`testpaths = ["tests"]`) — `[gui]`-less base 설치에서 "전체 코어 TC 실행"이 pytest 기본 수집으로는 `tests/apps/gui/`까지 수집해 napari/Qt 부재로 **수집 단계 ImportError**가 난다. GUI 테스트 배제 메커니즘(`--ignore=tests/apps`, `pytest.importorskip` 가드, 마커 등)이 spec/plan 어디에도 지정되지 않음 — ARCH-3(C-12)의 실행 가능성 공백. — Severity: minor

## Chain-of-Verification Pass

Second-look findings: (1) 35개 REQ를 전수 재독해 EARS 라벨-본문 정합을 개별 확인 — D4의 모집단이 완전함을 확인(IMAGE-1/2·RUN-2·COMPARE-3의 트리거 내 "하거나/또는"은 이벤트 열거이지 결정론 규칙의 비결정 택일이 아니므로 정확히 제외; SPIKE-2·EC-1은 "단일 순서 결정 — 또는 없음"을 명시해 §5 준수). (2) 후행 비양태 문장을 전 REQ에서 재스캔 — 0건 재확인(SPEC-TIER-001 D4 계열 결함이 본 SPEC에서 교정됨). (3) 추적성을 35건 전수+역방향 전수로 재검 — 갭 0 재확인. (4) Exclusions 9건의 구체성 재검 — 전부 C-NN/SWR 앵커 보유, 모호 항목 0건. (5) 문서 간 교차 모순 재탐색에서 **D10을 2차 패스에서 신규 발견**(1차 패스에서는 core-no-gui 잡을 통과 처리했으나, pyproject `testpaths` 전역 수집과 대조하자 배제 메커니즘 공백이 드러남). (6) run_harness 모순(D1)은 contract.py 원문 재독(L131-152)으로 재확증 — `result`는 비교 후 MismatchReport에 포함되지 않고 폐기됨. (7) 결정 필요 6건 전수 재검 — 전건 기본값+권장 보유(품질 양호)하나 D2(#18 배치)·D8(#19 처분)은 목록에 없는 미등재 열린 질문임을 확인.

## Recommendation

FAIL — 종합 0.72 < 0.90. 필수 관문(MP-1~4) 자체는 통과이므로 구조적 기각이 아닌 점수 미달 FAIL이며, 추적성(1.0)과 기준 충실도는 이 저장소 SPEC 중 최상급이다. manager-spec 수정 지시:

1. **D1 (major) 최우선**: REQ-VIEW-RUN-1(spec.md:L84)의 실행 경로를 코드 현실과 정합하게 재정의하라. 권장 문안 방향 — "THEN 시스템이 그 모듈을 `process` 계약 표면(ProcessModule)으로 실행해 입력·출력 XFrame을 산출해야 한다. WHERE fixture와 expected 골든 프레임이 존재하면 `run_harness` 검증 결과(MismatchReport)를 병행 표시할 수 있다." 파급 수정: spec.md:L15/L48 서술("run_harness 직결" → "ProcessModule/run_harness 하네스 계층 직결"로 완화 또는 이원화), acceptance.md Scenario 4 Given(L28)·Scenario 5 Then (a)(L35)·DoD L119, plan.md:L20/L51. 코어 표면 변경 금지 원칙(L23)은 유지하라 — run_harness에 반환 프레임을 추가하는 방향은 택하지 말 것.
2. **D2 (major)**: plan.md:L63-64의 "또는"을 제거하고 #18 배치를 `common/`(예: `common/synthetic_calibset.py` 또는 calibset 모듈 내 팩토리)으로 단일 확정하라 — REQ-VIEW-CORE-3 "배포 가능한"과 packages 목록이 이미 답을 강제한다. plan.md:L79와 정합화하고, 필요 시 「결정 필요/확인 사항」에 모듈 경로 확인 항목으로 등재하라.
3. **D3**: EC-2 Given(acceptance.md:L70)과 결정 필요 4(spec.md:L124)의 심기 메커니즘을 단일 확정 — 권장: "코어 패키지의 임시 복제 트리에 위반 모듈을 생성하고 그 트리를 대상으로 lint를 실행, 실패를 assert (프로덕션 원본 트리 무변경)". "코어 계층에 심되 프로덕션 트리 밖" 문구의 모순을 해소하라.
4. **D10**: plan.md §8 core-no-gui 잡에 GUI 테스트 수집 배제 메커니즘을 1줄로 명시하라(예: `--ignore=tests/apps` 또는 모듈 상단 `pytest.importorskip("napari"/"qtpy")` 가드 + 마커).
5. **D9**: "캡스톤 무간섭" 주장(spec.md:L47, acceptance.md:L132)에 "GUI 테스트 소스는 Gen 1 TC id(000~021) 문자열을 포함하지 않는다" 제약을 추가하거나 XDET-TC-031/036 계약 보존 테스트에 해당 스캔 가드를 포함하라.
6. **D4/D5/D6/D7/D8 (minor 일괄)**: RUN-4를 Ubiquitous로 재라벨, COMPARE-7의 THEN 제거, SPIKE-3·CORE-4를 acceptance L7/L8 분류표에 귀속(권장: CORE-4→Scenario 2 (d) 자동 검출로 귀속 명시, SPIKE-3→마일스톤 게이트 리뷰 규칙), CORE-4/RUN-2/ARCH-5 본문 식별자를 괄호/plan.md로 이동, ARCH 헤더를 "C-11~C-16·C-18·C-19"로 정정(또는 C-17 각주), #19 처분을 Exclusions 또는 결정 필요에 1줄 확정.

재감사(iteration 2)는 D1/D2 해소 증거를 중심으로 하고, 전 결함에 대한 회귀 검사를 수행한다. 아키텍처 골격(apps/gui 격리, additive 3건의 계약 KEPT 실행 가능성, 스택 폴백 단일 순서, TC 030~037 블록)은 코드·기준 문서 대조로 전부 검증되어 재설계가 불필요하다.
